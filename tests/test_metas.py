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
    ("B1", 1.25, BOM), ("B1", 1.26, OTIMO), ("B1", 0.25, REGULAR),
    ("B4", 1.0, BOM), ("B4", 1.01, OTIMO), ("B4", 0.5, SUFICIENTE),
    ("B4", 0.25, REGULAR),
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
    base = {"profissional": ["A", "B"], "funcao": ["dentista", "dentista"],
            "dias_trabalhados": [10, 10],
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


def _op(codigo):
    return next(m for m in metas.OPERACIONAIS if m["codigo"] == codigo)


@pytest.mark.parametrize("codigo,valor,esperado", [
    ("O1", 8, True), ("O1", 7.9, False),
    ("O3", 10, True), ("O3", 10.1, False),
    ("O1", None, None),
])
def test_atingiu_respeita_o_sentido_da_meta(codigo, valor, esperado):
    assert metas.atingiu(valor, _op(codigo)) is esperado


# ---------------------------------------------------------- faixas das
# metas operacionais: a meta é a fronteira do Ótimo e abaixo dela vêm três
# degraus de um terço da meta (pactuado em 23/09/2026)
@pytest.mark.parametrize("codigo,valor,esperado", [
    # "quanto mais, melhor": meta 8 -> degraus de 2,67
    ("O1", 9.0, OTIMO), ("O1", 8.0, OTIMO), ("O1", 7.9, BOM),
    ("O1", 5.34, BOM), ("O1", 5.33, SUFICIENTE), ("O1", 2.6, REGULAR),
    # "quanto menos, melhor": meta 10% -> degraus de 3,33
    ("O3", 9.9, OTIMO), ("O3", 10.0, OTIMO), ("O3", 10.1, BOM),
    ("O3", 13.3, BOM), ("O3", 15.0, SUFICIENTE), ("O3", 17.0, REGULAR),
])
def test_faixa_operacional_equidistante(codigo, valor, esperado):
    assert metas.faixa_operacional(valor, _op(codigo)) == esperado


def test_faixas_operacionais_sao_degraus_iguais_e_cobrem_o_eixo():
    for spec in metas.OPERACIONAIS:
        limites = metas.limites_operacional(spec)
        larguras = [round(fim - ini, 6) for ini, fim, _ in limites[1:-1]]
        assert len(set(larguras)) == 1, spec["codigo"]
        assert round(larguras[0], 6) == round(spec["meta"] / 3, 6)
        assert limites[0][0] == 0
        for (_, fim, _), (ini, _, _) in zip(limites, limites[1:]):
            assert fim == ini
        assert [f for _, _, f in limites].count(OTIMO) == 1


def test_faixa_sem_valor_e_none():
    assert metas.faixa_operacional(None, _op("O1")) is None


def test_texto_das_faixas_sai_na_ordem_do_melhor_para_o_pior():
    assert (metas.texto_faixas(_op("O1"))
            == "Ótimo: ≥ 8 · Bom: ≥ 5,33 · Suficiente: ≥ 2,67 "
               "· Regular: < 2,67")
    assert (metas.texto_faixas(_op("O3"))
            == "Ótimo: ≤ 10% · Bom: ≤ 13,33% · Suficiente: ≤ 16,67% "
               "· Regular: > 16,67%")


# ------------------------------------------------- aplicação por função
def test_indicadores_de_dentista_nao_aparecem_para_a_tecnica():
    """A TSB não faz exodontia, restauração, tratamento concluído nem
    urgência — medir isso nela só produziria zero."""
    ministeriais = [s["codigo"] for s in
                    metas.aplicaveis(metas.MINISTERIAIS, ["tecnico"])]
    operacionais = [s["codigo"] for s in
                    metas.aplicaveis(metas.OPERACIONAIS, ["tecnico"])]

    assert ministeriais == ["B4", "B5"]
    assert operacionais == ["O1", "O3", "O4"]


def test_recorte_com_as_duas_funcoes_mostra_tudo():
    assert (metas.aplicaveis(metas.OPERACIONAIS, ["dentista", "tecnico"])
            == metas.OPERACIONAIS)


def test_b1_usa_a_populacao_de_referencia_por_dentista():
    """3.500 pessoas por CD por mês: 35 primeiras consultas = 1%."""
    ind = _ind(funcao=["dentista", "dentista"],
               primeiras_consultas=[35, 35])
    assert metas.calcular(ind, _prod([]))["B1"] == 1.0


def test_b4_usa_18_por_cento_da_populacao_de_referencia():
    """630 crianças de 6 a 12 anos por equipe: 63 participantes = 10%."""
    assert metas.CRIANCAS_POR_DENTISTA == 630
    ind = _ind(funcao=["dentista", "dentista"])
    v = metas.calcular(ind, _prod([("01.01.02.003-1", 126)]))
    assert v["B4"] == 10.0            # 126 ÷ (630 × 2 equipes-mês)


def test_b4_conta_a_escovacao_da_tecnica_sem_duplicar_a_equipe():
    """A TSB escova, mas a população é da equipe do dentista: somar a
    técnica no denominador contaria a mesma equipe duas vezes."""
    ind = _ind(funcao=["dentista", "tecnico"])
    prod = pd.concat([
        _prod([("01.01.02.003-1", 30)]),
        _prod([("01.01.02.003-1", 33)]).assign(profissional="B"),
    ])
    assert metas.calcular(ind, prod)["B4"] == 10.0   # 63 ÷ (630 × 1)


def test_b4_num_recorte_so_de_tecnicas_usa_a_equipe_de_cada_uma():
    ind = _ind(funcao=["tecnico", "tecnico"])
    v = metas.calcular(ind, _prod([("01.01.02.003-1", 126)]))
    assert v["B4"] == 10.0


def test_b1_ignora_as_observacoes_da_tecnica():
    ind = _ind(funcao=["dentista", "tecnico"], primeiras_consultas=[35, 35])
    assert metas.calcular(ind, _prod([]))["B1"] == 1.0
