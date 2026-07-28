# -*- coding: utf-8 -*-
"""Testes do motor de indicadores (src/indicadores/motor.py).

Os valores esperados são conferíveis à mão a partir da fixture
`grupo_simples` (ver tests/conftest.py): 2 dias trabalhados, 30 procedimentos,
20 agendados e 5 faltosos.
"""
import pandas as pd
import pytest

from src.indicadores.motor import calcular_grupo, calcular_serie
from conftest import lancamento


def test_indicadores_do_mes_batem_com_a_conta_manual(grupo_simples):
    ind = calcular_grupo(grupo_simples)

    assert ind["dias_trabalhados"] == 2
    assert ind["total_procedimentos"] == 30
    assert ind["media_proc_dia"] == 15.0
    # retorno (6) + 1ª consulta (5) + urgência (3)
    assert ind["atendimentos"] == 14
    assert ind["media_atend_dia"] == 7.0
    assert ind["agendados"] == 20
    assert ind["faltosos"] == 5
    assert ind["media_faltas_dia"] == 2.5
    assert ind["taxa_absenteismo_pct"] == 25.0
    assert ind["primeiras_consultas"] == 5
    assert ind["trat_completados"] == 4
    assert ind["razao_tc"] == 0.8
    assert ind["urgencias"] == 3
    assert ind["art"] == 2
    assert ind["preventivos"] == 10
    assert ind["media_prev_dia"] == 5.0
    assert ind["exodontias"] == 2
    assert ind["pct_exodontias"] == 6.7
    assert ind["restauracoes"] == 8
    assert ind["razao_rest_exo"] == 4.0


def test_dias_trabalhados_ignora_linhas_de_agenda():
    """Dia com apenas agendados/faltosos não é dia trabalhado.

    Regra do projeto: agenda registra intenção, não presença.
    """
    df = pd.DataFrame([
        lancamento(dia=10, categoria="agenda", codigo_sigtap=None,
                   chave="agendados", quantidade=12),
        lancamento(dia=10, categoria="agenda", codigo_sigtap=None,
                   chave="faltosos", quantidade=3),
        lancamento(dia=11, quantidade=4),
    ])
    assert calcular_grupo(df)["dias_trabalhados"] == 1


@pytest.mark.parametrize("indicador", [
    "taxa_absenteismo_pct", "razao_tc", "razao_rest_exo",
    "media_proc_dia", "media_atend_dia",
])
def test_divisor_zero_devolve_none_e_nao_explode(indicador):
    """Sem agendados, sem 1ª consulta, sem exodontia ou sem dia trabalhado
    o indicador é ausente — nunca 0 nem exceção."""
    vazio = pd.DataFrame([
        lancamento(categoria="agenda", codigo_sigtap=None, chave="agendados",
                   quantidade=0),
    ])
    assert calcular_grupo(vazio)[indicador] is None


def test_total_e_recalculado_dos_lancamentos_diarios():
    """Nunca confiar na coluna TOTAL: o motor só enxerga lançamentos."""
    df = pd.DataFrame([
        lancamento(dia=d, quantidade=1.0) for d in range(1, 6)
    ])
    assert calcular_grupo(df)["total_procedimentos"] == 5


def test_serie_gera_uma_linha_por_profissional_e_competencia(grupo_simples):
    outro = grupo_simples.copy()
    outro["profissional"] = "Sicrano De Tal"
    outro["mes"] = 4
    serie = calcular_serie(pd.concat([grupo_simples, outro], ignore_index=True))

    assert len(serie) == 2
    assert set(serie["competencia"]) == {"2025-03", "2025-04"}
    assert serie["funcao"].tolist() == ["dentista", "dentista"]
    # a matriz precisa trazer os indicadores, não só a identificação
    assert {"media_atend_dia", "taxa_absenteismo_pct"} <= set(serie.columns)
