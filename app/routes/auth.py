import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import (
    GRANT_TYPE_CLIENT_CREDENTIALS,
    GRANT_TYPE_PASSWORD,
    OAuth2TokenRequestForm,
    autenticar_usuario,
    criar_access_token,
    criar_token_m2m,
    hash_password,
    obter_usuario_atual,
    verify_password,
)
from app.database import get_session
from app.models import (
    BootstrapAdmin,
    ClienteM2M,
    Token,
    Usuario,
    UsuarioRead,
)
from app.security import limitar_login


router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"],
)


@router.post(
    "/bootstrap",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
def criar_administrador_inicial(
    dados: BootstrapAdmin,
    session: Session = Depends(get_session),
) -> Usuario:
    usuario_existente = session.exec(
        select(Usuario)
    ).first()

    if usuario_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O administrador inicial já foi criado",
        )

    administrador = Usuario(
        username=dados.username,
        senha_hash=hash_password(dados.senha),
        papel="administrador",
        mfa_habilitado=True,
        mfa_codigo_hash=hash_password(dados.mfa_codigo),
    )

    session.add(administrador)
    session.commit()
    session.refresh(administrador)

    return administrador


@router.post(
    "/token",
    response_model=Token,
    dependencies=[Depends(limitar_login)],
)
def emitir_token(
    form_data: OAuth2TokenRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> Token:
    grant_type = (
        form_data.grant_type
        or GRANT_TYPE_PASSWORD
    )

    if grant_type == GRANT_TYPE_CLIENT_CREDENTIALS:
        if (
            not form_data.client_id
            or not form_data.client_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "client_id e client_secret "
                    "são obrigatórios"
                ),
                headers={"WWW-Authenticate": "Basic"},
            )

        statement = select(ClienteM2M).where(
            ClienteM2M.client_id == form_data.client_id
        )

        cliente = session.exec(statement).first()

        if cliente is None or not cliente.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cliente M2M inválido ou inativo",
                headers={"WWW-Authenticate": "Basic"},
            )

        if not verify_password(
            form_data.client_secret,
            cliente.client_secret_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cliente M2M inválido ou inativo",
                headers={"WWW-Authenticate": "Basic"},
            )

        try:
            escopos_permitidos = set(
                json.loads(cliente.escopos_json)
            )
        except (TypeError, ValueError):
            escopos_permitidos = set()

        escopos_solicitados = set(
            form_data.scope.split()
        )

        if not escopos_solicitados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Informe ao menos um escopo "
                    "no campo scope"
                ),
            )

        if not escopos_solicitados.issubset(
            escopos_permitidos
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "O cliente M2M não possui "
                    "os escopos solicitados"
                ),
            )

        escopos = sorted(escopos_solicitados)

        access_token = criar_token_m2m(
            cliente,
            escopos,
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60,
            scope=" ".join(escopos),
        )

    if grant_type != GRANT_TYPE_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grant_type não suportado",
        )

    if (
        not form_data.username
        or not form_data.password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "username e password "
                "são obrigatórios"
            ),
        )

    usuario = autenticar_usuario(
        session=session,
        username=form_data.username,
        senha=form_data.password,
    )

    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    mfa_verificado = True

    if usuario.mfa_habilitado:
        if (
            not form_data.mfa_code
            or not usuario.mfa_codigo_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA obrigatório",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(
            form_data.mfa_code,
            usuario.mfa_codigo_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )

    access_token = criar_access_token(
        usuario=usuario,
        mfa_verificado=mfa_verificado,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
    )


@router.get(
    "/me",
    response_model=UsuarioRead,
)
def usuario_atual(
    usuario: Usuario = Depends(obter_usuario_atual),
) -> Usuario:
    return usuario