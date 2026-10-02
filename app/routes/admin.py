import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import exigir_papeis, hash_password
from app.database import get_session
from app.models import (
    ClienteM2M,
    ClienteM2MCriado,
    ClienteM2MCreate,
    ClienteM2MRead,
    EscopoM2M,
    PapelUsuario,
    Usuario,
    UsuarioCreate,
    UsuarioRead,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administração"],
)


def _escopos_do_cliente(
    cliente: ClienteM2M,
) -> list[EscopoM2M]:
    try:
        valores = json.loads(cliente.escopos_json)
    except (TypeError, ValueError):
        valores = []

    return [EscopoM2M(valor) for valor in valores]


def _cliente_para_leitura(
    cliente: ClienteM2M,
) -> ClienteM2MRead:
    return ClienteM2MRead(
        id=cliente.id,
        client_id=cliente.client_id,
        nome=cliente.nome,
        escopos=_escopos_do_cliente(cliente),
        ativo=cliente.ativo,
    )


@router.get(
    "/usuarios",
    response_model=list[UsuarioRead],
)
def listar_usuarios(
    session: Session = Depends(get_session),
    _: Usuario = Depends(
        exigir_papeis(PapelUsuario.ADMINISTRADOR)
    ),
) -> list[Usuario]:
    statement = select(Usuario).order_by(Usuario.username)
    return list(session.exec(statement).all())


@router.post(
    "/usuarios",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
def criar_usuario(
    dados: UsuarioCreate,
    session: Session = Depends(get_session),
    _: Usuario = Depends(
        exigir_papeis(PapelUsuario.ADMINISTRADOR)
    ),
) -> Usuario:
    statement = select(Usuario).where(
        Usuario.username == dados.username
    )

    if session.exec(statement).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já cadastrado",
        )

    usuario = Usuario(
        username=dados.username,
        senha_hash=hash_password(dados.senha),
        papel=dados.papel,
        profissional_id=dados.profissional_id,
        mfa_habilitado=dados.mfa_habilitado,
        mfa_codigo_hash=(
            hash_password(dados.mfa_codigo)
            if dados.mfa_codigo
            else None
        ),
    )

    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    return usuario


@router.get(
    "/clientes-m2m",
    response_model=list[ClienteM2MRead],
)
def listar_clientes_m2m(
    session: Session = Depends(get_session),
    _: Usuario = Depends(
        exigir_papeis(PapelUsuario.ADMINISTRADOR)
    ),
) -> list[ClienteM2MRead]:
    statement = select(ClienteM2M).order_by(ClienteM2M.nome)
    clientes = session.exec(statement).all()

    return [
        _cliente_para_leitura(cliente)
        for cliente in clientes
    ]


@router.post(
    "/clientes-m2m",
    response_model=ClienteM2MCriado,
    status_code=status.HTTP_201_CREATED,
)
def criar_cliente_m2m(
    dados: ClienteM2MCreate,
    session: Session = Depends(get_session),
    _: Usuario = Depends(
        exigir_papeis(PapelUsuario.ADMINISTRADOR)
    ),
) -> ClienteM2MCriado:
    while True:
        client_id = f"lab_{secrets.token_urlsafe(12)}"

        statement = select(ClienteM2M).where(
            ClienteM2M.client_id == client_id
        )

        if session.exec(statement).first() is None:
            break

    client_secret = secrets.token_urlsafe(32)

    cliente = ClienteM2M(
        client_id=client_id,
        nome=dados.nome,
        client_secret_hash=hash_password(client_secret),
        escopos_json=json.dumps(
            [
                escopo.value
                for escopo in dados.escopos
            ]
        ),
    )

    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    return ClienteM2MCriado(
        id=cliente.id,
        client_id=cliente.client_id,
        client_secret=client_secret,
        nome=cliente.nome,
        escopos=dados.escopos,
        ativo=cliente.ativo,
    )