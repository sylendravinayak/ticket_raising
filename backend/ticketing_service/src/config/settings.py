from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, PostgresDsn
from functools import lru_cache


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        
    )

    database_url: str

    

    


