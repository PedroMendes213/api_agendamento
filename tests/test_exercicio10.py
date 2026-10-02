import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.security import limpar_rate_limits


@pytest.fixture()
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(test_engine):
    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    with TestClient(app) as test_client:
        yield test_client

    limpar_rate_limits()
    app.dependency_overrides.clear()


def test_cors_permite_origem_da_allowlist(
    client: TestClient,
) -> None:
    resposta = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert resposta.status_code == 200
    assert (
        resposta.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )


def test_cors_rejeita_origem_nao_autorizada(
    client: TestClient,
) -> None:
    resposta = client.options(
        "/health",
        headers={
            "Origin": "http://origem-nao-autorizada.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert resposta.status_code == 400
    assert "access-control-allow-origin" not in resposta.headers


def test_cabecalhos_de_seguranca_estao_presentes(
    client: TestClient,
) -> None:
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert (
        resposta.headers["strict-transport-security"]
        == "max-age=31536000; includeSubDomains"
    )
    assert resposta.headers["x-frame-options"] == "DENY"
    assert (
        resposta.headers["x-content-type-options"]
        == "nosniff"
    )


def test_login_bloqueia_excesso_de_tentativas(
    client: TestClient,
) -> None:
    respostas = []

    for _ in range(5):
        resposta = client.post(
            "/auth/token",
            data={
                "username": "usuario-inexistente",
                "password": "SenhaInvalida@123",
            },
        )

        respostas.append(resposta)

    for resposta in respostas:
        assert resposta.status_code == 401

    sexta_resposta = client.post(
        "/auth/token",
        data={
            "username": "usuario-inexistente",
            "password": "SenhaInvalida@123",
        },
    )

    assert sexta_resposta.status_code == 429
    assert (
        sexta_resposta.json()["detail"]
        == (
            "Muitas tentativas de login. "
            "Aguarde antes de tentar novamente."
        )
    )
    assert "Retry-After" in sexta_resposta.headers
    assert (
        sexta_resposta.headers["X-RateLimit-Limit"]
        == "5"
    )
    assert (
        sexta_resposta.headers["X-RateLimit-Remaining"]
        == "0"
    )