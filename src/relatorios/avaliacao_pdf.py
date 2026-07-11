# -*- coding: utf-8 -*-
"""
OdontoProd — Relatório PDF de Avaliação Individual do profissional.

Gera um PDF multipáginas (A4) com cabeçalho, tabela-síntese com percentis,
radar de posição relativa, destaques e gráficos de evolução mensal com a
banda de referência da rede (média±DP ou mediana+IIQ).
Renderização 100% matplotlib (sem dependências de navegador).
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
VERDE = "#2e7d5b"
VERMELHO = "#b0413e"
AMARELO = "#b8860b"

A4 = (8.27, 11.69)


def _rodape(fig, pagina):
    fig.text(0.5, 0.02,
             f"OdontoProd — Relatório de Avaliação Individual · página {pagina}",
             ha="center", fontsize=7, color=CINZA)


def gerar_pdf_avaliacao(*, profissional: str, funcao: str, unidade: str,
                        periodo_txt: str, n_profs: int, n_competencias: int,
                        tabela_linhas: list[dict], percentis: dict,
                        fortes: list[str], fracos: list[str],
                        series: list[dict], referencia_txt: str) -> bytes:
    """Monta o PDF e devolve os bytes.

    series: um dict por indicador com chaves
      titulo, labels (competências), centro, sup, inf, prof_x, prof_y,
      menor_melhor (bool)
    """
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:

        # ------------------------- página 1: capa + tabela ---------------
        fig = plt.figure(figsize=A4)
        fig.text(0.08, 0.955, "Avaliação Individual de Desempenho",
                 fontsize=17, fontweight="bold", color=AZUL)
        fig.text(0.08, 0.928, "OdontoProd — Produtividade em Saúde Bucal (APS)",
                 fontsize=10, color=CINZA)
        fig.text(0.08, 0.885, profissional, fontsize=14, fontweight="bold")
        papel = ("Cirurgião-dentista" if funcao == "dentista"
                 else "Técnico em saúde bucal")
        fig.text(0.08, 0.862,
                 f"{papel} · Unidade: {unidade or '—'}", fontsize=10)
        fig.text(0.08, 0.842,
                 f"Período: {periodo_txt} · {n_competencias} competência(s) · "
                 f"comparado com {n_profs} profissionais da rede",
                 fontsize=10)
        fig.text(0.08, 0.822,
                 f"Referência de comparação: {referencia_txt} · "
                 f"Gerado em {datetime.now():%d/%m/%Y %H:%M}",
                 fontsize=9, color=CINZA)

        if tabela_linhas:
            cab = ["Indicador", "Profis-\nsional", "Média\nrede", "DP",
                   "Mediana", "IIQ\n(P25–P75)", "Per-\ncentil", "Situação"]
            celulas = [[l["Indicador"], l["valor"], l["media"], l["dp"],
                        l["mediana"], l["iiq"], l["percentil"], l["situacao"]]
                       for l in tabela_linhas]
            ax = fig.add_axes([0.05, 0.06, 0.90, 0.72])
            ax.axis("off")
            tab = ax.table(cellText=celulas, colLabels=cab, loc="upper center",
                           cellLoc="center",
                           colWidths=[0.34, 0.09, 0.09, 0.08, 0.09, 0.13,
                                      0.08, 0.13])
            tab.auto_set_font_size(False)
            tab.set_fontsize(7.2)
            tab.scale(1, 1.75)
            for (lin, col), cel in tab.get_celld().items():
                if lin == 0:
                    cel.set_facecolor(AZUL)
                    cel.set_text_props(color="white", fontweight="bold")
                elif col == 0:
                    cel.set_text_props(ha="left")
                    cel.PAD = 0.02
                if lin > 0 and col == 7:
                    texto = celulas[lin - 1][7]
                    cor = (VERDE if "acima" in texto
                           else VERMELHO if "abaixo" in texto else AMARELO)
                    cel.set_text_props(color=cor, fontweight="bold")
            fig.text(0.08, 0.045,
                     "↓ = indicador em que valor MENOR é melhor; a Situação e o radar "
                     "já consideram a direção. Percentil sobre a média de cada "
                     "profissional no período.",
                     fontsize=7, color=CINZA)
        _rodape(fig, 1)
        pdf.savefig(fig)
        plt.close(fig)

        # ------------------- página 2: radar + destaques -----------------
        fig = plt.figure(figsize=A4)
        fig.text(0.08, 0.955, "Posição relativa na rede",
                 fontsize=14, fontweight="bold", color=AZUL)
        fig.text(0.08, 0.932,
                 "Percentil ajustado: 100 = melhor posição da rede, já "
                 "considerando a direção de cada indicador.",
                 fontsize=9, color=CINZA)

        if len(percentis) >= 3:
            rotulos = list(percentis.keys())
            valores = list(percentis.values())
            ang = np.linspace(0, 2 * np.pi, len(rotulos), endpoint=False)
            ang_f = np.concatenate([ang, ang[:1]])
            val_f = valores + valores[:1]
            ax = fig.add_axes([0.14, 0.42, 0.72, 0.48], polar=True)
            ax.plot(ang_f, val_f, color=AZUL, linewidth=2)
            ax.fill(ang_f, val_f, color=AZUL, alpha=0.20)
            ax.plot(ang_f, [50] * len(ang_f), color=CINZA, linestyle=":",
                    linewidth=1.2)
            ax.set_xticks(ang)
            ax.set_xticklabels([r[:24] for r in rotulos], fontsize=6.5)
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75])
            ax.set_yticklabels(["25", "50", "75"], fontsize=6)
            ax.set_title(f"{profissional} × mediana da rede (linha pontilhada)",
                         fontsize=9, pad=18)

        y = 0.34
        fig.text(0.08, y, "Pontos fortes", fontsize=11, fontweight="bold",
                 color=VERDE)
        for t in fortes or ["— (sem destaques no recorte)"]:
            y -= 0.025
            fig.text(0.10, y, "• " + t, fontsize=9)
        y -= 0.04
        fig.text(0.08, y, "Oportunidades de melhoria", fontsize=11,
                 fontweight="bold", color=VERMELHO)
        for t in fracos or ["— (nenhum indicador abaixo do P50)"]:
            y -= 0.025
            fig.text(0.10, y, "• " + t, fontsize=9)
        _rodape(fig, 2)
        pdf.savefig(fig)
        plt.close(fig)

        # ------------- páginas 3+: evolução mensal (6 por página) --------
        por_pagina = 6
        for p0 in range(0, len(series), por_pagina):
            bloco = series[p0:p0 + por_pagina]
            fig, axs = plt.subplots(3, 2, figsize=A4)
            fig.subplots_adjust(hspace=0.55, wspace=0.30, top=0.90,
                                bottom=0.07, left=0.09, right=0.97)
            fig.suptitle(f"Evolução mensal × rede ({referencia_txt})",
                         fontsize=11, fontweight="bold", color=AZUL, y=0.955)
            for ax in axs.ravel():
                ax.set_visible(False)
            for i, s in enumerate(bloco):
                ax = axs.ravel()[i]
                ax.set_visible(True)
                x = np.arange(len(s["labels"]))
                ax.fill_between(x, s["inf"], s["sup"],
                                color="#6c8ec8", alpha=0.18,
                                label="Faixa da rede")
                ax.plot(x, s["centro"], color=CINZA, linestyle="--",
                        linewidth=1.2, label="Rede")
                idx = [s["labels"].index(c) for c in s["prof_x"]
                       if c in s["labels"]]
                vals = [v for c, v in zip(s["prof_x"], s["prof_y"])
                        if c in s["labels"]]
                ax.plot(idx, vals, color=AZUL, linewidth=1.9, marker="o",
                        markersize=2.6, label=profissional)
                titulo = s["titulo"] + (" (menor é melhor)"
                                        if s.get("menor_melhor") else "")
                ax.set_title(titulo, fontsize=8, fontweight="bold")
                passo = max(1, len(x) // 6)
                ax.set_xticks(x[::passo])
                ax.set_xticklabels([s["labels"][j] for j in x[::passo]],
                                   fontsize=6, rotation=45)
                ax.tick_params(axis="y", labelsize=6.5)
                ax.grid(axis="y", linewidth=0.3, alpha=0.4)
                for sp in ("top", "right"):
                    ax.spines[sp].set_visible(False)
                if i == 0:
                    ax.legend(fontsize=6, frameon=False)
            _rodape(fig, 3 + p0 // por_pagina)
            pdf.savefig(fig)
            plt.close(fig)

    return buf.getvalue()
