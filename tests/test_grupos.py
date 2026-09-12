# -*- coding: utf-8 -*-
"""Testes do classificador de grupos de produção (src/indicadores/grupos.py).

Regra central defendida no TCC: consultas/agenda, preventivos e curativos
NUNCA são somados juntos. Estes testes travam essa regra.
"""
import pandas as pd
import pytest

from src.indicadores.grupos import ORDEM_GRUPOS, aplicar_grupos, classificar
from conftest import lancamento


@pytest.mark.parametrize("codigo,esperado", [
    ("01.01.02.010-4", "Preventivos e ações coletivas"),
    ("01.01.02.006-6", "Preventivos e ações coletivas"),
    ("02.11.09.001-2", "Diagnósticos (radiografias, biópsias)"),
    ("03.01.01.015-3", "Atendimentos e consultas (SIGTAP)"),
    ("03.01.06.003-7", "Atendimentos e consultas (SIGTAP)"),
    ("03.07.01.012-0", "Curativos e reabilitadores"),
    ("07.01.03.001-0", "Curativos e reabilitadores"),
    ("04.14.02.013-8", "Cirúrgicos"),
    ("05.02.01.001-0", "Demais procedimentos SIGTAP"),
])
def test_classificacao_por_prefixo_sigtap(codigo, esperado):
    assert classificar(codigo, "procedimento") == esperado


def test_profilaxia_conta_como_preventivo_apesar_do_prefixo_clinico():
    """03.07.03.004-0 é 03.07 (clínico) mas de natureza preventiva."""
    assert classificar("03.07.03.004-0", "procedimento") == \
        "Preventivos e ações coletivas"


def test_agenda_e_linha_livre_ficam_em_grupos_proprios():
    assert classificar(None, "agenda") == "Consultas e agenda (sem código SIGTAP)"
    assert classificar(None, "outros") == "Outros registros (sem código SIGTAP)"
    # procedimento sem código também não pode virar produção clínica
    assert classificar("", "procedimento") == "Outros registros (sem código SIGTAP)"


def test_grupos_de_naturezas_diferentes_nao_se_misturam():
    """O teste que protege a regra central: consulta, preventivo e curativo
    precisam cair em grupos distintos."""
    consulta = classificar("03.01.01.015-3", "procedimento")
    preventivo = classificar("01.01.02.010-4", "procedimento")
    curativo = classificar("03.07.01.012-0", "procedimento")
    assert len({consulta, preventivo, curativo}) == 3


def test_aplicar_grupos_preserva_linhas_e_so_acrescenta_a_coluna():
    df = pd.DataFrame([
        lancamento(codigo_sigtap="01.01.02.010-4"),
        lancamento(codigo_sigtap="04.14.02.013-8"),
        lancamento(codigo_sigtap=None, categoria="agenda", chave="agendados"),
    ])
    saida = aplicar_grupos(df)

    assert len(saida) == len(df)
    assert list(df.columns) == [c for c in saida.columns if c != "grupo"]
    assert saida["grupo"].tolist() == [
        "Preventivos e ações coletivas",
        "Cirúrgicos",
        "Consultas e agenda (sem código SIGTAP)",
    ]
    # não altera o DataFrame original
    assert "grupo" not in df.columns


def test_nulos_de_origens_diferentes_nao_quebram_a_classificacao():
    """Regressão: None, NaN do numpy e NaN nativo convivem na mesma coluna
    quando a base é concatenada com dado de upload ou lido de CSV. Como
    NaN != NaN, a versão antiga levantava KeyError e derrubava a aba
    Produção da Rede inteira."""
    import numpy as np

    df = pd.DataFrame({
        "codigo_sigtap": [None, np.nan, float("nan"), "01.01.02.010-4"],
        "categoria": ["agenda", "agenda", "procedimento", "procedimento"],
        "quantidade": [1.0, 2.0, 3.0, 4.0],
    })
    saida = aplicar_grupos(df)

    assert saida["grupo"].tolist() == [
        "Consultas e agenda (sem código SIGTAP)",
        "Consultas e agenda (sem código SIGTAP)",
        "Outros registros (sem código SIGTAP)",
        "Preventivos e ações coletivas",
    ]


def test_codigo_com_espaco_nao_vira_grupo_diferente():
    df = pd.DataFrame({
        "codigo_sigtap": ["04.14.02.013-8", " 04.14.02.013-8 "],
        "categoria": ["procedimento", "procedimento"],
        "quantidade": [1.0, 1.0],
    })
    assert aplicar_grupos(df)["grupo"].nunique() == 1


def test_todo_grupo_produzido_esta_na_ordem_de_exibicao():
    """Se alguém criar um grupo novo sem incluí-lo em ORDEM_GRUPOS, os
    relatórios o perderiam silenciosamente."""
    codigos = ["01.01.02.010-4", "02.11.09.001-2", "03.01.01.015-3",
               "03.07.01.012-0", "04.14.02.013-8", "05.02.01.001-0", None]
    for c in codigos:
        for categoria in ("procedimento", "agenda", "outros"):
            assert classificar(c, categoria) in ORDEM_GRUPOS
