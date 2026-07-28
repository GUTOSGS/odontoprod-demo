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
