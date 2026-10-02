from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from app.auth import obter_usuario_atual
from app.database import get_session
from app.models import Consulta, PapelUsuario, Usuario


TEMPLATE_DIRECTORY = (
    Path(__file__).resolve().parent.parent / "templates"
)

templates = Jinja2Templates(
    directory=str(TEMPLATE_DIRECTORY)
)

# Garante o escape automático dos valores inseridos no HTML.
templates.env.autoescape = True


router = APIRouter(
    tags=["Agenda"],
)


@router.get(
    "/agenda",
    response_class=HTMLResponse,
)
def visualizar_agenda(
    request: Request,
    data: date = Query(...),
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(obter_usuario_atual),
) -> HTMLResponse:
    condicoes = [
        func.date(Consulta.data_hora) == data.isoformat()
    ]

    if usuario.papel == PapelUsuario.PROFISSIONAL:
        if usuario.profissional_id is None:
            consultas = []
        else:
            condicoes.append(
                Consulta.profissional_id == usuario.profissional_id
            )

            statement = (
                select(Consulta)
                .where(*condicoes)
                .order_by(Consulta.data_hora)
            )

            consultas = list(
                session.exec(statement).all()
            )
    else:
        statement = (
            select(Consulta)
            .where(*condicoes)
            .order_by(Consulta.data_hora)
        )

        consultas = list(
            session.exec(statement).all()
        )

    return templates.TemplateResponse(
        request=request,
        name="consultas.html",
        context={
            "consultas": consultas,
            "data": data,
        },
    )