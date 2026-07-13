# -*- coding: utf-8 -*-
"""
OdontoProd — Relatório PDF de Produção Consolidada da Rede.

Página 1: síntese por grupo (consultas, preventivos, curativos...) e
gráfico de barras empilhadas por competência. Páginas seguintes: tabela
detalhada de todos os itens da planilha com totais no período.
"""

import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

AZUL = "#1f3864"
CINZA = "#8c8c8c"
A4 = (8.27, 11.69)
CORES_GRUPOS = ["#1f3864", "#2e5f8a", "#2e7d5b", "#8c6d1f",
                "#b0413e", "#6b4f8a", "#5b7553", "#999999"]


def _rodape(fig, pagina):
    fig.text(0.5, 0.02,
             f"OdontoProd — Produção Consolidada da Rede · página {pagina}",
             ha="center", fontsize=7, color=CINZA)


def gerar_pdf_producao(*, periodo_txt: str, n_profissionais: int,
                       resumo_grupos: list[dict], labels_serie: list[str],
                       series_grupos: dict, detalhe: list[dict]) -> bytes:
    """Monta o PDF e devolve os bytes.

    resumo_grupos: [{grupo, total, participacao}]
    series_grupos: {grupo: [valores por competência]}
    detalhe: [{grupo, codigo, procedimento, total}]
    """
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        # ------------------- página 1: síntese ---------------------------
        fig = plt.figure(figsize=A4)
        fig.text(0.08, 0.955, "Produção Consolidada da Rede",
                 fontsize=17, fontweight="bold", color=AZUL)
        fig.text(0.08, 0.930, "OdontoProd — Produtividade em Saúde Bucal (APS)",
                 fontsize=10, color=CINZA)
        fig.text(0.08, 0.898, f"Período: {periodo_txt} · "
                 f"{n_profissionais} profissionais",
                 fontsize=11)
        fig.text(0.08, 0.878,
                 f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · Consultas, "
                 "preventivos e curativos totalizados separadamente",
                 fontsize=9, color=CINZA)

        # tabela síntese por grupo
        ax = fig.add_axes([0.06, 0.60, 0.88, 0.24])
        ax.axis("off")
        celulas = [[r["grupo"], f"{r['total']:,.0f}".replace(",", "."),
                    f"{r['participacao']:.1f}%"] for r in resumo_grupos]
        tab = ax.table(cellText=celulas,
                       colLabels=["Grupo de produção", "Total no período",
                                  "Participação"],
                       loc="upper center", cellLoc="center",
                       colWidths=[0.58, 0.22, 0.20])
        tab.auto_set_font_size(False)
        tab.set_fontsize(8)
        tab.scale(1, 1.7)
        for (lin, col), cel in tab.get_celld().items():
            if lin == 0:
                cel.set_facecolor(AZUL)
                cel.set_text_props(color="white", fontweight="bold")
            elif col == 0:
                cel.set_text_props(ha="left")

        # gráfico empilhado por competência
        ax2 = fig.add_axes([0.10, 0.10, 0.84, 0.42])
        x = np.arange(len(labels_serie))
        base = np.zeros(len(labels_serie))
        for i, (grupo, vals) in enumerate(series_grupos.items()):
            vals = np.array(vals, dtype=float)
            ax2.bar(x, vals, bottom=base, label=grupo[:38],
                    color=CORES_GRUPOS[i % len(CORES_GRUPOS)], width=0.8)
            base += vals
        passo = max(1, len(x) // 12)
        ax2.set_xticks(x[::passo])
        ax2.set_xticklabels([labels_serie[i] for i in range(0, len(x), passo)],
                            fontsize=6.5, rotation=45)
        ax2.tick_params(axis="y", labelsize=7)
        ax2.set_title("Produção mensal por grupo (empilhado)", fontsize=10,
                      fontweight="bold", color=AZUL)
        ax2.legend(fontsize=6.2, frameon=False, ncol=2, loc="upper left")
        ax2.grid(axis="y", linewidth=0.3, alpha=0.4)
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
        _rodape(fig, 1)
        pdf.savefig(fig)
        plt.close(fig)

        # ------------- páginas 2+: tabela detalhada ----------------------
        por_pagina = 38
        pagina = 2
        for p0 in range(0, len(detalhe), por_pagina):
            bloco = detalhe[p0:p0 + por_pagina]
            fig = plt.figure(figsize=A4)
            fig.text(0.08, 0.955, "Detalhamento por item da planilha",
                     fontsize=13, fontweight="bold", color=AZUL)
            fig.text(0.08, 0.935, f"Período: {periodo_txt}",
                     fontsize=9, color=CINZA)
            ax = fig.add_axes([0.04, 0.05, 0.92, 0.86])
            ax.axis("off")
            celulas = [[r["grupo"][:30], r["codigo"] or "—",
                        r["procedimento"][:52],
                        f"{r['total']:,.0f}".replace(",", ".")]
                       for r in bloco]
            tab = ax.table(cellText=celulas,
                           colLabels=["Grupo", "Código SIGTAP",
                                      "Item da planilha", "Total"],
                           loc="upper center", cellLoc="center",
                           colWidths=[0.24, 0.14, 0.50, 0.12])
            tab.auto_set_font_size(False)
            tab.set_fontsize(6.6)
            tab.scale(1, 1.42)
            for (lin, col), cel in tab.get_celld().items():
                if lin == 0:
                    cel.set_facecolor(AZUL)
                    cel.set_text_props(color="white", fontweight="bold")
                elif col in (0, 2):
                    cel.set_text_props(ha="left")
            _rodape(fig, pagina)
            pdf.savefig(fig)
            plt.close(fig)
            pagina += 1

    return buf.getvalue()
