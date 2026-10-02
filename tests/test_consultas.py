from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


def criar_admin(client: TestClient) -> dict[str, str]:
    resposta_bootstrap = client.post(
        "/auth/bootstrap",
        json={
            "username": "admin",
            "senha": "Admin12345!",
            "mfa_codigo": "123456",
        },
    )

    assert resposta_bootstrap.status_code == 201

    resposta_token = client.post(
        "/auth/token",
        data={
            "username": "admin",
            "password": "Admin12345!",
            "mfa_code": "123456",
        },
    )

    assert resposta_token.status_code == 200

    token = resposta_token.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def criar_profissional(
    client: TestClient,
    headers_admin: dict[str, str],
) -> tuple[dict[str, str], str]:
    profissional_id = str(uuid4())

    resposta = client.post(
        "/admin/usuarios",
        headers=headers_admin,
        json={
            "username": "profissional",
            "senha": "Profissional123!",
            "papel": "profissional",
            "profissional_id": profissional_id,
            "mfa_habilitado": False,
        },
    )

    assert resposta.status_code == 201

    resposta_token = client.post(
        "/auth/token",
        data={
            "username": "profissional",
            "password": "Profissional123!",
        },
    )

    assert resposta_token.status_code == 200

    token = resposta_token.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }, profissional_id


def criar_recepcionista(
    client: TestClient,
    headers_admin: dict[str, str],
) -> dict[str, str]:
    resposta = client.post(
        "/admin/usuarios",
        headers=headers_admin,
        json={
            "username": "recepcao",
            "senha": "Recepcao123!",
            "papel": "recepcionista",
        },
    )

    assert resposta.status_code == 201

    resposta_token = client.post(
        "/auth/token",
        data={
            "username": "recepcao",
            "password": "Recepcao123!",
        },
    )

    assert resposta_token.status_code == 200

    token = resposta_token.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_criar_e_listar_consulta_com_sucesso(
    client: TestClient,
):
    headers_admin = criar_admin(client)
    headers_profissional, profissional_id = criar_profissional(
        client,
        headers_admin,
    )

    data_consulta = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    payload = {
        "paciente_id": str(uuid4()),
        "profissional_id": profissional_id,
        "data_hora": data_consulta.isoformat(),
        "status": "agendada",
        "observacoes": "Consulta de avaliação.",
    }

    resposta_criacao = client.post(
        "/consultas",
        headers=headers_profissional,
        json=payload,
    )

    assert resposta_criacao.status_code == 201

    resposta_lista = client.get(
        "/consultas",
        headers=headers_profissional,
    )

    assert resposta_lista.status_code == 200
    assert len(resposta_lista.json()) == 1
    assert resposta_lista.json()[0]["profissional_id"] == profissional_id


def test_agenda_html_escapa_xss(
    client: TestClient,
):
    headers_admin = criar_admin(client)
    headers_profissional, profissional_id = criar_profissional(
        client,
        headers_admin,
    )

    data_consulta = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    payload = {
        "paciente_id": str(uuid4()),
        "profissional_id": profissional_id,
        "data_hora": data_consulta.isoformat(),
        "status": "agendada",
        "observacoes": "<script>alert('xss')</script>",
    }

    resposta_criacao = client.post(
        "/consultas",
        headers=headers_profissional,
        json=payload,
    )

    assert resposta_criacao.status_code == 201

    resposta_html = client.get(
        f"/agenda?data={data_consulta.date().isoformat()}",
        headers=headers_profissional,
    )

    assert resposta_html.status_code == 200
    assert "<script>" not in resposta_html.text
    assert "&lt;script&gt;" in resposta_html.text


def test_usuario_sem_admin_e_barrado(
    client: TestClient,
):
    headers_admin = criar_admin(client)
    headers_recepcionista = criar_recepcionista(
        client,
        headers_admin,
    )

    resposta = client.post(
        "/admin/usuarios",
        headers=headers_recepcionista,
        json={
            "username": "outro_usuario",
            "senha": "OutroUsuario123!",
            "papel": "recepcionista",
        },
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Usuário sem permissão para esta operação"
    )


def test_profissional_nao_acessa_consulta_de_outro(
    client: TestClient,
):
    headers_admin = criar_admin(client)

    headers_profissional_1, profissional_id_1 = criar_profissional(
        client,
        headers_admin,
    )

    profissional_id_2 = str(uuid4())

    resposta_usuario_2 = client.post(
        "/admin/usuarios",
        headers=headers_admin,
        json={
            "username": "profissional2",
            "senha": "Profissional2123!",
            "papel": "profissional",
            "profissional_id": profissional_id_2,
        },
    )

    assert resposta_usuario_2.status_code == 201

    resposta_token_2 = client.post(
        "/auth/token",
        data={
            "username": "profissional2",
            "password": "Profissional2123!",
        },
    )

    assert resposta_token_2.status_code == 200

    headers_profissional_2 = {
        "Authorization": (
            f"Bearer {resposta_token_2.json()['access_token']}"
        ),
    }

    data_consulta = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    resposta_consulta = client.post(
        "/consultas",
        headers=headers_profissional_1,
        json={
            "paciente_id": str(uuid4()),
            "profissional_id": profissional_id_1,
            "data_hora": data_consulta.isoformat(),
            "status": "agendada",
        },
    )

    assert resposta_consulta.status_code == 201

    consulta_id = resposta_consulta.json()["id"]

    resposta_acesso = client.get(
        f"/consultas/{consulta_id}",
        headers=headers_profissional_2,
    )

    assert resposta_acesso.status_code == 403