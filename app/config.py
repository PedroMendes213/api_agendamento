from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "API de Agendamento de Consultas"
    database_url: str = "sqlite:///./agendamento.db"

    jwt_secret_key: str = Field(
        default="",
        min_length=32,
        repr=False,
    )

    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = Field(
        default=30,
        ge=5,
        le=60,
    )

    cors_allowed_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    login_rate_limit_requests: int = Field(
        default=5,
        ge=1,
        le=100,
    )

    login_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validar_chave_jwt(cls, valor: str) -> str:
        valor_limpo = valor.strip()

        if not valor_limpo:
            raise ValueError(
                "JWT_SECRET_KEY deve ser definido no arquivo .env"
            )

        if valor_limpo == "development-only-change-this-secret-key":
            raise ValueError(
                "Não utilize a chave JWT padrão de desenvolvimento"
            )

        if len(valor_limpo) < 32:
            raise ValueError(
                "JWT_SECRET_KEY deve possuir pelo menos 32 caracteres"
            )

        return valor_limpo

    def obter_cors_origins(self) -> list[str]:
        return [
            origem.strip()
            for origem in self.cors_allowed_origins.split(",")
            if origem.strip()
        ]


settings = Settings()