from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, Response, status

from app.config import settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def verificar_limite(
        self,
        chave: str,
        limite: int,
        janela_em_segundos: int,
    ) -> tuple[bool, int, int]:
        agora = monotonic()
        inicio_janela = agora - janela_em_segundos

        with self._lock:
            requisicoes = self._requests[chave]

            while (
                requisicoes
                and requisicoes[0] <= inicio_janela
            ):
                requisicoes.popleft()

            if len(requisicoes) >= limite:
                retry_after = max(
                    1,
                    int(
                        requisicoes[0]
                        + janela_em_segundos
                        - agora
                    )
                    + 1,
                )

                return False, 0, retry_after

            requisicoes.append(agora)

            restante = limite - len(requisicoes)

            return True, restante, 0

    def limpar(self) -> None:
        with self._lock:
            self._requests.clear()


login_rate_limiter = InMemoryRateLimiter()


def obter_identificador_cliente(request: Request) -> str:
    if request.client is None:
        return "cliente-desconhecido"

    return request.client.host


def limitar_login(
    request: Request,
    response: Response,
) -> None:
    identificador = obter_identificador_cliente(request)

    limite = settings.login_rate_limit_requests
    janela = settings.login_rate_limit_window_seconds

    permitido, restante, retry_after = (
        login_rate_limiter.verificar_limite(
            chave=identificador,
            limite=limite,
            janela_em_segundos=janela,
        )
    )

    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas de login. "
                "Aguarde antes de tentar novamente."
            ),
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limite),
                "X-RateLimit-Remaining": "0",
            },
        )

    response.headers["X-RateLimit-Limit"] = str(limite)
    response.headers["X-RateLimit-Remaining"] = str(restante)


def limpar_rate_limits() -> None:
    login_rate_limiter.limpar()