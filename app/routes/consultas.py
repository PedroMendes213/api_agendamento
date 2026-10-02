from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.auth import (
    garantir_gerenciamento_consulta,
    garantir_leitura_consulta,
    garantir_profissional_da_consulta,
    exigir_papeis,
    obter_usuario_atual,
)
from app.database import get_session
from app.models import (
    Consulta,
    ConsultaCreate,
    ConsultaRead,
    ConsultaUpdate,
    PapelUsuario,
    StatusConsulta,
    Usuario,
)


router = APIRouter(
    prefix="/consultas",
    tags=["Consultas"],
)


STATUS_OCUPA_HORARIO = (
    StatusConsulta.AGENDADA,
    StatusConsulta.CONFIRMADA,
)


def verificar_conflito_de_horario(
    session: Session,
    profissional_id: UUID,
    data_hora,
    consulta_id: UUID | None = None,
) -> None:
    statement = select(Consulta).where(
        Consulta.profissional_id == profissional_id,
        Consulta.data_hora == data_hora,
        Consulta.status.in_(STATUS_OCUPA_HORARIO),
    )

    if consulta_id is not None:
        statement = statement.where(
            Consulta.id != consulta_id
        )

    consulta_existente = session.exec(statement).first()

    if consulta_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Já existe uma consulta agendada "
                "para este profissional neste horário"
            ),
        )


@router.get(
    "",
    response_model=list[ConsultaRead],
)
def listar_consultas(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(obter_usuario_atual),
) -> list[ConsultaRead]:
    consulta_sql = select(Consulta)

    if usuario.papel == PapelUsuario.PROFISSIONAL:
        if usuario.profissional_id is None:
            return []

        consulta_sql = consulta_sql.where(
            Consulta.profissional_id == usuario.profissional_id
        )

    consulta_sql = consulta_sql.offset(offset).limit(limit)

    return list(session.exec(consulta_sql).all())


@router.post(
    "",
    response_model=ConsultaRead,
    status_code=status.HTTP_201_CREATED,
)
def criar_consulta(
    dados: ConsultaCreate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(
        exigir_papeis(
            PapelUsuario.PROFISSIONAL,
            PapelUsuario.ADMINISTRADOR,
        )
    ),
) -> Consulta:
    garantir_profissional_da_consulta(
        usuario,
        dados.profissional_id,
    )

    if dados.status in STATUS_OCUPA_HORARIO:
        verificar_conflito_de_horario(
            session=session,
            profissional_id=dados.profissional_id,
            data_hora=dados.data_hora,
        )

    consulta = Consulta(**dados.model_dump())

    session.add(consulta)
    session.commit()
    session.refresh(consulta)

    return consulta


@router.get(
    "/{consulta_id}",
    response_model=ConsultaRead,
)
def buscar_consulta(
    consulta_id: UUID,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(obter_usuario_atual),
) -> Consulta:
    consulta = session.get(Consulta, consulta_id)

    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )

    garantir_leitura_consulta(usuario, consulta)

    return consulta


@router.put(
    "/{consulta_id}",
    response_model=ConsultaRead,
)
def atualizar_consulta(
    consulta_id: UUID,
    dados: ConsultaUpdate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(
        exigir_papeis(
            PapelUsuario.PROFISSIONAL,
            PapelUsuario.ADMINISTRADOR,
        )
    ),
) -> Consulta:
    consulta = session.get(Consulta, consulta_id)

    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )

    garantir_gerenciamento_consulta(usuario, consulta)

    campos_atualizados = dados.model_dump(
        exclude_unset=True,
    )

    novo_profissional_id = campos_atualizados.get(
        "profissional_id",
        consulta.profissional_id,
    )

    nova_data_hora = campos_atualizados.get(
        "data_hora",
        consulta.data_hora,
    )

    novo_status = campos_atualizados.get(
        "status",
        consulta.status,
    )

    if "profissional_id" in campos_atualizados:
        garantir_profissional_da_consulta(
            usuario,
            novo_profissional_id,
        )

    if novo_status in STATUS_OCUPA_HORARIO:
        verificar_conflito_de_horario(
            session=session,
            profissional_id=novo_profissional_id,
            data_hora=nova_data_hora,
            consulta_id=consulta.id,
        )

    for campo, valor in campos_atualizados.items():
        setattr(consulta, campo, valor)

    session.add(consulta)
    session.commit()
    session.refresh(consulta)

    return consulta


@router.delete(
    "/{consulta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def excluir_consulta(
    consulta_id: UUID,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(
        exigir_papeis(
            PapelUsuario.PROFISSIONAL,
            PapelUsuario.ADMINISTRADOR,
        )
    ),
) -> Response:
    consulta = session.get(Consulta, consulta_id)

    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )

    garantir_gerenciamento_consulta(usuario, consulta)

    session.delete(consulta)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)