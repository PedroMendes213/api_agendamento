import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth import (
    decodificar_token,
    garantir_leitura_consulta,
    obter_usuario_atual,
)
from app.config import settings
from app.main import app
from app.models import (
    ConsultaCreate,
    PapelUsuario,
    Usuario,
    UsuarioCreate,
)


def test_validacao_rejeita_campo_extra():
    with pytest.raises(ValidationError):
        ConsultaCreate(
            paciente_id=uuid4(),
            profissional_id=uuid4(),
            data_hora=datetime.now(timezone.utc),
            status="agendada",
            observacoes="Consulta de teste",
            campo_nao_declarado="valor proibido",
        )


def test_validacao_rejeita_username_fora_da_regex():
    with pytest.raises(ValidationError):
        UsuarioCreate(
            username="usuario<script>",
            senha="SenhaSegura123!",
            papel=PapelUsuario.RECEPCIONISTA,
        )


@patch("app.auth.jwt.decode")
def test_decodificacao_de_token_trata_erro_com_mock(
    mock_decode,
):
    from jwt.exceptions import InvalidTokenError

    mock_decode.side_effect = InvalidTokenError(
        "assinatura inválida"
    )

    with pytest.raises(HTTPException) as erro:
        decodificar_token("token-falso")

    assert erro.value.status_code == 401
    assert erro.value.detail == "Token inválido ou expirado"
    mock_decode.assert_called_once()


def test_token_com_algoritmo_nao_autorizado_e_rejeitado():
    token = jwt.encode(
        {"sub": str(uuid4())},
        settings.jwt_secret_key,
        algorithm="HS512",
    )

    with pytest.raises(HTTPException) as erro:
        decodificar_token(token)

    assert erro.value.status_code == 401


def test_autorizacao_rejeita_consulta_de_outro_profissional_com_mock():
    usuario = Mock()
    usuario.papel = PapelUsuario.PROFISSIONAL
    usuario.profissional_id = uuid4()

    consulta = Mock()
    consulta.profissional_id = uuid4()

    with pytest.raises(HTTPException) as erro:
        garantir_leitura_consulta(
            usuario,
            consulta,
        )

    assert erro.value.status_code == 403
    assert erro.value.detail == (
        "Usuário sem acesso a esta consulta"
    )


def test_obter_usuario_atual_consulta_sessao_com_mock():
    usuario_id = uuid4()

    usuario = Usuario(
        id=usuario_id,
        username="profissional_teste",
        senha_hash="hash-falso",
        papel=PapelUsuario.PROFISSIONAL,
        profissional_id=uuid4(),
        ativo=True,
    )

    sessao = Mock()
    sessao.get.return_value = usuario

    payload = {
        "sub": str(usuario_id),
        "role": PapelUsuario.PROFISSIONAL.value,
        "token_type": "user",
        "mfa": False,
    }

    resultado = obter_usuario_atual(
        payload=payload,
        session=sessao,
    )

    assert resultado is usuario
    sessao.get.assert_called_once_with(
        Usuario,
        usuario_id,
    )


def test_openapi_declara_oauth2_e_rotas_protegidas():
    especificacao = app.openapi()

    esquemas = especificacao["components"]["securitySchemes"]
    esquema_oauth = esquemas["OAuth2PasswordBearer"]

    assert esquema_oauth["type"] == "oauth2"
    assert esquema_oauth["flows"]["password"]["tokenUrl"] == (
        "/auth/token"
    )
    assert "agenda:horarios" in (
        esquema_oauth["flows"]["password"]["scopes"]
    )

    rotas_protegidas = {
        ("/consultas", "get"),
        ("/consultas", "post"),
        ("/consultas/{consulta_id}", "get"),
        ("/agenda", "get"),
    }

    for caminho, metodo in rotas_protegidas:
        operacao = especificacao["paths"][caminho][metodo]
        assert operacao.get("security")


def test_openapi_nao_expoe_campos_sensiveis():
    especificacao = app.openapi()
    especificacao_texto = json.dumps(
        especificacao,
        ensure_ascii=False,
    )

    assert "senha_hash" not in especificacao_texto
    assert "client_secret_hash" not in especificacao_texto