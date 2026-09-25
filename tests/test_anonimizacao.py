# -*- coding: utf-8 -*-
"""Guarda da anonimização — o teste mais importante deste repositório.

Esta é a versão pública de demonstração do OdontoProd. A base operacional,
com nomes reais de profissionais e unidades, roda apenas em ambiente local do
município. Aqui, todo identificador precisa ser um rótulo sintético
("Profissional NN", "Unidade NN").

Se algum dia um arquivo com dado nominal for copiado para cá por engano,
estes testes falham antes do commit.
"""
import re
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

ROTULO_PROFISSIONAL = re.compile(r"^Profissional \d{2,}$")
# vazio e 'Não informada' (planilha sem unidade) são aceitos
ROTULO_UNIDADE = re.compile(r"^(Unidade \d{2,}|Não informada)?$")

# arquivos que só existem no ambiente local e nunca podem chegar aqui
ARQUIVOS_PROIBIDOS = [
    "src/ingestao/nomes_canonicos.py",   # mapa de nomes reais
    "dados/mapa_anonimizacao.csv",       # real -> anônimo
    "dados/producao_completa.parquet",   # base antes da canonicalização
    ".streamlit/secrets.toml",           # credenciais
]


@pytest.fixture(scope="module")
def producao():
    return pd.read_parquet(DADOS / "producao_canonica.parquet")


@pytest.fixture(scope="module")
def indicadores():
    return pd.read_parquet(DADOS / "indicadores_mensais.parquet")


@pytest.mark.parametrize("caminho", ARQUIVOS_PROIBIDOS)
def test_arquivo_com_dado_nominal_nao_esta_no_repositorio(caminho):
    assert not (RAIZ / caminho).exists(), (
        f"{caminho} não pode existir na demonstração pública"
    )


def test_todo_profissional_tem_rotulo_sintetico(producao, indicadores):
    for base, nome in ((producao, "produção"), (indicadores, "indicadores")):
        fora = [p for p in base["profissional"].dropna().unique()
                if not ROTULO_PROFISSIONAL.match(str(p))]
        assert not fora, f"nomes não anonimizados em {nome}: {fora[:5]}"


def test_toda_unidade_tem_rotulo_sintetico(producao):
    fora = [u for u in producao["unidade"].dropna().unique()
            if not ROTULO_UNIDADE.match(str(u))]
    assert not fora, f"unidades não anonimizadas: {fora[:5]}"


def test_nenhuma_coluna_carrega_o_nome_original(producao, indicadores):
    """A coluna `profissional_original` existe na base local e guarda a
    grafia real da planilha — ela não pode ter vindo junto."""
    for base in (producao, indicadores):
        assert "profissional_original" not in base.columns


def test_a_base_publicada_continua_com_o_tamanho_esperado(producao):
    """Sanidade: se este número despencar, alguém publicou um recorte errado;
    se explodir, pode ter vindo base que não é a anonimizada."""
    # 43 desde 25/09/2026: saíram três não profissionais (estagiários) e um
    # nome duplicado por espaços repetidos foi unificado
    assert producao["profissional"].nunique() == 43
    assert producao["unidade"].nunique() == 18       # 17 + 'Não informada'
    assert len(producao) > 150_000
