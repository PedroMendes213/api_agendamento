from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import hash_password
from app.database import get_session
from app.main import app
from app.models import (
    Consulta,
    PapelUsuario,
    StatusConsulta,
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
def profissionais(test_engine):
    profissional_1_id = uuid4()
    profissional_2_id = uuid4()

    with Session(test_engine) as session:
        profissional_1 = Usuario(
            username="profissional_ex9_1",
            senha_hash=hash_password("Profissional@123"),
            papel=PapelUsuario.PROFISSIONAL,
            profissional_id=profissional_1_id,
        )

        profissional_2 = Usuario(
            username="profissional_ex9_2",
            senha_hash=hash_password("Profissional@456"),
            papel=PapelUsuario.PROFISSIONAL,
            profissional_id=profissional_2_id,
        )

        session.add(profissional_1)
        session.add(profissional_2)
        session.commit()

    return {
        "primeiro": profissional_1_id,
        "segundo": profissional_2_id,
    }


def obter_token(
    client: TestClient,
    username: str,
    password: str,
) -> str:
    resposta = client.post(
        "/auth/token",
        data={
            "username": username,
            "password": password,
        },
    )

    assert resposta.status_code == 200

    return resposta.json()["access_token"]


def cabecalho_autorizacao(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def criar_payload_consulta(
    profissional_id: UUID,
    data_hora: str = "2030-01-15T14:30:00-03:00",
    observacoes: str | None = None,
) -> dict:
    payload = {
        "paciente_id": str(uuid4()),
        "profissional_id": str(profissional_id),
        "data_hora": data_hora,
        "status": "agendada",
    }

    if observacoes is not None:
        payload["observacoes"] = observacoes

    return payload


def test_rejeita_username_fora_da_regex(
    client: TestClient,
) -> None:
    resposta = client.post(
        "/auth/bootstrap",
        json={
            "username": "usuario inválido",
            "senha": "Administrador@123",
            "mfa_codigo": "123456",
        },
    )

    assert resposta.status_code == 422


def test_rejeita_campo_extra_no_corpo(
    client: TestClient,
    profissionais: dict[str, UUID],
) -> None:
    token = obter_token(
        client,
        "profissional_ex9_1",
        "Profissional@123",
    )

    payload = criar_payload_consulta(
        profissional_id=profissionais["primeiro"],
    )

    payload["campo_nao_declarado"] = "tentativa de injeção"

    resposta = client.post(
        "/consultas",
        json=payload,
        headers=cabecalho_autorizacao(token),
    )

    assert resposta.status_code == 422


def test_impede_conflito_de_horario(
    client: TestClient,
    profissionais: dict[str, UUID],
) -> None:
    token = obter_token(
        client,
        "profissional_ex9_1",
        "Profissional@123",
    )

    primeiro_payload = criar_payload_consulta(
        profissional_id=profissionais["primeiro"],
    )

    primeira_resposta = client.post(
        "/consultas",
        json=primeiro_payload,
        headers=cabecalho_autorizacao(token),
    )

    assert primeira_resposta.status_code == 201

    segundo_payload = criar_payload_consulta(
        profissional_id=profissionais["primeiro"],
    )

    segunda_resposta = client.post(
        "/consultas",
        json=segundo_payload,
        headers=cabecalho_autorizacao(token),
    )

    assert segunda_resposta.status_code == 409
    assert segunda_resposta.json()["detail"] == (
        "Já existe uma consulta agendada "
        "para este profissional neste horário"
    )


def test_saida_html_escapa_xss(
    client: TestClient,
    profissionais: dict[str, UUID],
) -> None:
    token = obter_token(
        client,
        "profissional_ex9_1",
        "Profissional@123",
    )

    payload = criar_payload_consulta(
        profissional_id=profissionais["primeiro"],
        data_hora="2030-01-16T14:30:00-03:00",
        observacoes="<script>alert('xss')</script>",
    )

    resposta_criacao = client.post(
        "/consultas",
        json=payload,
        headers=cabecalho_autorizacao(token),
    )

    assert resposta_criacao.status_code == 201

    resposta_html = client.get(
        "/agenda?data=2030-01-16",
        headers=cabecalho_autorizacao(token),
    )

    assert resposta_html.status_code == 200
    assert "<script>" not in resposta_html.text
    assert "&lt;script&gt;" in resposta_html.text
    assert "alert" in resposta_html.text


def test_ownership_impede_acesso_a_consulta_de_outro_profissional(
    client: TestClient,
    test_engine,
    profissionais: dict[str, UUID],
) -> None:
    data_hora = datetime(
        2030,
        1,
        17,
        14,
        30,
        tzinfo=timezone.utc,
    )

    consulta_id = uuid4()

    with Session(test_engine) as session:
        consulta = Consulta(
            id=consulta_id,
            paciente_id=uuid4(),
            profissional_id=profissionais["primeiro"],
            data_hora=data_hora,
            status=StatusConsulta.AGENDADA,
            observacoes="Consulta protegida",
        )

        session.add(consulta)
        session.commit()

    token_profissional_2 = obter_token(
        client,
        "profissional_ex9_2",
        "Profissional@456",
    )

    resposta = client.get(
        f"/consultas/{consulta_id}",
        headers=cabecalho_autorizacao(token_profissional_2),
    )

    assert resposta.status_code == 403


def test_rejeita_parametro_de_data_malformado(
    client: TestClient,
    profissionais: dict[str, UUID],
) -> None:
    token = obter_token(
        client,
        "profissional_ex9_1",
        "Profissional@123",
    )

    resposta = client.get(
        "/agenda?data=2030-01-16%27%20OR%201%3D1",
        headers=cabecalho_autorizacao(token),
    )

    assert resposta.status_code == 422