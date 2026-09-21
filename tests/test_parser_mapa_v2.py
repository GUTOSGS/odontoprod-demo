# -*- coding: utf-8 -*-
"""Testes do roteamento e da leitura de competência do template v2
(Mapa de Produção 2025+, src/ingestao/parser_mapa_v2.py).

Regra do projeto: no v2 o campo MÊS/ANO é texto livre e frequentemente
errado — o nome da aba prevalece, com checagem de plausibilidade do ano.
"""
import pytest

from src.ingestao.parser_mapa_v2 import (
    _mes_ano_de_texto,
    _mes_da_pasta,
    eh_template_v2,
)


@pytest.mark.parametrize("abas", [
    ["CIRURGIÃO-DENTISTA", "TÉCNICA EM SAÚDE BUCAL"],
    ["TSB"],
    ["AGOSTO 2025", "SETEMBRO 2025"],
    ["JULHO25"],
])
def test_reconhece_o_template_v2(abas):
    assert eh_template_v2(abas) is True


@pytest.mark.parametrize("abas", [
    ["Planilha1"],
    ["PRODUÇÃO"],
    [],
])
def test_nao_confunde_v1_com_v2(abas):
    assert eh_template_v2(abas) is False


@pytest.mark.parametrize("texto,esperado", [
    ("AGOSTO DE 2025", (8, 2025)),
    ("Janeiro 2026", (1, 2026)),
    ("JULHO25", (7, 2025)),
    ("março 24", (3, 2024)),
    ("Dezembro", (12, 0)),          # sem ano: quem decide é a pasta/aba
    ("Planilha1", (0, 0)),
])
def test_mes_e_ano_de_texto_livre(texto, esperado):
    assert _mes_ano_de_texto(texto) == esperado


@pytest.mark.parametrize("pasta,esperado", [
    ("03 MARÇO", 3),
    ("11 NOVEMBRO", 11),
    ("SETEMBRO", 9),
    ("sem mês aqui", 0),
])
def test_mes_da_pasta(pasta, esperado):
    assert _mes_da_pasta(pasta) == esperado


# ------------------------------------------------------------ fim a fim
# Planilha cumulativa do template 2025: a aba genérica 'CIRURGIÃO-DENTISTA'
# (sem mês no nome, herda o mês da PASTA) convive com abas nomeadas por mês.

import pandas as pd  # noqa: E402

from src.ingestao.parser_mapa_v2 import (  # noqa: E402
    PREFIXO_CONFLITO,
    parse_arquivo_v2,
)


def _aba(quantidades):
    """Uma aba do template v2 com três dias e dois procedimentos."""
    linhas = [
        ["MÊS/ANO:", None, None, None],
        ["UNIDADE DE SAÚDE: CENTRO", None, None, None],
        ["NOME CIRURGIÃO-DENTISTA: FULANA DE TAL", None, None, None],
        ["1- CONSULTAS", 1, 2, 3],
    ]
    for codigo, qs in zip(["03.01.01.015-3", "03.07.01.012-0"], quantidades):
        linhas.append([f"{codigo} - PROCEDIMENTO", *qs])
    return pd.DataFrame(linhas)


def _planilha(tmp_path, abas):
    pasta = tmp_path / "Produção 2025" / "4 ABRIL"
    pasta.mkdir(parents=True)
    arquivo = pasta / "FULANA.xlsx"
    with pd.ExcelWriter(arquivo, engine="openpyxl") as w:
        for nome, quantidades in abas.items():
            _aba(quantidades).to_excel(w, sheet_name=nome, header=False,
                                       index=False)
    return arquivo


def _por_mes(resultados):
    return {(r.ano, r.mes): float(r.dados["quantidade"].sum())
            for r in resultados if not r.dados.empty}


def _conflitos(resultados):
    return [a for r in resultados for a in r.avisos
            if a.startswith(PREFIXO_CONFLITO)]


def test_aba_do_mes_vence_a_generica_desatualizada(tmp_path):
    """O caso real: a genérica é cópia velha, maior que a aba do mês. A
    regra antiga ('fica a maior') ficava com a cópia velha."""
    arq = _planilha(tmp_path, {
        "CIRURGIÃO-DENTISTA": [[9, 9, 9], [9, 9, 9]],    # velha: 54
        "ABRIL 2025": [[5, 5, 5], [4, 4, 4]],            # real: 27
    })
    res = parse_arquivo_v2(arq)

    assert _por_mes(res) == {(2025, 4): 27.0}
    conflitos = _conflitos(res)
    assert len(conflitos) == 1
    assert "mantida a aba do mês 'ABRIL 2025'" in conflitos[0]


def test_aba_do_mes_quase_vazia_perde_para_a_generica(tmp_path):
    """O outro lado: a aba do mês foi aberta e mal preenchida."""
    arq = _planilha(tmp_path, {
        "CIRURGIÃO-DENTISTA": [[9, 9, 9], [9, 9, 9]],    # 54
        "ABRIL 2025": [[1, 0, 0], [0, 0, 0]],            # 1 (< 25%)
    })
    res = parse_arquivo_v2(arq)

    assert _por_mes(res) == {(2025, 4): 54.0}
    assert "quase vazia" in _conflitos(res)[0]


def test_abas_identicas_nao_sao_conflito(tmp_path):
    arq = _planilha(tmp_path, {
        "CIRURGIÃO-DENTISTA": [[3, 3, 3], [2, 2, 2]],
        "ABRIL 2025": [[3, 3, 3], [2, 2, 2]],
    })
    res = parse_arquivo_v2(arq)

    assert _por_mes(res) == {(2025, 4): 15.0}      # contado UMA vez
    assert _conflitos(res) == []


def test_generica_sozinha_fica_com_o_mes_da_pasta(tmp_path):
    arq = _planilha(tmp_path, {"CIRURGIÃO-DENTISTA": [[1, 2, 3], [0, 1, 0]]})
    res = parse_arquivo_v2(arq)

    assert _por_mes(res) == {(2025, 4): 7.0}
    assert _conflitos(res) == []


def test_planilha_cumulativa_nao_duplica_meses(tmp_path):
    """Três meses nomeados + genérica velha: cada mês aparece uma vez só."""
    arq = _planilha(tmp_path, {
        "CIRURGIÃO-DENTISTA": [[9, 9, 9], [9, 9, 9]],
        "FEVEREIRO 2025": [[1, 1, 1], [1, 1, 1]],
        "MARÇO 2025": [[2, 2, 2], [2, 2, 2]],
        "ABRIL 2025": [[3, 3, 3], [3, 3, 3]],
    })
    res = parse_arquivo_v2(arq)

    assert _por_mes(res) == {(2025, 2): 6.0, (2025, 3): 12.0, (2025, 4): 18.0}
    assert all(r.profissional == "Fulana De Tal" for r in res)
