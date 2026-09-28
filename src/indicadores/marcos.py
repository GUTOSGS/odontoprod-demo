# -*- coding: utf-8 -*-
"""Marcos da série histórica, desenhados nos gráficos de evolução.

Painel acionável liga a variação no tempo ao que pode explicá-la (Stahlman
et al., 2025). Aqui ficam as competências em que algo externo à produção
mudou — o instrumento de registro, uma regra de contagem — e que por isso
podem explicar um degrau no gráfico.
"""

# A transição de template foi medida no relatório de cobertura do lote: em
# jan/2025, 10 de 23 planilhas já estavam no modelo novo; de fev/2025 em
# diante, quase todas.
MARCOS = [
    {"competencia": "2025-01",
     "rotulo": "Novo instrumento de registro",
     "texto": "transição para o Mapa de Produção Odontológica, adotado por "
              "quase toda a rede a partir de fev/2025"},
]


def no_intervalo(ini: str, fim: str) -> list:
    """Marcos depois de `ini` e até `fim`: os que podem gerar um degrau.

    Um marco na primeira competência exibida não separa nada no gráfico.
    """
    return [m for m in MARCOS if ini < m["competencia"] <= fim]
