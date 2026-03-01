from typing import Any

from fastapi import status


class ApplicationError(Exception):
    """
    Root exception for all application errors.
    Designed to be caught by a global FastAPI exception handler.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."
    headers: dict[str, str] | None = None

    def __init__(
        self,
        *,
        status_code: int | None = None,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        details: Any = None,
    ) -> None:
        self.status_code = status_code or self.__class__.status_code
        self.detail = detail or self.__class__.detail
        self.headers = headers or self.__class__.headers
        self.details = details
        super().__init__(self.detail)
