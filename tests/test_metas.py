# -*- coding: utf-8 -*-
"""Testes das metas de 2026 (src/indicadores/metas.py): faixas ministeriais
nas fronteiras exatas das notas e agregação por soma de numeradores e
denominadores."""
import pandas as pd
import pytest

from src.indicadores import metas
from src.indicadores.metas import BOM, OTIMO, REGULAR, SEM_FAIXA, SUFICIENTE


def _spec(codigo):
    return next(m for m in metas.MINISTERIAIS if m["codigo"] == codigo)


@pytest.mark.parametrize("codigo,valor,esperado", [
    ("B2", 100.0, OTIMO), ("B2", 100.1, SEM_FAIXA), ("B2", 75.0, BOM),
    ("B2", 50.0, SUFICIENTE), ("B2", 25.0, REGULAR),
    ("B3", 2.99, REGULAR), ("B3", 3.0, OTIMO), ("B3", 10.0, BOM),
    ("B3", 12.0, SUFICIENTE), ("B3", 14.0, REGULAR),
    ("B5", 85.0, OTIMO), ("B5", 85.1, REGULAR), ("B5", 64.9, BOM),
    ("B5", 40.0, SUFICIENTE), ("B5", 39.9, REGULAR),
    ("B6", 8.0, BOM), ("B6", 8.01, OTIMO), ("B6", 3.0, REGULAR),
])
def test_faixas_nas_fronteiras_das_notas(codigo, valor, esperado):
    assert _spec(codigo)["faixa"](valor) == esperado


def test_passos_do_velocimetro_cobrem_o_eixo_sem_buraco():
    for m in metas.MINISTERIAIS:
        if not m["calculavel"]:
            continue
        passos = m["passos"]
        assert passos[0][0] == 0 and passos[-1][1] == m["eixo"]
        for (_, fim, _), (ini, _, _) in zip(passos, passos[1:]):
            assert fim == ini


def _ind(**colunas):
    base = {"profissional": ["A", "B"], "dias_trabalhados": [10, 10],
            "agendados": [80, 0], "faltosos": [8, 5], "atendimentos": [50, 50],
            "urgencias": [10, 30], "trat_completados": [9, 0],
            "primeiras_consultas": [10, 10]}
    base.update(colunas)
    return pd.DataFrame(base)


def _prod(itens):
    return pd.DataFrame([{"profissional": "A", "categoria": "procedimento",
                          "codigo_sigtap": c, "quantidade": q}
                         for c, q in itens],
                        columns=["profissional", "categoria",
                                 "codigo_sigtap", "quantidade"])


def test_agrega_somando_numeradores_e_denominadores():
    v = metas.calcular(_ind(), _prod([]))
    assert v["B2"] == 45.0            # 9 ÷ 20, não média de 90% e 0%
    assert v["O5"] == 2.0             # 40 urgências ÷ 20 dias
    assert v["O6"] == 40.0            # 40 ÷ 100 atendimentos


def test_agenda_so_conta_competencias_com_agendados():
    """B não registra agendados: seus 5 faltosos não inflam o percentual."""
    v = metas.calcular(_ind(), _prod([]))
    assert v["O1"] == 8.0             # 80 ÷ 10 dias de A
    assert v["O3"] == 10.0            # 8 ÷ 80


def test_denominador_zero_e_nao_calculavel():
    v = metas.calcular(_ind(primeiras_consultas=[0, 0],
                            agendados=[0, 0]), _prod([]))
    assert v["B2"] is None and v["O1"] is None and v["O3"] is None
    assert v["B3"] is None and v["B6"] is None


def test_b3_b5_b6_usam_so_procedimentos_individuais():
    v = metas.calcular(_ind(), _prod([
        ("01.01.02.007-4", 60),       # flúor individual -> preventivo
        ("01.01.02.003-1", 500),      # escovação supervisionada: coletivo
        ("03.07.03.004-0", 10),       # profilaxia -> preventivo, não curativo
        ("03.07.01.012-0", 20),       # restauração -> curativo
        ("03.07.01.007-4", 5),        # ART -> curativo
        ("04.14.02.013-8", 5),        # exodontia
    ]))
    # base individual = 70 preventivos + 25 curativos + 5 exodontias = 100
    assert v["B5"] == 70.0
    assert v["B3"] == 5.0
    assert v["B6"] == 20.0            # 5 ÷ (20 + 5)


@pytest.mark.parametrize("codigo,valor,esperado", [
    ("O1", 8, True), ("O1", 7.9, False),
    ("O3", 10, True), ("O3", 10.1, False),
    ("O2", 1.0, None), ("O1", None, None),
])
def test_atingiu_respeita_o_sentido_da_meta(codigo, valor, esperado):
    spec = next(m for m in metas.OPERACIONAIS if m["codigo"] == codigo)
    assert metas.atingiu(valor, spec) is esperado
