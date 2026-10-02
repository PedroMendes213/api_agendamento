from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def obter_connect_args() -> dict[str, object]:
    if settings.database_url.startswith("sqlite"):
        return {
            "check_same_thread": False,
        }

    return {}


engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=obter_connect_args(),
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session