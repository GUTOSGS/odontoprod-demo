# -*- coding: utf-8 -*-
"""Configuração comum dos testes: torna o projeto importável e cria fixtures."""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def lancamento(**campos):
    """Um lançamento no formato longo da base, com padrões razoáveis."""
    base = {
        "profissional": "Fulana De Tal",
        "funcao": "dentista",
        "unidade": "Unidade Teste",
        "ano": 2025,
        "mes": 3,
        "dia": 1,
        "categoria": "procedimento",
        "codigo_sigtap": "03.07.01.012-0",
        "chave": "03.07.01.012-0",
        "procedimento": "RESTAURACAO",
        "quantidade": 1.0,
    }
    base.update(campos)
    return base


@pytest.fixture
def grupo_simples():
    """Um profissional, um mês: 2 dias de atendimento com agenda e clínica.

    Números escolhidos para que cada indicador tenha resultado conferível
    à mão (ver test_motor.py).
    """
    linhas = [
        # agenda: 20 agendados, 5 faltosos, 4 TC (dias de agenda não contam
        # como dia trabalhado)
        lancamento(dia=1, categoria="agenda", codigo_sigtap=None,
                   chave="agendados", procedimento="AGENDADOS", quantidade=20),
        lancamento(dia=1, categoria="agenda", codigo_sigtap=None,
                   chave="faltosos", procedimento="FALTOSOS", quantidade=5),
        lancamento(dia=1, categoria="agenda", codigo_sigtap=None,
                   chave="tratamento_completado",
                   procedimento="TRATAMENTO COMPLETADO (TC)", quantidade=4),
        lancamento(dia=1, categoria="agenda", codigo_sigtap=None,
                   chave="consulta_retorno", procedimento="CONSULTA DE RETORNO",
                   quantidade=6),
        # clínica do dia 1
        lancamento(dia=1, codigo_sigtap="03.01.01.015-3", chave="03.01.01.015-3",
                   procedimento="PRIMEIRA CONSULTA", quantidade=5),
        lancamento(dia=1, codigo_sigtap="03.07.01.012-0", chave="03.07.01.012-0",
                   procedimento="RESTAURACAO POSTERIOR", quantidade=8),
        lancamento(dia=1, codigo_sigtap="04.14.02.013-8", chave="04.14.02.013-8",
                   procedimento="EXODONTIA PERMANENTE", quantidade=2),
        # clínica do dia 2
        lancamento(dia=2, codigo_sigtap="03.01.06.003-7", chave="03.01.06.003-7",
                   procedimento="URGENCIA", quantidade=3),
        lancamento(dia=2, codigo_sigtap="01.01.02.010-4", chave="01.01.02.010-4",
                   procedimento="ORIENTACAO DE HIGIENE BUCAL", quantidade=10),
        lancamento(dia=2, codigo_sigtap="03.07.01.007-4", chave="03.07.01.007-4",
                   procedimento="ART", quantidade=2),
    ]
    return pd.DataFrame(linhas)
