from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import (
    ConfigDict,
    Field as PydanticField,
    field_validator,
    model_validator,
)
from sqlmodel import Field, SQLModel


USERNAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,49}$"
MFA_PATTERN = r"^[A-Za-z0-9]{6,12}$"
NOME_CLIENTE_PATTERN = r"^[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 .&'_-]{2,99}$"


class PapelUsuario(str, Enum):
    RECEPCIONISTA = "recepcionista"
    PROFISSIONAL = "profissional"
    ADMINISTRADOR = "administrador"


class StatusConsulta(str, Enum):
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    CONCLUIDA = "concluida"


class EscopoM2M(str, Enum):
    AGENDA_HORARIOS = "agenda:horarios"


class ConsultaBase(SQLModel):
    model_config = ConfigDict(extra="forbid")

    paciente_id: UUID
    profissional_id: UUID
    data_hora: datetime
    status: StatusConsulta = StatusConsulta.AGENDADA
    observacoes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("observacoes")
    @classmethod
    def validar_observacoes(
        cls,
        valor: Optional[str],
    ) -> Optional[str]:
        if valor is not None and "\x00" in valor:
            raise ValueError("observacoes contém caractere inválido")

        return valor


class Consulta(ConsultaBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)


class ConsultaCreate(ConsultaBase):
    @field_validator("data_hora")
    @classmethod
    def validar_fuso_horario(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError(
                "data_hora deve incluir informação de fuso horário"
            )

        return valor


class ConsultaRead(ConsultaBase):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID


class ConsultaUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    paciente_id: Optional[UUID] = None
    profissional_id: Optional[UUID] = None
    data_hora: Optional[datetime] = None
    status: Optional[StatusConsulta] = None
    observacoes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("data_hora")
    @classmethod
    def validar_fuso_horario(
        cls,
        valor: Optional[datetime],
    ) -> Optional[datetime]:
        if valor is not None and (
            valor.tzinfo is None or valor.utcoffset() is None
        ):
            raise ValueError(
                "data_hora deve incluir informação de fuso horário"
            )

        return valor

    @field_validator("observacoes")
    @classmethod
    def validar_observacoes(
        cls,
        valor: Optional[str],
    ) -> Optional[str]:
        if valor is not None and "\x00" in valor:
            raise ValueError("observacoes contém caractere inválido")

        return valor


class Usuario(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    senha_hash: str = Field(max_length=255)
    papel: PapelUsuario = Field(default=PapelUsuario.RECEPCIONISTA)
    profissional_id: Optional[UUID] = Field(default=None, index=True)
    mfa_habilitado: bool = False
    mfa_codigo_hash: Optional[str] = Field(default=None, max_length=255)
    ativo: bool = True


class UsuarioCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    username: str = PydanticField(
        min_length=3,
        max_length=50,
        pattern=USERNAME_PATTERN,
    )
    senha: str = PydanticField(min_length=8, max_length=72)
    papel: PapelUsuario = PapelUsuario.RECEPCIONISTA
    profissional_id: Optional[UUID] = None
    mfa_habilitado: bool = False
    mfa_codigo: Optional[str] = PydanticField(
        default=None,
        min_length=6,
        max_length=12,
        pattern=MFA_PATTERN,
    )

    @model_validator(mode="after")
    def validar_regras_do_usuario(self) -> "UsuarioCreate":
        if (
            self.papel == PapelUsuario.PROFISSIONAL
            and self.profissional_id is None
        ):
            raise ValueError(
                "profissional_id é obrigatório para usuários profissionais"
            )

        if self.papel == PapelUsuario.ADMINISTRADOR:
            if not self.mfa_habilitado or not self.mfa_codigo:
                raise ValueError(
                    "administradores devem possuir MFA habilitado e código MFA"
                )

        if self.mfa_habilitado and not self.mfa_codigo:
            raise ValueError(
                "mfa_codigo é obrigatório quando o MFA está habilitado"
            )

        return self


class BootstrapAdmin(SQLModel):
    model_config = ConfigDict(extra="forbid")

    username: str = PydanticField(
        min_length=3,
        max_length=50,
        pattern=USERNAME_PATTERN,
    )
    senha: str = PydanticField(min_length=8, max_length=72)
    mfa_codigo: str = PydanticField(
        min_length=6,
        max_length=12,
        pattern=MFA_PATTERN,
    )


class UsuarioRead(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    username: str
    papel: PapelUsuario
    profissional_id: Optional[UUID] = None
    mfa_habilitado: bool
    ativo: bool


class ClienteM2M(SQLModel, table=True):
    __tablename__ = "cliente_m2m"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: str = Field(index=True, unique=True, max_length=100)
    nome: str = Field(max_length=100)
    client_secret_hash: str = Field(max_length=255)
    escopos_json: str = Field(max_length=2000)
    ativo: bool = True


class ClienteM2MCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = PydanticField(
        min_length=3,
        max_length=100,
        pattern=NOME_CLIENTE_PATTERN,
    )
    escopos: list[EscopoM2M] = PydanticField(
        min_length=1,
        max_length=10,
    )

    @field_validator("escopos")
    @classmethod
    def validar_escopos(
        cls,
        valores: list[EscopoM2M],
    ) -> list[EscopoM2M]:
        if len(set(valores)) != len(valores):
            raise ValueError("Não é permitido repetir escopos")

        return valores


class ClienteM2MRead(SQLModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    client_id: str
    nome: str
    escopos: list[EscopoM2M]
    ativo: bool


class ClienteM2MCriado(ClienteM2MRead):
    client_secret: str


class HorariosDisponiveisRead(SQLModel):
    model_config = ConfigDict(extra="forbid")

    data: str
    profissional_id: Optional[UUID] = None
    horarios_disponiveis: list[str]


class Token(SQLModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    scope: Optional[str] = None