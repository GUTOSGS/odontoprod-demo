"""Metas de 2026: indicadores ministeriais B1-B6 e metas operacionais.

Os valores de um recorte somam numeradores e denominadores; percentuais
com bases diferentes nunca são tirados por média. Denominador zero devolve
None ("não calculável").

B1 e B4 usam populações de referência pactuadas localmente, e não o
cadastro do SIAPS. B2, B3, B5 e B6 são aproximações por profissional com
os códigos SIGTAP das planilhas; o valor oficial é apurado por equipe.
"""

import pandas as pd

from src.indicadores.motor import (COD_ART, COD_EXODONTIAS, COD_PREVENTIVOS,
                                   COD_RESTAURACOES)

# B3 e B5 tratam de procedimentos individuais
COD_PREVENTIVOS_COLETIVOS = {
    "01.01.02.001-5",  # flúor gel coletivo
    "01.01.02.002-3",  # bochecho fluorado
    "01.01.02.003-1",  # escovação supervisionada
}
COD_PREVENTIVOS_INDIVIDUAIS = COD_PREVENTIVOS - COD_PREVENTIVOS_COLETIVOS
COD_PROFILAXIA = "03.07.03.004-0"  # está no grupo 03.07, mas é preventivo

# denominadores de B1 (pessoas vinculadas a cada cirurgião-dentista) e B4
# (crianças de 6 a 12 anos nessa população)
POPULACAO_POR_DENTISTA = 3500
PROPORCAO_6_A_12_ANOS = 0.18
CRIANCAS_POR_DENTISTA = round(POPULACAO_POR_DENTISTA * PROPORCAO_6_A_12_ANOS)
COD_ESCOVACAO = "01.01.02.003-1"

# a técnica não faz exodontia, restauração, tratamento concluído nem
# urgência; esses indicadores valem só para o cirurgião-dentista
CD, TSB = "dentista", "tecnico"
AMBOS = (CD, TSB)

OTIMO, BOM, SUFICIENTE, REGULAR = "Ótimo", "Bom", "Suficiente", "Regular"
SEM_FAIXA = "Sem faixa definida"

CORES = {OTIMO: "#2e8b6e", BOM: "#8cc152", SUFICIENTE: "#f0b429",
         REGULAR: "#c0504d", SEM_FAIXA: "#b0b0b0"}


def _acima_de(otimo, bom, suficiente):
    """Faixas em que o valor precisa superar cada limite."""
    def faixa(v):
        for limite, nome in ((otimo, OTIMO), (bom, BOM),
                             (suficiente, SUFICIENTE)):
            if v > limite:
                return nome
        return REGULAR
    return faixa


_faixa_b1 = _acima_de(1.25, 0.75, 0.25)
_faixa_b4 = _acima_de(1, 0.5, 0.25)
_faixa_b6 = _acima_de(8, 6, 3)


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


MINISTERIAIS = [
    {"codigo": "B1", "nome": "Primeira consulta programada",
     "funcoes": (CD,), "otima": "> 1,25%", "faixa": _faixa_b1, "eixo": 2,
     "passos": [(0, 0.25, REGULAR), (0.25, 0.75, SUFICIENTE),
                (0.75, 1.25, BOM), (1.25, 2, OTIMO)],
     "formula": (f"primeiras consultas programáticas no mês ÷ "
                 f"{POPULACAO_POR_DENTISTA} pessoas por cirurgião-dentista "
                 f"× 100 (população de referência pactuada, não o cadastro "
                 f"do SIAPS)")},
    {"codigo": "B2", "nome": "Tratamento concluído",
     "funcoes": (CD,), "otima": "> 75% e ≤ 100%", "faixa": _faixa_b2,
     "eixo": 120,
     "passos": [(0, 25, REGULAR), (25, 50, SUFICIENTE), (50, 75, BOM),
                (75, 100, OTIMO), (100, 120, SEM_FAIXA)],
     "formula": "tratamentos concluídos ÷ primeiras consultas programáticas"},
    {"codigo": "B3", "nome": "Taxa de exodontia",
     "funcoes": (CD,), "otima": "≥ 3% e < 10%", "faixa": _faixa_b3,
     "eixo": 20,
     "passos": [(0, 3, REGULAR), (3, 10, OTIMO), (10, 12, BOM),
                (12, 14, SUFICIENTE), (14, 20, REGULAR)],
     "formula": "exodontias ÷ (preventivos individuais + curativos + "
                "exodontias)"},
    {"codigo": "B4", "nome": "Escovação supervisionada",
     "funcoes": AMBOS, "otima": "> 1%", "faixa": _faixa_b4, "eixo": 2,
     "passos": [(0, 0.25, REGULAR), (0.25, 0.5, SUFICIENTE),
                (0.5, 1, BOM), (1, 2, OTIMO)],
     "formula": (f"participantes da escovação supervisionada no mês ÷ "
                 f"{CRIANCAS_POR_DENTISTA} crianças de 6 a 12 anos por "
                 f"equipe ({PROPORCAO_6_A_12_ANOS:.0%} de "
                 f"{POPULACAO_POR_DENTISTA} pessoas) × 100. A equipe é "
                 f"contada pelos cirurgiões-dentistas do recorte; num "
                 f"recorte só de técnicas, por técnica. A planilha não "
                 f"informa idade, então o numerador inclui todos os "
                 f"participantes")},
    {"codigo": "B5", "nome": "Preventivos individuais",
     "funcoes": AMBOS, "otima": "≥ 65% e ≤ 85%", "faixa": _faixa_b5,
     "eixo": 100,
     "passos": [(0, 40, REGULAR), (40, 55, SUFICIENTE), (55, 65, BOM),
                (65, 85, OTIMO), (85, 100, REGULAR)],
     "formula": "preventivos individuais ÷ (preventivos individuais + "
                "curativos + exodontias)"},
    {"codigo": "B6", "nome": "Tratamento restaurador atraumático (ART)",
     "funcoes": (CD,), "otima": "> 8%", "faixa": _faixa_b6, "eixo": 15,
     "passos": [(0, 3, REGULAR), (3, 6, SUFICIENTE), (6, 8, BOM),
                (8, 15, OTIMO)],
     "formula": "ART ÷ (restaurações + ART)"},
]

# sentido: "minimo" (quanto mais, melhor) ou "teto" (quanto menos, melhor)
OPERACIONAIS = [
    {"codigo": "O1", "nome": "Agendamentos por dia", "meta": 8,
     "sentido": "minimo", "unidade": "", "casas": 1, "funcoes": AMBOS,
     "formula": "agendados ÷ dias trabalhados (competências com agenda)"},
    {"codigo": "O2", "nome": "Faltas (% dos agendados)", "meta": 10,
     "sentido": "teto", "unidade": "%", "casas": 1, "funcoes": AMBOS,
     "formula": "faltosos ÷ agendados × 100"},
    {"codigo": "O3", "nome": "Dias trabalhados por mês", "meta": 17,
     "sentido": "minimo", "unidade": "", "casas": 1, "funcoes": AMBOS,
     "formula": "soma dos dias trabalhados ÷ profissionais × meses"},
    {"codigo": "O4", "nome": "Urgências por dia", "meta": 2,
     "sentido": "teto", "unidade": "", "casas": 2, "funcoes": (CD,),
     "formula": "urgências ÷ dias trabalhados"},
    {"codigo": "O5", "nome": "Urgências (% das consultas)", "meta": 20,
     "sentido": "teto", "unidade": "%", "casas": 1, "funcoes": (CD,),
     "formula": "urgências ÷ atendimentos × 100"},
    {"codigo": "O6", "nome": "Consultas por tratamento completado",
     "meta": 5, "sentido": "teto", "unidade": "", "casas": 1,
     "funcoes": (CD,),
     "formula": "(atendimentos − urgências) ÷ tratamentos completados "
                "(aproximação: a planilha não identifica o episódio)"},
]

# a meta é a fronteira do Ótimo; abaixo dela, três degraus de um terço da
# meta formam Bom, Suficiente e Regular, como nas faixas ministeriais
DEGRAUS = 3


def limites_operacional(spec) -> list:
    """Fronteiras da escala, do Ótimo ao Regular, na ordem do eixo.

    Devolve [(inicio, fim, faixa), ...] cobrindo 0 até o fim do eixo.
    """
    meta, passo = spec["meta"], spec["meta"] / DEGRAUS
    if spec["sentido"] == "minimo":
        return [(0, meta - 2 * passo, REGULAR),
                (meta - 2 * passo, meta - passo, SUFICIENTE),
                (meta - passo, meta, BOM),
                (meta, meta * 1.5, OTIMO)]
    return [(0, meta, OTIMO),
            (meta, meta + passo, BOM),
            (meta + passo, meta + 2 * passo, SUFICIENTE),
            (meta + 2 * passo, meta * 2, REGULAR)]


def faixa_operacional(valor, spec) -> str | None:
    """Em que faixa o valor cai. None quando não há valor.

    A meta entra no Ótimo: atingir a meta é atingir a meta.
    """
    if valor is None or pd.isna(valor):
        return None
    meta, passo = spec["meta"], spec["meta"] / DEGRAUS
    if spec["sentido"] == "minimo":
        cortes = [(meta, OTIMO), (meta - passo, BOM),
                  (meta - 2 * passo, SUFICIENTE)]
        return next((f for corte, f in cortes if valor >= corte), REGULAR)
    cortes = [(meta, OTIMO), (meta + passo, BOM),
              (meta + 2 * passo, SUFICIENTE)]
    return next((f for corte, f in cortes if valor <= corte), REGULAR)


def texto_faixas(spec) -> str:
    """A escala em uma linha, para a legenda e a documentação."""
    meta, passo = spec["meta"], spec["meta"] / DEGRAUS
    u = spec["unidade"]
    if spec["sentido"] == "minimo":
        cortes = [(OTIMO, "≥", meta), (BOM, "≥", meta - passo),
                  (SUFICIENTE, "≥", meta - 2 * passo),
                  (REGULAR, "<", meta - 2 * passo)]
    else:
        cortes = [(OTIMO, "≤", meta), (BOM, "≤", meta + passo),
                  (SUFICIENTE, "≤", meta + 2 * passo),
                  (REGULAR, ">", meta + 2 * passo)]
    return " · ".join(f"{faixa}: {sinal} {_num(corte)}{u}"
                      for faixa, sinal, corte in cortes)


def _num(v) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


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

    # B1 e B4 são mensais: população de referência × observações do recorte.
    # A população de B4 é contada pelo dentista, para não contar a mesma
    # equipe duas vezes; num recorte só de técnicas, conta-se cada uma.
    cd = ind[ind["funcao"] == CD] if "funcao" in ind else ind
    equipes_mes = len(cd) if len(cd) else len(ind)
    escovacao = q[cod == COD_ESCOVACAO].sum()

    return {
        "B1": _razao(cd["primeiras_consultas"].sum(),
                     POPULACAO_POR_DENTISTA * len(cd), 100),
        "B4": _razao(escovacao, CRIANCAS_POR_DENTISTA * equipes_mes, 100),
        "B2": _razao(ind["trat_completados"].sum(),
                     ind["primeiras_consultas"].sum(), 100),
        "B3": _razao(exo, base_individual, 100),
        "B5": _razao(prev_ind, base_individual, 100),
        "B6": _razao(art, rest + art, 100),
        "O1": _razao(com_agenda["agendados"].sum(), dias_ag),
        "O2": _razao(com_agenda["faltosos"].sum(),
                     com_agenda["agendados"].sum(), 100),
        "O3": _razao(dias, len(ind)),
        "O4": _razao(urg, dias),
        "O5": _razao(urg, atend, 100),
        "O6": _razao(atend - urg, ind["trat_completados"].sum()),
    }


def atingiu(valor, spec) -> bool | None:
    """Meta operacional atingida (ou seja, Ótimo)? None sem valor."""
    if valor is None or pd.isna(valor):
        return None
    if spec["sentido"] == "minimo":
        return valor >= spec["meta"]
    return valor <= spec["meta"]


def aplicaveis(specs, funcoes) -> list:
    """Filtra os indicadores que fazem sentido para as funções do recorte."""
    escolhidas = set(funcoes)
    return [s for s in specs if escolhidas & set(s.get("funcoes", AMBOS))]


def por_profissional(ind: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por profissional com os valores de `calcular`."""
    linhas = []
    for prof, g in ind.groupby("profissional"):
        valores = calcular(g, prod[prod["profissional"] == prof])
        linhas.append({"profissional": prof, **valores})
    return pd.DataFrame(linhas)
