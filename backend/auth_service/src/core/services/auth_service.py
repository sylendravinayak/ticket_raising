import uuid
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from src.config.settings import get_settings
from src.core.exceptions.auth import (
    AuthenticationError,
    InvalidTokenTypeError,
    TokenRevokedError,
    TokenExpiredError
)
from src.data.models.postgres.role import Role
from src.data.models.postgres.token import RefreshToken
from src.data.models.postgres.user import User
from src.data.repositories.token_repository import TokenRepository
from src.data.repositories.user_repository import UserRepository
from src.observability.logging.logger import get_logger
from src.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from jose import JWTError, ExpiredSignatureError
logger = get_logger(__name__)

settings = get_settings()


pwd = CryptContext(schemes=["argon2"])
_DUMMY_HASH=pwd.hash("dummy_password")

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
            logger.warning("Signup attempt with existing email: %s", data.email)
            raise AuthenticationError("Unable to create account")

        result = await self._user_repo.session.execute(
            select(Role).where(Role.name == data.role)
        )
        role_record = result.scalar_one_or_none()
        if role_record is None:
            role_record = Role(name=data.role)
            self._user_repo.session.add(role_record)
            await self._user_repo.session.flush()

        user = User(
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            role_id=role_record.id,
        )
        saved = await self._user_repo.save(user)
        logger.info("signup successfull", email=data.email, user_id=str(saved.id))
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
            logger.warning("Failed login attempt", email=data.email)
            raise AuthenticationError()

        await self._token_repo.cleanup_expired(user.id)

        tokens = await self._issue_token_pair(user)

        logger.info("Login successful", email=data.email, user_id=str(user.id))
        return tokens


    async def refresh(self, refresh_token: str) -> TokenResponse:
        """
        Rotate refresh token and issue new token pair.
        """

        try:
            payload = decode_token(refresh_token)
        except Exception as err:
            logger.warning("Failed to decode refresh token", error=str(err))
            raise AuthenticationError("Invalid token") from err

        if payload.get("token_type") != "refresh":
            logger.warning(
                "Invalid token type for refresh",
                 token_type=payload.get("token_type")
                 )
            raise InvalidTokenTypeError()


        jti: str = payload.get("jti", "")

        record = await self._token_repo.get_by_jti(jti)

        if record is None:
            logger.warning("Refresh token not found in database", jti=jti)
            raise AuthenticationError("Invalid token")

        if record.revoked:

            await self._token_repo.revoke_all_for_user(record.user_id)
            logger.warning(
                "Refresh token reuse detected - all tokens revoked for user",
                  user_id=str(record.user_id), jti=jti
                  )
            raise TokenRevokedError()

        if record.expires_at <= datetime.now(UTC):
            logger.warning(
                "Refresh token expired",
                jti=jti,
                expires_at=record.expires_at.isoformat()
                )
            raise AuthenticationError("Token expired")

        await self._token_repo.revoke(record)

        user = await self._user_repo.get_by_id(record.user_id)
        if not user or not user.is_active:
            logger.warning(
            "User not found or inactive during token refresh",
            user_id=str(record.user_id)
            )
            raise AuthenticationError()

        tokens = await self._issue_token_pair(user)



        return tokens


    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)

        except ExpiredSignatureError as err:
            raise TokenExpiredError() from err

        except JWTError as err:
            raise AuthenticationError("Invalid token") from err

        if payload.get("token_type") != "refresh":
            raise InvalidTokenTypeError()

        jti = payload.get("jti")
        if not jti:
            raise AuthenticationError("Invalid token payload")

        record = await self._token_repo.get_by_jti(jti)

        if not record:
            raise AuthenticationError("Invalid token")

        if record.revoked:
            raise TokenRevokedError()

        await self._token_repo.revoke(record)

    async def get_user_profile(self, user_id: str) -> UserResponse:
        """
        Fetch user profile by ID (from access token sub claim).

        """
        user = await self._user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            logger.warning("User not found or inactive", user_id=user_id)
            raise AuthenticationError()
        logger.info("Fetched user profile", user_id=user_id)
        return UserResponse.model_validate(user)


    async def _issue_token_pair(
        self, user: User
    ) -> TokenResponse:
        """
        Create DB refresh token record + sign both JWTs.

        """
        refresh_jti = str(uuid.uuid4())
        access_jti = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )


        refresh_record = RefreshToken(
            user_id=user.id,
            jti=refresh_jti,
            expires_at=expires_at,
        )
        await self._token_repo.save(refresh_record)

        role_name = user.role.name.value if user.role else "user"
        access_token = create_access_token(str(user.id), role_name, access_jti)
        refresh_token = create_refresh_token(str(user.id), refresh_jti)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
