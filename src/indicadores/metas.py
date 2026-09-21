# -*- coding: utf-8 -*-
"""
OdontoProd — Metas de 2026 para os velocímetros do painel.

Fonte: o resumo municipal de indicadores de saúde bucal para o planejamento
2026 (coordenação municipal), que reúne:

  * os seis indicadores ministeriais B1-B6 (notas metodológicas do MS,
    maio/2026), com faixas Ótimo/Bom/Suficiente/Regular;
  * as sete metas operacionais da RASB do município.

Regras de cálculo adotadas (as do próprio documento):
  * agregar somando numeradores e denominadores — nunca média simples de
    percentuais com bases diferentes;
  * denominador zero -> "não calculável" (None).

Limites que o painel precisa declarar:
  * B1 e B4 dependem de população vinculada (SIAPS/SCNES): não calculáveis
    a partir das planilhas;
  * B2, B3, B5 e B6 aqui são APROXIMAÇÕES por profissional, com os códigos
    SIGTAP das planilhas locais; o valor oficial é apurado no SIAPS por
    equipe (INE), com os códigos elegíveis da nota;
  * o documento não define se as metas operacionais são teto ou mínimo.
    Os sentidos abaixo são PROPOSTA até a pactuação — ajuste aqui.
"""

import pandas as pd

from src.indicadores.motor import (COD_ART, COD_EXODONTIAS, COD_PREVENTIVOS,
                                   COD_RESTAURACOES)

# preventivos de natureza coletiva ficam fora de B3/B5 (a nota fala em
# procedimentos INDIVIDUAIS)
COD_PREVENTIVOS_COLETIVOS = {
    "01.01.02.001-5",  # flúor gel coletivo
    "01.01.02.002-3",  # bochecho fluorado
    "01.01.02.003-1",  # escovação supervisionada
}
COD_PREVENTIVOS_INDIVIDUAIS = COD_PREVENTIVOS - COD_PREVENTIVOS_COLETIVOS
COD_PROFILAXIA = "03.07.03.004-0"          # 03.07, mas é preventivo

# ----------------------------------------------------------------------
# Faixas ministeriais
# ----------------------------------------------------------------------
OTIMO, BOM, SUFICIENTE, REGULAR = "Ótimo", "Bom", "Suficiente", "Regular"
SEM_FAIXA = "Sem faixa definida"

CORES = {OTIMO: "#2e8b6e", BOM: "#8cc152", SUFICIENTE: "#f0b429",
         REGULAR: "#c0504d", SEM_FAIXA: "#b0b0b0"}


def _faixa_b2(v):
    if v > 100:
        return SEM_FAIXA      # a ficha não classifica; exige análise
    if v > 75:
        return OTIMO
    if v > 50:
        return BOM
    if v > 25:
        return SUFICIENTE
    return REGULAR


def _faixa_b3(v):
    if 3 <= v < 10:
        return OTIMO
    if 10 <= v < 12:
        return BOM
    if 12 <= v < 14:
        return SUFICIENTE
    return REGULAR            # < 3% também é regular na ficha


def _faixa_b5(v):
    if 65 <= v <= 85:
        return OTIMO
    if 55 <= v < 65:
        return BOM
    if 40 <= v < 55:
        return SUFICIENTE
    return REGULAR            # > 85% também é regular na ficha


def _faixa_b6(v):
    if v > 8:
        return OTIMO
    if v > 6:
        return BOM
    if v > 3:
        return SUFICIENTE
    return REGULAR


MINISTERIAIS = [
    {"codigo": "B1", "nome": "Primeira consulta programada",
     "calculavel": False, "otima": "> 1,25%",
     "motivo": "denominador é a população vinculada à eSF/eAP (SIAPS)"},
    {"codigo": "B2", "nome": "Tratamento concluído", "calculavel": True,
     "otima": "> 75% e ≤ 100%", "faixa": _faixa_b2, "eixo": 120,
     "passos": [(0, 25, REGULAR), (25, 50, SUFICIENTE), (50, 75, BOM),
                (75, 100, OTIMO), (100, 120, SEM_FAIXA)],
     "formula": "tratamentos concluídos ÷ primeiras consultas programáticas"},
    {"codigo": "B3", "nome": "Taxa de exodontia", "calculavel": True,
     "otima": "≥ 3% e < 10%", "faixa": _faixa_b3, "eixo": 20,
     "passos": [(0, 3, REGULAR), (3, 10, OTIMO), (10, 12, BOM),
                (12, 14, SUFICIENTE), (14, 20, REGULAR)],
     "formula": "exodontias ÷ (preventivos individuais + curativos + "
                "exodontias)"},
    {"codigo": "B4", "nome": "Escovação supervisionada",
     "calculavel": False, "otima": "> 1%",
     "motivo": "denominador são as crianças de 6 a 12 anos vinculadas (SIAPS)"},
    {"codigo": "B5", "nome": "Preventivos individuais", "calculavel": True,
     "otima": "≥ 65% e ≤ 85%", "faixa": _faixa_b5, "eixo": 100,
     "passos": [(0, 40, REGULAR), (40, 55, SUFICIENTE), (55, 65, BOM),
                (65, 85, OTIMO), (85, 100, REGULAR)],
     "formula": "preventivos individuais ÷ (preventivos individuais + "
                "curativos + exodontias)"},
    {"codigo": "B6", "nome": "Tratamento restaurador atraumático (ART)",
     "calculavel": True, "otima": "> 8%", "faixa": _faixa_b6, "eixo": 15,
     "passos": [(0, 3, REGULAR), (3, 6, SUFICIENTE), (6, 8, BOM),
                (8, 15, OTIMO)],
     "formula": "ART ÷ (restaurações + ART)"},
]

# ----------------------------------------------------------------------
# Metas operacionais da RASB do município
# sentido: "minimo" (atingiu se >=), "teto" (atingiu se <=) ou None
# ----------------------------------------------------------------------
OPERACIONAIS = [
    {"codigo": "O1", "nome": "Agendamentos por dia", "meta": 8,
     "sentido": "minimo", "unidade": "", "casas": 1,
     "formula": "agendados ÷ dias trabalhados (competências com agenda)"},
    {"codigo": "O2", "nome": "Faltas por dia", "meta": None,
     "sentido": None, "unidade": "", "casas": 2,
     "formula": "faltosos ÷ dias trabalhados (competências com agenda)",
     "nota": "sem meta: os 10% informados são percentual (a pactuar)"},
    {"codigo": "O3", "nome": "Faltas (% dos agendados)", "meta": 10,
     "sentido": "teto", "unidade": "%", "casas": 1,
     "formula": "faltosos ÷ agendados × 100"},
    {"codigo": "O4", "nome": "Dias trabalhados por mês", "meta": 18,
     "sentido": "minimo", "unidade": "", "casas": 1,
     "formula": "soma dos dias trabalhados ÷ profissionais × meses"},
    {"codigo": "O5", "nome": "Urgências por dia", "meta": 2,
     "sentido": "teto", "unidade": "", "casas": 2,
     "formula": "urgências ÷ dias trabalhados"},
    {"codigo": "O6", "nome": "Urgências (% das consultas)", "meta": 20,
     "sentido": "teto", "unidade": "%", "casas": 1,
     "formula": "urgências ÷ atendimentos × 100"},
    {"codigo": "O7", "nome": "Consultas por tratamento completado",
     "meta": 5, "sentido": "teto", "unidade": "", "casas": 1,
     "formula": "(atendimentos − urgências) ÷ tratamentos completados — "
                "aproximação: a planilha não identifica o episódio"},
]


def _razao(num, den, escala=1.0):
    return round(escala * num / den, 2) if den else None


def calcular(ind: pd.DataFrame, prod: pd.DataFrame) -> dict:
    """Valores dos indicadores com meta, somando numeradores e denominadores.

    `ind` é a matriz profissional × competência (indicadores_mensais) e
    `prod` a base de lançamentos, ambos já filtrados no mesmo recorte.
    """
    com_agenda = ind[ind["agendados"] > 0]
    dias_ag = com_agenda["dias_trabalhados"].sum()
    dias = ind["dias_trabalhados"].sum()
    urg = ind["urgencias"].sum()
    atend = ind["atendimentos"].sum()

    p = prod[prod["categoria"] == "procedimento"]
    cod = p["codigo_sigtap"].astype(str)
    q = p["quantidade"]
    prev_ind = q[cod.isin(COD_PREVENTIVOS_INDIVIDUAIS)].sum()
    exo = q[cod.isin(COD_EXODONTIAS)].sum()
    curativos = q[cod.str.startswith("03.07.") & (cod != COD_PROFILAXIA)].sum()
    art = q[cod == COD_ART].sum()
    rest = q[cod.isin(COD_RESTAURACOES)].sum()
    base_individual = prev_ind + curativos + exo

    return {
        "B2": _razao(ind["trat_completados"].sum(),
                     ind["primeiras_consultas"].sum(), 100),
        "B3": _razao(exo, base_individual, 100),
        "B5": _razao(prev_ind, base_individual, 100),
        "B6": _razao(art, rest + art, 100),
        "O1": _razao(com_agenda["agendados"].sum(), dias_ag),
        "O2": _razao(com_agenda["faltosos"].sum(), dias_ag),
        "O3": _razao(com_agenda["faltosos"].sum(),
                     com_agenda["agendados"].sum(), 100),
        "O4": _razao(dias, len(ind)),
        "O5": _razao(urg, dias),
        "O6": _razao(urg, atend, 100),
        "O7": _razao(atend - urg, ind["trat_completados"].sum()),
    }


def atingiu(valor, spec) -> bool | None:
    """Meta operacional atingida? None quando não há meta ou valor."""
    if valor is None or pd.isna(valor) or spec["sentido"] is None:
        return None
    if spec["sentido"] == "minimo":
        return valor >= spec["meta"]
    return valor <= spec["meta"]


def por_profissional(ind: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por profissional com os valores de `calcular`."""
    linhas = []
    for prof, g in ind.groupby("profissional"):
        valores = calcular(g, prod[prod["profissional"] == prof])
        linhas.append({"profissional": prof, **valores})
    return pd.DataFrame(linhas)
