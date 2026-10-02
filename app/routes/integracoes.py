from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.auth import exigir_cliente_m2m_com_escopo
from app.database import get_session
from app.models import (
    ClienteM2M,
    Consulta,
    EscopoM2M,
    HorariosDisponiveisRead,
    StatusConsulta,
)


router = APIRouter(
    prefix="/integracoes",
    tags=["Integrações"],
)


@router.get(
    "/laboratorio/horarios",
    response_model=HorariosDisponiveisRead,
)
def consultar_horarios_disponiveis(
    data: date = Query(
        ...,
        description="Data no formato AAAA-MM-DD",
    ),
    profissional_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    _: ClienteM2M = Depends(
        exigir_cliente_m2m_com_escopo(
            EscopoM2M.AGENDA_HORARIOS.value
        )
    ),
) -> HorariosDisponiveisRead:
    condicoes = [
        func.date(Consulta.data_hora) == data.isoformat(),
        Consulta.status != StatusConsulta.CANCELADA,
    ]

    if profissional_id is not None:
        condicoes.append(
            Consulta.profissional_id == profissional_id
        )

    statement = select(Consulta).where(*condicoes)
    consultas = list(session.exec(statement).all())

    horarios_ocupados = {
        consulta.data_hora.strftime("%H:%M")
        for consulta in consultas
    }

    horarios_disponiveis: list[str] = []

    for minuto_do_dia in range(
        8 * 60,
        18 * 60,
        30,
    ):
        hora = minuto_do_dia // 60
        minuto = minuto_do_dia % 60
        horario = f"{hora:02d}:{minuto:02d}"

        if horario not in horarios_ocupados:
            horarios_disponiveis.append(
                f"{data.isoformat()}T{horario}:00-03:00"
            )

    return HorariosDisponiveisRead(
        data=data.isoformat(),
        profissional_id=profissional_id,
        horarios_disponiveis=horarios_disponiveis,
    )