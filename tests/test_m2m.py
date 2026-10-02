import json
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import hash_password
from app.config import settings
from app.database import get_session
from app.main import app
from app.models import (
    ClienteM2M,
    EscopoM2M,
    PapelUsuario,
    Usuario,
)


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

    app.dependency_overrides.clear()


@pytest.fixture()
def credenciais_laboratorio(test_engine):
    client_id = "lab_teste"
    client_secret = "segredo-lab-teste"

    with Session(test_engine) as session:
        cliente = ClienteM2M(
            client_id=client_id,
            nome="Laboratório de Teste",
            client_secret_hash=hash_password(client_secret),
            escopos_json=json.dumps(
                [EscopoM2M.AGENDA_HORARIOS.value]
            ),
        )

        session.add(cliente)
        session.commit()

    return client_id, client_secret


def obter_token_laboratorio(
    client: TestClient,
    client_id: str,
    client_secret: str,
) -> str:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "agenda:horarios",
        },
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["token_type"] == "bearer"
    assert dados["scope"] == "agenda:horarios"

    return dados["access_token"]


def test_laboratorio_recebe_claims_e_consulta_horarios(
    client: TestClient,
    credenciais_laboratorio: tuple[str, str],
) -> None:
    client_id, client_secret = credenciais_laboratorio

    token = obter_token_laboratorio(
        client,
        client_id,
        client_secret,
    )

    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert claims["token_type"] == "m2m"
    assert claims["client_type"] == "laboratorio"
    assert claims["grant_type"] == "client_credentials"
    assert claims["client_id"] == client_id
    assert claims["scope"] == "agenda:horarios"

    resposta = client.get(
        "/integracoes/laboratorio/horarios?data=2030-01-16",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["data"] == "2030-01-16"
    assert resposta.json()["horarios_disponiveis"]


def test_profissional_nao_pode_usar_endpoint_do_laboratorio(
    client: TestClient,
    test_engine,
) -> None:
    profissional_id = uuid4()

    with Session(test_engine) as session:
        profissional = Usuario(
            username="profissional_teste",
            senha_hash=hash_password("Profissional@123"),
            papel=PapelUsuario.PROFISSIONAL,
            profissional_id=profissional_id,
        )

        session.add(profissional)
        session.commit()

    resposta_token = client.post(
        "/auth/token",
        data={
            "username": "profissional_teste",
            "password": "Profissional@123",
        },
    )

    assert resposta_token.status_code == 200

    token_profissional = resposta_token.json()["access_token"]

    resposta = client.get(
        "/integracoes/laboratorio/horarios?data=2030-01-16",
        headers={
            "Authorization": f"Bearer {token_profissional}",
        },
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Apenas o cliente M2M do laboratório "
        "pode usar esta operação"
    )