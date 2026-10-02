from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


LIMITE_CVSS = 7.0


def carregar_json(caminho: str) -> Any:
    arquivo = Path(caminho)

    if not arquivo.exists():
        raise FileNotFoundError(f"Relatório não encontrado: {arquivo}")

    with arquivo.open("r", encoding="utf-8") as arquivo_json:
        return json.load(arquivo_json)


def converter_score(valor: Any) -> float | None:
    if valor is None:
        return None

    if isinstance(valor, dict):
        for chave in ("score", "base_score", "baseScore", "severity"):
            score = converter_score(valor.get(chave))
            if score is not None:
                return score
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip().upper()

    if texto in {"CRITICAL", "CRÍTICO"}:
        return 9.0

    if texto in {"HIGH", "ALTO", "ALTA"}:
        return 8.0

    if texto in {"MEDIUM", "MÉDIO", "MEDIA", "MÉDIA"}:
        return 5.0

    if texto in {"LOW", "BAIXO", "BAIXA"}:
        return 2.0

    try:
        return float(texto)
    except ValueError:
        return None


def verificar_bandit(caminho: str, falhas: list[str]) -> None:
    relatorio = carregar_json(caminho)
    resultados = relatorio.get("results", [])

    for resultado in resultados:
        severidade = resultado.get("issue_severity", "UNKNOWN")
        score = converter_score(severidade)

        arquivo = resultado.get("filename", "arquivo desconhecido")
        linha = resultado.get("line_number", "?")
        descricao = resultado.get(
            "issue_text",
            "vulnerabilidade não detalhada",
        )

        if score is not None and score >= LIMITE_CVSS:
            falhas.append(
                f"[SAST] {severidade} em {arquivo}:{linha} - {descricao}"
            )


def obter_vulnerabilidades_pip(relatorio: Any):
    if isinstance(relatorio, list):
        dependencias = relatorio
    else:
        dependencias = relatorio.get("dependencies", [])

    for dependencia in dependencias:
        nome = dependencia.get("name", "dependência desconhecida")
        versao = dependencia.get("version", "versão desconhecida")

        for vulnerabilidade in dependencia.get("vulns", []):
            yield nome, versao, vulnerabilidade


def verificar_pip_audit(caminho: str, falhas: list[str]) -> None:
    relatorio = carregar_json(caminho)
    encontrou_vulnerabilidade = False

    for nome, versao, vulnerabilidade in obter_vulnerabilidades_pip(
        relatorio
    ):
        encontrou_vulnerabilidade = True

        identificador = vulnerabilidade.get(
            "id",
            vulnerabilidade.get("alias", "identificador desconhecido"),
        )

        score = None

        for chave in ("cvss", "cvss_score", "score", "severity"):
            score = converter_score(vulnerabilidade.get(chave))
            if score is not None:
                break

        if score is None:
            falhas.append(
                "[SCA] "
                f"{nome} {versao} possui {identificador}, "
                "mas não há score verificável; revisão obrigatória."
            )
        elif score >= LIMITE_CVSS:
            falhas.append(
                "[SCA] "
                f"{nome} {versao} possui {identificador} "
                f"com score {score:.1f}."
            )

    if not encontrou_vulnerabilidade:
        print("[SCA] Nenhuma vulnerabilidade conhecida encontrada.")


def obter_alertas_zap(relatorio: Any) -> list[dict[str, Any]]:
    alertas: list[dict[str, Any]] = []

    if isinstance(relatorio, dict):
        for site in relatorio.get("site", []):
            alertas.extend(site.get("alerts", []))

        alertas.extend(relatorio.get("alerts", []))

    return alertas


def score_alerta_zap(alerta: dict[str, Any]) -> float | None:
    risco = alerta.get("riskcode")

    if risco is not None:
        try:
            codigo = int(str(risco))
        except ValueError:
            codigo = None

        if codigo == 3:
            return 8.0

        if codigo == 2:
            return 5.0

        if codigo == 1:
            return 2.0

        if codigo == 0:
            return 0.0

    descricao_risco = alerta.get("riskdesc", "")
    return converter_score(descricao_risco.split()[0] if descricao_risco else None)


def verificar_zap(caminho: str, falhas: list[str]) -> None:
    relatorio = carregar_json(caminho)
    alertas = obter_alertas_zap(relatorio)

    for alerta in alertas:
        score = score_alerta_zap(alerta)

        if score is not None and score >= LIMITE_CVSS:
            nome = alerta.get("name", "alerta sem nome")
            risco = alerta.get("riskdesc", "risco não informado")

            falhas.append(
                f"[DAST] {nome} ({risco})"
            )

    print(f"[DAST] Alertas analisados: {len(alertas)}")


def executar(args: argparse.Namespace) -> int:
    falhas: list[str] = []
    relatorios_analisados = 0

    try:
        if args.bandit:
            verificar_bandit(args.bandit, falhas)
            relatorios_analisados += 1

        if args.pip_audit:
            verificar_pip_audit(args.pip_audit, falhas)
            relatorios_analisados += 1

        if args.zap:
            verificar_zap(args.zap, falhas)
            relatorios_analisados += 1

    except (FileNotFoundError, json.JSONDecodeError) as erro:
        print(f"ERRO ao ler relatório: {erro}", file=sys.stderr)
        return 1

    if relatorios_analisados == 0:
        print(
            "Nenhum relatório foi informado. "
            "Use --bandit, --pip-audit ou --zap.",
            file=sys.stderr,
        )
        return 1

    if falhas:
        print("\nSECURITY GATE: BLOQUEADO")
        print(
            "Critério: bloquear score CVSS igual ou superior a "
            f"{LIMITE_CVSS:.1f} ou severidade High/Critical."
        )

        for falha in falhas:
            print(f"- {falha}")

        return 1

    print("\nSECURITY GATE: APROVADO")
    print(
        "Nenhuma vulnerabilidade High/Critical ou com CVSS "
        f"igual ou superior a {LIMITE_CVSS:.1f} foi encontrada."
    )

    return 0


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aplica a política de severidade do security gate."
    )

    parser.add_argument("--bandit")
    parser.add_argument("--pip-audit")
    parser.add_argument("--zap")

    return parser


if __name__ == "__main__":
    argumentos = criar_parser().parse_args()
    sys.exit(executar(argumentos))