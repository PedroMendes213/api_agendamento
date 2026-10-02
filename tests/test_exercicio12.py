from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_consultas_rejeita_acesso_sem_jwt(client: TestClient):
    resposta = client.get("/consultas")

    assert resposta.status_code in {401, 403}


def test_consultas_rejeita_jwt_malformado(client: TestClient):
    resposta = client.get(
        "/consultas",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert resposta.status_code == 401


def test_agenda_nao_processa_injecao_sem_autenticacao(
    client: TestClient,
):
    resposta = client.get(
        "/agenda",
        params={"data": "2026-10-02' OR '1'='1"},
    )

    assert resposta.status_code == 401


def test_cors_rejeita_origem_nao_autorizada(client: TestClient):
    resposta = client.options(
        "/consultas",
        headers={
            "Origin": "https://origem-nao-autorizada.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert resposta.status_code in {400, 403}
    assert "access-control-allow-origin" not in resposta.headers