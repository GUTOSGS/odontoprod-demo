# -*- coding: utf-8 -*-
"""
OdontoProd — Módulo 3: Motor de indicadores de produtividade e perfil
assistencial, calculados por profissional × competência (mês).

Cada indicador é uma função pura sobre o subconjunto (grupo) de lançamentos
de um profissional em uma competência. Adicionar um indicador novo =
adicionar uma função e registrá-la em INDICADORES.
"""

import pandas as pd

# ----------------------------------------------------------------------
# Códigos SIGTAP usados nos indicadores
# ----------------------------------------------------------------------
COD_PRIMEIRA_CONSULTA = "03.01.01.015-3"
COD_ART = "03.07.01.007-4"
COD_URGENCIA = "03.01.06.003-7"

COD_EXODONTIAS = {
    "04.14.02.012-0",  # exodontia de dente decíduo
    "04.14.02.013-8",  # exodontia de dente permanente
    "04.14.02.043-0",  # exodontia de dente supranumerário
}

COD_RESTAURACOES = {
    "03.07.01.003-1",  # permanente anterior resina
    "03.07.01.008-2",  # decíduo posterior resina
    "03.07.01.009-0",  # decíduo posterior amálgama
    "03.07.01.010-4",  # decíduo posterior ionômero
    "03.07.01.011-2",  # decíduo anterior resina
    "03.07.01.012-0",  # permanente posterior resina
    "03.07.01.013-9",  # permanente posterior amálgama
}

COD_PREVENTIVOS = {
    "01.01.02.001-5",  # flúor gel coletivo
    "01.01.02.002-3",  # bochecho fluorado
    "01.01.02.003-1",  # escovação supervisionada
    "01.01.02.005-8",  # cariostático
    "01.01.02.006-6",  # selante
    "01.01.02.007-4",  # flúor individual
    "01.01.02.008-2",  # evidenciação de placa
    "01.01.02.009-0",  # selamento provisório
    "01.01.02.010-4",  # orientação de higiene bucal
    "03.07.03.004-0",  # profilaxia / remoção de placa
}

CHAVES_AGENDA_NAO_CLINICAS = {"agendados", "faltosos"}


# ----------------------------------------------------------------------
# Auxiliares sobre o grupo (lançamentos de 1 profissional × 1 competência)
# ----------------------------------------------------------------------
def _proc(g: pd.DataFrame) -> pd.DataFrame:
    return g[g["categoria"] == "procedimento"]


def _agenda(g: pd.DataFrame, chave: str) -> float:
    m = (g["categoria"] == "agenda") & (g["chave"] == chave)
    return float(g.loc[m, "quantidade"].sum())


def _soma_cod(g: pd.DataFrame, codigos) -> float:
    if isinstance(codigos, str):
        codigos = {codigos}
    p = _proc(g)
    return float(p.loc[p["codigo_sigtap"].isin(codigos), "quantidade"].sum())


def dias_trabalhados(g: pd.DataFrame) -> int:
    """Dias com ao menos um lançamento clínico (exclui agendados/faltosos)."""
    clinico = g[~g["chave"].isin(CHAVES_AGENDA_NAO_CLINICAS)]
    return int(clinico["dia"].nunique())


def atendimentos(g: pd.DataFrame) -> float:
    """Consultas de retorno + no dia + manutenção + 1ª programática + urgência."""
    return (_agenda(g, "consulta_retorno") + _agenda(g, "consulta_no_dia")
            + _agenda(g, "consulta_manutencao")
            + _soma_cod(g, COD_PRIMEIRA_CONSULTA) + _soma_cod(g, COD_URGENCIA))


# ----------------------------------------------------------------------
# Registro central: nome do indicador -> função(grupo) -> valor
# ----------------------------------------------------------------------
def _por_dia(valor: float, dias: int) -> float | None:
    return round(valor / dias, 2) if dias else None


def calcular_grupo(g: pd.DataFrame) -> dict:
    """Calcula todos os indicadores de um profissional em uma competência."""
    dias = dias_trabalhados(g)
    total_proc = float(_proc(g)["quantidade"].sum())
    atend = atendimentos(g)
    agendados = _agenda(g, "agendados")
    faltosos = _agenda(g, "faltosos")
    primeiras = _soma_cod(g, COD_PRIMEIRA_CONSULTA)
    tc = _agenda(g, "tratamento_completado")
    urgencias = _soma_cod(g, COD_URGENCIA)
    art = _soma_cod(g, COD_ART)
    prev = _soma_cod(g, COD_PREVENTIVOS)
    exo = _soma_cod(g, COD_EXODONTIAS)
    rest = _soma_cod(g, COD_RESTAURACOES)

    return {
        "dias_trabalhados": dias,
        "total_procedimentos": int(total_proc),
        "media_proc_dia": _por_dia(total_proc, dias),
        "atendimentos": int(atend),
        "media_atend_dia": _por_dia(atend, dias),
        "agendados": int(agendados),
        "faltosos": int(faltosos),
        "media_faltas_dia": _por_dia(faltosos, dias),
        "taxa_absenteismo_pct": (round(100 * faltosos / agendados, 1)
                                 if agendados else None),
        "primeiras_consultas": int(primeiras),
        "trat_completados": int(tc),
        "razao_tc": round(tc / primeiras, 2) if primeiras else None,
        "urgencias": int(urgencias),
        "art": int(art),
        "media_art_dia": _por_dia(art, dias),
        "preventivos": int(prev),
        "media_prev_dia": _por_dia(prev, dias),
        "exodontias": int(exo),
        "pct_exodontias": (round(100 * exo / total_proc, 1)
                           if total_proc else None),
        "restauracoes": int(rest),
        "razao_rest_exo": round(rest / exo, 2) if exo else None,
    }


def calcular_serie(dados: pd.DataFrame) -> pd.DataFrame:
    """Calcula a matriz de indicadores profissional × competência.

    Espera o formato longo da base canônica (producao_canonica.parquet).
    """
    linhas = []
    grupos = dados.groupby(["profissional", "ano", "mes"], sort=True)
    for (prof, ano, mes), g in grupos:
        linha = {
            "profissional": prof,
            "funcao": g["funcao"].mode().iat[0] if not g["funcao"].mode().empty else "",
            "unidade": g["unidade"].mode().iat[0] if not g["unidade"].mode().empty else "",
            "ano": int(ano),
            "mes": int(mes),
            "competencia": f"{int(ano)}-{int(mes):02d}",
        }
        linha.update(calcular_grupo(g))
        linhas.append(linha)
    return pd.DataFrame(linhas)
