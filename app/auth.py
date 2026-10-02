import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import (
    ClienteM2M,
    Consulta,
    PapelUsuario,
    Usuario,
)


TOKEN_TIPO_USUARIO = "user"
TOKEN_TIPO_M2M = "m2m"

GRANT_TYPE_PASSWORD = "password"
GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "agenda:horarios": (
            "Consultar horários disponíveis para o laboratório parceiro"
        ),
    },
)


class OAuth2TokenRequestForm:
    """Dados aceitos pelos fluxos password e client_credentials."""

    def __init__(
        self,
        grant_type: str | None = Form(default=None),
        username: str | None = Form(default=None),
        password: str | None = Form(default=None),
        scope: str = Form(default=""),
        client_id: str | None = Form(default=None),
        client_secret: str | None = Form(default=None),
        mfa_code: str | None = Form(default=None),
    ) -> None:
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret
        self.mfa_code = mfa_code


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, UnicodeError):
        return False


def _criar_payload_base(expiracao: datetime) -> dict[str, Any]:
    agora = datetime.now(timezone.utc)

    return {
        "iat": agora,
        "exp": expiracao,
    }


def criar_access_token(
    usuario: Usuario,
    mfa_verificado: bool,
) -> str:
    agora = datetime.now(timezone.utc)
    expiracao = agora + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload: dict[str, Any] = _criar_payload_base(expiracao)

    payload.update(
        {
            "sub": str(usuario.id),
            "role": usuario.papel.value,
            "profissional_id": (
                str(usuario.profissional_id)
                if usuario.profissional_id is not None
                else None
            ),
            "mfa": mfa_verificado,
            "token_type": TOKEN_TIPO_USUARIO,
            "principal_type": "usuario",
            "scope": "",
        }
    )

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def criar_token_m2m(
    cliente: ClienteM2M,
    escopos: list[str],
) -> str:
    agora = datetime.now(timezone.utc)
    expiracao = agora + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload: dict[str, Any] = _criar_payload_base(expiracao)

    payload.update(
        {
            "sub": cliente.client_id,
            "client_id": cliente.client_id,
            "client_type": "laboratorio",
            "grant_type": GRANT_TYPE_CLIENT_CREDENTIALS,
            "token_type": TOKEN_TIPO_M2M,
            "scope": " ".join(sorted(escopos)),
        }
    )

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decodificar_token(token: str) -> dict[str, Any]:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise credenciais_invalidas from exc
    except InvalidTokenError as exc:
        raise credenciais_invalidas from exc

    if not isinstance(payload, dict):
        raise credenciais_invalidas

    return payload


def obter_claims_token(
    token: str = Depends(oauth2_scheme),
) -> dict[str, Any]:
    return decodificar_token(token)


def obter_usuario_atual(
    payload: dict[str, Any] = Depends(obter_claims_token),
    session: Session = Depends(get_session),
) -> Usuario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de usuário inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if payload.get("token_type") != TOKEN_TIPO_USUARIO:
        raise credenciais_invalidas

    subject = payload.get("sub")
    role = payload.get("role")

    if not isinstance(subject, str) or not isinstance(role, str):
        raise credenciais_invalidas

    try:
        usuario_id = UUID(subject)
    except ValueError as exc:
        raise credenciais_invalidas from exc

    usuario = session.get(Usuario, usuario_id)

    if usuario is None or not usuario.ativo:
        raise credenciais_invalidas

    if usuario.papel.value != role:
        raise credenciais_invalidas

    if usuario.mfa_habilitado and payload.get("mfa") is not True:
        raise credenciais_invalidas

    return usuario


def exigir_cliente_m2m_com_escopo(
    escopo_obrigatorio: str,
) -> Callable[..., ClienteM2M]:
    def verificar_cliente(
        payload: dict[str, Any] = Depends(obter_claims_token),
        session: Session = Depends(get_session),
    ) -> ClienteM2M:
        if (
            payload.get("token_type") != TOKEN_TIPO_M2M
            or payload.get("grant_type") != GRANT_TYPE_CLIENT_CREDENTIALS
            or payload.get("client_type") != "laboratorio"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Apenas o cliente M2M do laboratório "
                    "pode usar esta operação"
                ),
            )

        client_id = payload.get("client_id")
        subject = payload.get("sub")
        scope_claim = payload.get("scope")

        if (
            not isinstance(client_id, str)
            or not isinstance(subject, str)
            or not isinstance(scope_claim, str)
            or subject != client_id
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Claims do token M2M inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        escopos_do_token = set(scope_claim.split())

        if escopo_obrigatorio not in escopos_do_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Token M2M sem o escopo necessário "
                    "para esta operação"
                ),
            )

        statement = select(ClienteM2M).where(
            ClienteM2M.client_id == client_id
        )

        cliente = session.exec(statement).first()

        if cliente is None or not cliente.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cliente M2M inválido ou inativo",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            escopos_permitidos = set(
                json.loads(cliente.escopos_json)
            )
        except (TypeError, ValueError):
            escopos_permitidos = set()

        if escopo_obrigatorio not in escopos_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "O cliente M2M não possui este "
                    "escopo contratado"
                ),
            )

        if not escopos_do_token.issubset(escopos_permitidos):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "O token contém escopos não autorizados "
                    "para o cliente"
                ),
            )

        return cliente

    return verificar_cliente


def exigir_papeis(
    *papeis_permitidos: PapelUsuario,
) -> Callable[..., Usuario]:
    def verificar_papel(
        usuario: Usuario = Depends(obter_usuario_atual),
    ) -> Usuario:
        if usuario.papel not in papeis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem permissão para esta operação",
            )

        return usuario

    return verificar_papel


def garantir_leitura_consulta(
    usuario: Usuario,
    consulta: Consulta,
) -> None:
    if usuario.papel in {
        PapelUsuario.ADMINISTRADOR,
        PapelUsuario.RECEPCIONISTA,
    }:
        return

    if (
        usuario.papel == PapelUsuario.PROFISSIONAL
        and usuario.profissional_id == consulta.profissional_id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Usuário sem acesso a esta consulta",
    )


def garantir_gerenciamento_consulta(
    usuario: Usuario,
    consulta: Consulta,
) -> None:
    if usuario.papel == PapelUsuario.ADMINISTRADOR:
        return

    if (
        usuario.papel == PapelUsuario.PROFISSIONAL
        and usuario.profissional_id == consulta.profissional_id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Somente o profissional responsável ou "
            "um administrador pode gerenciar esta consulta"
        ),
    )


def garantir_profissional_da_consulta(
    usuario: Usuario,
    profissional_id: UUID,
) -> None:
    if usuario.papel == PapelUsuario.ADMINISTRADOR:
        return

    if (
        usuario.papel == PapelUsuario.PROFISSIONAL
        and usuario.profissional_id == profissional_id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="O profissional só pode operar consultas próprias",
    )


def autenticar_usuario(
    session: Session,
    username: str,
    senha: str,
) -> Usuario | None:
    statement = select(Usuario).where(
        Usuario.username == username
    )

    usuario = session.exec(statement).first()

    if usuario is None:
        return None

    if not verify_password(senha, usuario.senha_hash):
        return None

    return usuario