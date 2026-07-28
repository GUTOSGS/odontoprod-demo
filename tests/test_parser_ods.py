# -*- coding: utf-8 -*-
"""Testes do parser do template v1 (src/ingestao/parser_ods.py).

Princípio do projeto que estes testes travam: o parser tolera planilha
imperfeita, mas nunca falha em silêncio — toda decisão automática vira aviso.
"""
import pandas as pd
import pytest

from src.ingestao.parser_ods import (
    _reparar_dias,
    _sem_acento,
    ano_do_caminho,
    parse_arquivo,
)

# ---------------------------------------------------------------- unidades


def test_sem_acento_normaliza_para_comparacao():
    assert _sem_acento("Produção Odontológica") == "PRODUCAO ODONTOLOGICA"
    assert _sem_acento("  março ") == "MARCO"


def test_ano_vem_da_pasta_mais_profunda_com_um_unico_ano(tmp_path):
    pasta = tmp_path / "PRODUÇÃO MENSAL 2022_2023_2024" / "PRODUÇÃO MENSAL 2023"
    pasta.mkdir(parents=True)
    # a raiz cita três anos e não pode decidir; a subpasta cita um só
    assert ano_do_caminho(pasta / "Fulana.ods") == 2023


def test_ano_indefinido_quando_nenhuma_pasta_cita_ano(tmp_path):
    assert ano_do_caminho(tmp_path / "Fulana.ods") == 0


def test_dia_fora_de_sequencia_e_reparado_pelos_vizinhos():
    avisos = []
    # cabeçalho ... 7, 4, 9 ...  -> o 4 só pode ser 8
    mapa = _reparar_dias({1: 7, 2: 4, 3: 9}, avisos)
    assert mapa == {1: 7, 2: 8, 3: 9}
    assert any("corrigido para 8" in a for a in avisos)


def test_dia_irreparavel_e_descartado_com_aviso():
    avisos = []
    mapa = _reparar_dias({1: 10, 2: 3, 3: 25}, avisos)
    assert mapa == {1: 10, 3: 25}          # o 3 não tinha como ser inferido
    assert any("fora de ordem" in a for a in avisos)


# ------------------------------------------------------------ fim a fim

@pytest.fixture
def planilha_v1(tmp_path):
    """Planilha no template v1 com quatro defeitos propositais.

    1. mês do metadado (fevereiro) diferente do mês da pasta (março)
    2. um dia digitado errado no cabeçalho (9 onde deveria ser 3)
    3. coluna TOTAL divergente da soma dos dias
    4. uma linha de procedimento criada à mão, fora do template
    """
    pasta = tmp_path / "PRODUÇÃO MENSAL 2025" / "03 MARÇO"
    pasta.mkdir(parents=True)
    arquivo = pasta / "Fulana De Tal.xlsx"

    linhas = [
        ["MÊS: FEVEREIRO", None, None, None, None, None, None],
        ["UNIDADE DE SAÚDE: CENTRO   DENTISTA: FULANA DE TAL",
         None, None, None, None, None, None],
        ["PRODUÇÃO ODONTOLOGIA", 1, 2, 9, 4, 5, "TOTAL"],
        ["AGENDADOS", 10, 8, None, None, None, 18],
        ["FALTOSOS", 2, 1, None, None, None, 3],
        ["TRATAMENTO COMPLETADO (TC)", 1, None, None, None, None, 1],
        ["03.01.01.015-3 - PRIMEIRA CONSULTA ODONTOLÓGICA PROGRAMÁTICA",
         3, 2, None, None, None, 5],
        ["04.14.02.013-8 - EXODONTIA DE DENTE PERMANENTE",
         None, 1, None, None, None, 99],
        ["PROCEDIMENTO CRIADO À MÃO", None, None, 4, None, None, 4],
        ["TOTAL", 16, 12, 4, 0, 0, 32],
    ]
    pd.DataFrame(linhas).to_excel(arquivo, header=False, index=False)
    return arquivo


def test_parse_le_metadados_e_dados(planilha_v1):
    res = parse_arquivo(planilha_v1)

    assert res.ok
    assert res.profissional == "Fulana De Tal"
    assert res.funcao == "dentista"
    assert res.unidade == "Centro"
    assert res.ano == 2025
    assert res.mes == 3                     # o mês da pasta prevalece
    assert not res.erros


def test_parse_classifica_agenda_procedimento_e_linha_livre(planilha_v1):
    dados = parse_arquivo(planilha_v1).dados
    contagem = dados["categoria"].value_counts().to_dict()

    assert contagem["agenda"] == 5          # agendados, faltosos e TC
    assert contagem["procedimento"] == 3    # 1ªs consultas (2 dias) + exodontia
    assert contagem["outros"] == 1          # a linha criada à mão

    consultas = dados[dados["codigo_sigtap"] == "03.01.01.015-3"]
    assert consultas["quantidade"].sum() == 5
    assert consultas["procedimento"].iat[0] == \
        "PRIMEIRA CONSULTA ODONTOLÓGICA PROGRAMÁTICA"


def test_parse_repara_o_dia_errado_do_cabecalho(planilha_v1):
    res = parse_arquivo(planilha_v1)
    # a linha livre estava na coluna do "9", que só podia ser 3
    livre = res.dados[res.dados["categoria"] == "outros"]
    assert livre["dia"].tolist() == [3]
    assert 9 not in res.dados["dia"].tolist()


def test_dias_trabalhados_desconsidera_dias_so_de_agenda(planilha_v1):
    res = parse_arquivo(planilha_v1)
    assert res.dias_trabalhados == [1, 2, 3]


@pytest.mark.parametrize("trecho", [
    "usando o da pasta",        # mês do metadado x mês da pasta
    "corrigido para 3",         # dia reparado
    "TOTAL divergente",         # coluna TOTAL não confere
    "Linha não reconhecida",    # procedimento fora do template
])
def test_toda_decisao_automatica_vira_aviso(planilha_v1, trecho):
    avisos = parse_arquivo(planilha_v1).avisos
    assert any(trecho in a for a in avisos), f"faltou aviso sobre {trecho!r}"


def test_arquivo_ilegivel_nao_derruba_o_lote(tmp_path):
    quebrado = tmp_path / "corrompido.xlsx"
    quebrado.write_text("isto não é uma planilha", encoding="utf-8")

    res = parse_arquivo(quebrado)
    assert not res.ok
    assert res.erros                      # registra o erro em vez de estourar
    assert res.dados.empty
