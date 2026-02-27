import uuid
from datetime import datetime, timedelta, timezone

import structlog
from src.config.settings import get_settings
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.core.exceptions.auth import (
    AuthenticationException,
    InvalidTokenTypeException,
    TokenRevokedException,
)

from src.data.models.postgres.token import RefreshToken
from src.data.models.postgres.user import User
from src.data.repositories.token_repository import TokenRepository
from src.data.repositories.user_repository import UserRepository
from src.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)
settings = get_settings()


_DUMMY_HASH: str = (
    "$2b$12$notarealhashbutlongenoughtomakebcryptrunfullrounds0000"
)


class AuthService:
    """
    Handles all authentication workflows.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._user_repo = UserRepository(session)
        self._token_repo = TokenRepository(session)


    async def signup(self, data: SignupRequest) -> UserResponse:
        """
        Register a new user account.
        """
        if await self._user_repo.email_exists(data.email):
            raise AuthenticationException("Unable to create account")

        user = User(
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        saved = await self._user_repo.save(user)

        await logger.ainfo(
            "auth.signup",
            user_id=str(saved.id),
            role=saved.role,
        )

        return UserResponse.model_validate(saved)

   

    async def login(self, data: LoginRequest) -> TokenResponse:
        """
        Authenticate user and issue a new token pair.
        """
        user = await self._user_repo.get_by_email(data.email.lower().strip())

      
        password_valid = verify_password(
            data.password,
            user.hashed_password if user else _DUMMY_HASH,
        )

        if not user or not password_valid or not user.is_active:
            raise AuthenticationException()

        await self._token_repo.cleanup_expired(user.id)

        tokens = await self._issue_token_pair(user, data.device_id)

        await logger.ainfo(
            "auth.login",
            user_id=str(user.id),
            device_id=data.device_id,
        )

        return tokens


    async def refresh(self, refresh_token: str, device_id: str) -> TokenResponse:
        """
        Rotate refresh token and issue new token pair.
        """
        
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise AuthenticationException("Invalid token")

        if payload.get("token_type") != "refresh":
            raise InvalidTokenTypeException()

        jti: str = payload.get("jti", "")
        user_id_str: str = payload.get("sub", "")

        record = await self._token_repo.get_by_jti(jti)

        if record is None:
            raise AuthenticationException("Invalid token")

        if record.revoked:
            await logger.awarning(
                "auth.token_reuse_detected",
                user_id=str(record.user_id),
                jti=jti,
                device_id=device_id,
            )
            await self._token_repo.revoke_all_for_user(record.user_id)
            raise TokenRevokedException()

        
        if record.device_id != device_id:
            await logger.awarning(
                "auth.device_mismatch",
                user_id=str(record.user_id),
                expected_device=record.device_id,
                presented_device=device_id,
            )
            raise AuthenticationException("Device mismatch")

        if record.expires_at <= datetime.now(timezone.utc):
            raise AuthenticationException("Token expired")

        await self._token_repo.revoke(record)

        user = await self._user_repo.get_by_id(record.user_id)
        if not user or not user.is_active:
            raise AuthenticationException()

        tokens = await self._issue_token_pair(user, device_id)

        await logger.ainfo(
            "auth.token_rotated",
            user_id=str(user.id),
            device_id=device_id,
        )

        return tokens


    async def logout(self, refresh_token: str) -> None:
        """
        Logout by revoking the refresh token.
        """
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti", "")
            record = await self._token_repo.get_by_jti(jti)
            if record and not record.revoked:
                await self._token_repo.revoke(record)
                await logger.ainfo(
                    "auth.logout",
                    user_id=str(record.user_id),
                )
        except Exception:
            
            pass


    async def get_user_profile(self, user_id: str) -> UserResponse:
        """
        Fetch user profile by ID (from access token sub claim).

        """
        user = await self._user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise AuthenticationException()
        return UserResponse.model_validate(user)


    async def _issue_token_pair(
        self, user: User, device_id: str
    ) -> TokenResponse:
        """
        Create DB refresh token record + sign both JWTs.

        """
        refresh_jti = str(uuid.uuid4())
        access_jti = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )


        refresh_record = RefreshToken(
            user_id=user.id,
            jti=refresh_jti,
            device_id=device_id,
            expires_at=expires_at,
        )
        await self._token_repo.save(refresh_record)

        access_token = create_access_token(str(user.id), user.role, access_jti)
        refresh_token = create_refresh_token(str(user.id), refresh_jti)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )