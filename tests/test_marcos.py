# -*- coding: utf-8 -*-
"""Testes dos marcos da série (src/indicadores/marcos.py)."""
import re

from src.indicadores import marcos


def test_marco_aparece_quando_o_intervalo_o_atravessa():
    assert marcos.no_intervalo("2024-07", "2025-06")
    assert marcos.no_intervalo("2022-01", "2025-01")


def test_marco_fora_ou_na_borda_inicial_nao_aparece():
    assert not marcos.no_intervalo("2025-01", "2025-06")
    assert not marcos.no_intervalo("2023-01", "2024-12")


def test_marcos_tem_competencia_valida_e_rotulo():
    for m in marcos.MARCOS:
        assert re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m["competencia"])
        assert m["rotulo"] and m["texto"]
