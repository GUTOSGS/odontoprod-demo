# -*- coding: utf-8 -*-
"""
OdontoProd — Painel de Produtividade em Saúde Bucal (APS)
TCC MBA Data Science & Analytics — USP/Esalq

Executar:  streamlit run app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from src.auth import barra_usuario, exigir_login
from src.indicadores import metas
from src.indicadores.grupos import ORDEM_GRUPOS, aplicar_grupos
from src.indicadores.motor import calcular_serie
from src.relatorios.avaliacao_pdf import gerar_pdf_avaliacao
from src.relatorios.producao_pdf import gerar_pdf_producao
from src.ingestao.parser_mapa_v2 import eh_template_v2, parse_arquivo_v2
from src.ingestao.parser_ods import parse_arquivo

DADOS = Path(__file__).parent / "dados"

st.set_page_config(
    page_title="OdontoProd — Saúde Bucal APS",
    page_icon="🦷",
    layout="wide",
)

sessao = exigir_login()

AZUL = "#1f3864"
PALETA = px.colors.qualitative.Set2

INDICADORES_ROTULOS = {
    "media_atend_dia": "Atendimentos/dia",
    "media_proc_dia": "Procedimentos/dia",
    "taxa_absenteismo_pct": "Absenteísmo (%)",
    "media_faltas_dia": "Faltas/dia",
    "primeiras_consultas": "1ªs consultas programáticas",
    "razao_tc": "Razão de tratamento completado",
    "media_prev_dia": "Preventivos/dia",
    "media_art_dia": "ART/dia",
    "pct_exodontias": "Exodontias (% dos procedimentos)",
    "razao_rest_exo": "Razão restauração/exodontia",
    "urgencias": "Atendimentos de urgência",
    "total_procedimentos": "Total de procedimentos",
    "atendimentos": "Total de atendimentos",
    "dias_trabalhados": "Dias trabalhados",
}


# ----------------------------------------------------------------------
@st.cache_data
def carregar():
    ind = pd.read_parquet(DADOS / "indicadores_mensais.parquet")
    prod = pd.read_parquet(DADOS / "producao_canonica.parquet")
    prod["competencia"] = (prod["ano"].astype(str) + "-"
                           + prod["mes"].astype(str).str.zfill(2))
    return ind, prod


ind, prod = carregar()
competencias = sorted(ind["competencia"].unique())

MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
               "jul", "ago", "set", "out", "nov", "dez"]


def fmt_comp(c: str) -> str:
    ano, mes = c.split("-")
    return f"{MESES_ABREV[int(mes) - 1]}/{ano}"


# ----------------------------------------------------------------------
# Barra lateral: filtros globais
# ----------------------------------------------------------------------
st.sidebar.title("🦷 OdontoProd")
st.sidebar.caption("Demonstração pública — **dados anonimizados** · TCC MBA DSA USP/Esalq")

modo_periodo = st.sidebar.radio("Período", ["Intervalo", "Mês único"],
                                horizontal=True, label_visibility="collapsed")
if modo_periodo == "Mês único":
    comp_unica = st.sidebar.selectbox("Competência", competencias,
                                      index=len(competencias) - 1,
                                      format_func=fmt_comp)
    ini = fim = comp_unica
else:
    col_de, col_ate = st.sidebar.columns(2)
    ini = col_de.selectbox("De", competencias, index=0, format_func=fmt_comp)
    fim = col_ate.selectbox("Até", competencias,
                            index=len(competencias) - 1, format_func=fmt_comp)
    if ini > fim:
        ini, fim = fim, ini

funcoes = st.sidebar.multiselect(
    "Função", ["dentista", "tecnico"], default=["dentista"],
    format_func=lambda x: "Cirurgião-dentista" if x == "dentista" else "Técnico (TSB/ASB)",
)

profs_opcoes = sorted(ind.loc[ind["funcao"].isin(funcoes), "profissional"].unique())
profs_sel = st.sidebar.multiselect(
    "Profissionais (vazio = todos)", profs_opcoes, default=[],
)

f = ind[(ind["competencia"] >= ini) & (ind["competencia"] <= fim)
        & (ind["funcao"].isin(funcoes))]
if profs_sel:
    f = f[f["profissional"].isin(profs_sel)]

fp = prod[(prod["competencia"] >= ini) & (prod["competencia"] <= fim)
          & (prod["funcao"].isin(funcoes))]
if profs_sel:
    fp = fp[fp["profissional"].isin(profs_sel)]

st.sidebar.divider()
st.sidebar.caption(
    f"**{f['profissional'].nunique()}** profissionais · "
    f"**{f['competencia'].nunique()}** competências · "
    f"**{int(f['total_procedimentos'].sum()):,}** procedimentos".replace(",", ".")
)
barra_usuario()

if f.empty:
    st.warning("⚠️ Nenhum registro para a combinação de filtros selecionada. "
               "Verifique o período, a função (CD/técnico) e os profissionais "
               "escolhidos — por exemplo, um dentista não aparece quando o "
               "filtro de função está em 'Técnico', e vice-versa.")
    st.stop()

# ----------------------------------------------------------------------
titulo_abas = ["📊 Visão Geral", "⏱️ Metas 2026",
               "👤 Produtividade Individual",
               "🎯 Avaliação Individual", "⚖️ Comparativo",
               "🩺 Indicadores Clínicos", "📋 Produção da Rede",
               "📁 Dados & Exportação"]
(aba1, aba_metas, aba2, aba_av, aba3, aba4, aba_prod,
 aba5) = st.tabs(titulo_abas)

# indicadores em que valor MENOR é melhor (inverte leitura do percentil)
MENOR_MELHOR = {"taxa_absenteismo_pct", "media_faltas_dia", "pct_exodontias"}


def kpi_fmt(v, casas=1, sufixo=""):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}{sufixo}".replace(",", "X").replace(".", ",").replace("X", ".")


# ======================================================================
# ABA 1 — VISÃO GERAL
# ======================================================================
with aba1:
    st.subheader("Visão geral da rede no período")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Atendimentos/dia (média)", kpi_fmt(f["media_atend_dia"].mean()))
    c2.metric("Procedimentos/dia (média)", kpi_fmt(f["media_proc_dia"].mean()))
    c3.metric("Absenteísmo médio", kpi_fmt(f["taxa_absenteismo_pct"].mean(), 1, "%"))
    c4.metric("Razão TC média", kpi_fmt(f["razao_tc"].mean(), 2))
    c5.metric("Exodontias (média %)", kpi_fmt(f["pct_exodontias"].mean(), 1, "%"))
    c6.metric("1ªs consultas (total)", kpi_fmt(f["primeiras_consultas"].sum(), 0))

    st.divider()
    col_a, col_b = st.columns([3, 2])

    with col_a:
        serie = (f.groupby("competencia")
                 .agg(atend=("media_atend_dia", "mean"),
                      proc=("media_proc_dia", "mean"),
                      absent=("taxa_absenteismo_pct", "mean"))
                 .reset_index())
        fig = go.Figure()
        fig.add_scatter(x=serie["competencia"], y=serie["atend"],
                        name="Atendimentos/dia", mode="lines+markers",
                        line=dict(color=AZUL, width=2.5))
        fig.add_scatter(x=serie["competencia"], y=serie["proc"],
                        name="Procedimentos/dia", mode="lines+markers",
                        line=dict(color="#2e8b6e", width=2))
        fig.add_scatter(x=serie["competencia"], y=serie["absent"],
                        name="Absenteísmo (%)", mode="lines",
                        line=dict(color="#c0504d", width=1.5, dash="dot"))
        fig.update_layout(title="Evolução mensal — médias da rede",
                          height=380, legend=dict(orientation="h", y=-0.25),
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        top_uni = (f.groupby("unidade")["media_atend_dia"].mean()
                   .sort_values(ascending=True).tail(12).reset_index())
        fig = px.bar(top_uni, x="media_atend_dia", y="unidade",
                     orientation="h", title="Atendimentos/dia por unidade",
                     color_discrete_sequence=[AZUL])
        fig.update_layout(height=380, xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Heatmap — atendimentos/dia por profissional × competência")
    hm = f.pivot_table(index="profissional", columns="competencia",
                       values="media_atend_dia", aggfunc="mean")
    hm = hm.reindex(hm.mean(axis=1).sort_values(ascending=False).index)
    fig = px.imshow(hm, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(color="Atend/dia"))
    fig.update_layout(height=max(350, 22 * len(hm)), xaxis_title=None,
                      yaxis_title=None, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ABA METAS 2026 — VELOCÍMETROS
# ======================================================================


def _translucida(hexa, alfa=0.45):
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def velocimetro(valor, titulo, eixo, passos=(), meta=None, sentido=None,
                sufixo="", casas=1):
    """Velocímetro plotly: faixas coloridas ao fundo, ponteiro em barra e,
    havendo meta, linha de referência e diferença em relação a ela."""
    indicador = go.Indicator(
        mode="gauge+number" + ("+delta" if meta is not None else ""),
        value=valor,
        number={"suffix": sufixo, "valueformat": f".{casas}f"},
        title={"text": titulo, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, eixo]},
            "bar": {"color": AZUL, "thickness": 0.3},
            "steps": [{"range": [a, b], "color": c} for a, b, c in passos],
            **({"threshold": {"line": {"color": "#222", "width": 3},
                              "thickness": 0.85, "value": meta}}
               if meta is not None else {}),
        },
        **({"delta": {"reference": meta, "valueformat": f".{casas}f",
                      "increasing": {"color": "#2e8b6e" if sentido == "minimo"
                                     else "#c0504d"},
                      "decreasing": {"color": "#c0504d" if sentido == "minimo"
                                     else "#2e8b6e"}}}
           if meta is not None else {}),
    )
    fig = go.Figure(indicador)
    fig.update_layout(height=230, margin=dict(t=60, b=10, l=25, r=25),
                      separators=",.")
    return fig


def _selo(faixa):
    return (f"<span style='background:{metas.CORES[faixa]};color:white;"
            f"padding:2px 10px;border-radius:10px;font-size:0.85em'>"
            f"{faixa}</span>")


with aba_metas:
    st.subheader("Metas 2026 — indicadores ministeriais e operacionais")
    st.caption(
        "Fonte das metas: resumo municipal de indicadores de saúde bucal "
        "para o planejamento 2026 (coordenação). Os valores respeitam os filtros "
        "da barra lateral e somam numeradores e denominadores do recorte "
        "(nunca média de percentuais). Cada indicador só aparece para a "
        "função que o realiza: exodontia, tratamento concluído e urgência "
        "são do cirurgião-dentista.")

    recorte = st.radio("Recorte", ["Rede (filtros atuais)", "Um profissional"],
                       horizontal=True, key="metas_recorte")
    f_m, fp_m = f, fp
    if recorte == "Um profissional":
        prof_m = st.selectbox("Profissional",
                              sorted(f["profissional"].unique()),
                              key="metas_prof")
        f_m = f[f["profissional"] == prof_m]
        fp_m = fp[fp["profissional"] == prof_m]

    valores = metas.calcular(f_m, fp_m)

    st.markdown("#### Indicadores ministeriais (B1-B6)")
    st.caption(
        f"São **aproximações** a partir das planilhas locais, por "
        f"profissional — o valor oficial é apurado no SIAPS por equipe "
        f"(INE), com os códigos elegíveis de cada nota. B1 usa a população "
        f"de referência de {metas.POPULACAO_POR_DENTISTA:,} pessoas por "
        f"cirurgião-dentista, pactuada pela coordenação, e B4 as "
        f"{metas.CRIANCAS_POR_DENTISTA} crianças de 6 a 12 anos estimadas "
        f"nessa população ({metas.PROPORCAO_6_A_12_ANOS:.0%})."
        .replace(",", "."))
    ministeriais = metas.aplicaveis(metas.MINISTERIAIS, funcoes)
    colunas = st.columns(3)
    for i, spec in enumerate(ministeriais):
        with colunas[i % 3]:
            titulo = f"{spec['codigo']} · {spec['nome']}"
            if not spec["calculavel"]:
                st.markdown(f"**{titulo}**")
                st.info(f"Não calculável pelas planilhas: {spec['motivo']}. "
                        f"Faixa ótima: {spec['otima']}.")
                continue
            v = valores[spec["codigo"]]
            if v is None:
                st.markdown(f"**{titulo}**")
                st.warning("Não calculável no recorte (denominador zero).")
                continue
            eixo = max(spec["eixo"], round(v * 1.1))
            passos = [(a, b if b < spec["eixo"] else eixo,
                       _translucida(metas.CORES[faixa]))
                      for a, b, faixa in spec["passos"]]
            st.plotly_chart(velocimetro(v, titulo, eixo, passos, sufixo="%"),
                            use_container_width=True,
                            key=f"vel_{spec['codigo']}")
            st.markdown(f"<div style='text-align:center;margin-top:-12px'>"
                        f"{_selo(spec['faixa'](v))} &nbsp;"
                        f"<small>ótimo: {spec['otima']}</small></div>",
                        unsafe_allow_html=True)

    st.markdown("#### Metas operacionais da RASB do município")
    st.caption(
        "A meta municipal é a fronteira do **Ótimo**; abaixo dela vêm três "
        "degraus de mesmo tamanho (um terço da meta), no formato das faixas "
        "do Ministério. O sentido de cada meta — quanto mais, melhor ou "
        "quanto menos, melhor — é o declarado no documento. A linha preta "
        "marca a meta; o número pequeno é a diferença em relação a ela.")
    operacionais = metas.aplicaveis(metas.OPERACIONAIS, funcoes)
    colunas = st.columns(3)
    for i, spec in enumerate(operacionais):
        with colunas[i % 3]:
            v = valores[spec["codigo"]]
            titulo = spec["nome"]
            if v is None:
                st.markdown(f"**{titulo}**")
                st.warning("Não calculável no recorte.")
                continue
            meta = spec["meta"]
            limites = metas.limites_operacional(spec)
            eixo = max(limites[-1][1], v * 1.15)
            passos = [(a, b if b < limites[-1][1] else eixo,
                       _translucida(metas.CORES[faixa]))
                      for a, b, faixa in limites]
            st.plotly_chart(
                velocimetro(v, titulo, eixo, passos, meta=meta,
                            sentido=spec["sentido"], sufixo=spec["unidade"],
                            casas=spec["casas"]),
                use_container_width=True, key=f"vel_{spec['codigo']}")
            alvo = "≥" if spec["sentido"] == "minimo" else "≤"
            st.markdown(f"<div style='text-align:center;margin-top:-12px'>"
                        f"{_selo(metas.faixa_operacional(v, spec))} &nbsp;"
                        f"<small>meta {alvo} {kpi_fmt(meta, 0)}"
                        f"{spec['unidade']}</small><br>"
                        f"<small style='opacity:.7'>"
                        f"{metas.texto_faixas(spec)}</small></div>",
                        unsafe_allow_html=True)

    if recorte.startswith("Rede"):
        st.markdown("#### Quem atinge cada meta")
        tab = metas.por_profissional(f, fp)
        exibe = pd.DataFrame({"Profissional": tab["profissional"]})
        for spec in ministeriais:
            if spec["calculavel"]:
                exibe[spec["codigo"]] = [
                    "—" if pd.isna(v) else
                    f"{kpi_fmt(v, 1)}% · {spec['faixa'](v)}"
                    for v in tab[spec["codigo"]]]
        for spec in operacionais:
            exibe[spec["nome"]] = [
                "—" if pd.isna(v) else
                f"{kpi_fmt(v, spec['casas'])}{spec['unidade']} · "
                f"{metas.faixa_operacional(v, spec)}"
                for v in tab[spec["codigo"]]]
        st.dataframe(exibe, hide_index=True, use_container_width=True)
        st.caption("Faixa de cada meta operacional: " + " | ".join(
            f"**{s['nome']}** — {metas.texto_faixas(s)}"
            for s in operacionais))

    with st.expander("Como cada valor é calculado"):
        for spec in ministeriais + operacionais:
            nome = f"**{spec['codigo']} · {spec['nome']}**"
            st.markdown(f"- {nome}: " + spec.get(
                "formula", f"não calculável — {spec.get('motivo', '')}"))
        st.markdown(
            "- Agendamentos e faltas usam só as competências em que o "
            "profissional registrou agendados — quem não preenche o campo "
            "não puxa a média da rede para baixo.\n"
            "- Preventivos coletivos (flúor gel, bochecho, escovação "
            "supervisionada) ficam fora de B3 e B5, que tratam de "
            "procedimentos individuais.")

# ======================================================================
# ABA 2 — PRODUTIVIDADE INDIVIDUAL
# ======================================================================
with aba2:
    prof = st.selectbox("Profissional",
                        sorted(f["profissional"].unique()))
    g = f[f["profissional"] == prof].sort_values("competencia")
    gp = fp[fp["profissional"] == prof]

    info = g.iloc[-1]
    st.subheader(f"{prof}")
    rotulo_funcao = ("Cirurgião-dentista" if info["funcao"] == "dentista"
                     else "Técnico em saúde bucal")
    st.caption(f"{rotulo_funcao}"
               f" · Unidade: {info['unidade'] or '—'} · "
               f"{g['competencia'].nunique()} competências no período")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Atendimentos/dia", kpi_fmt(g["media_atend_dia"].mean()))
    c2.metric("Procedimentos/dia", kpi_fmt(g["media_proc_dia"].mean()))
    c3.metric("Absenteísmo", kpi_fmt(g["taxa_absenteismo_pct"].mean(), 1, "%"))
    c4.metric("Razão TC", kpi_fmt(g["razao_tc"].mean(), 2))
    c5.metric("Exodontias", kpi_fmt(g["pct_exodontias"].mean(), 1, "%"))
    c6.metric("Dias trabalhados (média)", kpi_fmt(g["dias_trabalhados"].mean()))

    col_a, col_b = st.columns(2)
    with col_a:
        indicador = st.selectbox(
            "Indicador para evolução mensal",
            list(INDICADORES_ROTULOS.keys()),
            format_func=INDICADORES_ROTULOS.get,
        )
        media_rede = (f.groupby("competencia")[indicador].mean()
                      .reindex(g["competencia"]).values)
        fig = go.Figure()
        fig.add_scatter(x=g["competencia"], y=g[indicador],
                        name=prof, mode="lines+markers",
                        line=dict(color=AZUL, width=2.5))
        fig.add_scatter(x=g["competencia"], y=media_rede,
                        name="Média da rede", mode="lines",
                        line=dict(color="#999999", width=1.5, dash="dash"))
        fig.update_layout(title=INDICADORES_ROTULOS[indicador], height=360,
                          legend=dict(orientation="h", y=-0.25),
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        top = (gp[gp["categoria"] == "procedimento"]
               .groupby("procedimento")["quantidade"].sum()
               .sort_values(ascending=True).tail(12).reset_index())
        top["procedimento"] = top["procedimento"].str.slice(0, 48)
        fig = px.bar(top, x="quantidade", y="procedimento", orientation="h",
                     title="Ranking de procedimentos no período",
                     color_discrete_sequence=["#2e8b6e"])
        fig.update_layout(height=360, xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ABA — AVALIAÇÃO INDIVIDUAL COMPLETA
# ======================================================================
with aba_av:
    # Quem pode ser avaliado: respeita o filtro de função da barra lateral
    # (mas ignora o de profissionais, para não restringir a escolha).
    base_sel = ind[(ind["competencia"] >= ini) & (ind["competencia"] <= fim)
                   & (ind["funcao"].isin(funcoes))]
    if base_sel.empty:
        st.info("Sem dados no período/função selecionados.")
    else:
        c_sel1, c_sel2 = st.columns([1, 2])
        prof_av = c_sel1.selectbox(
            "Profissional avaliado", sorted(base_sel["profissional"].unique()),
            key="av_prof")

        # COM QUEM ele é comparado: sempre a própria função, independente do
        # filtro da barra lateral. Misturar CD e TSB desloca o percentil em
        # dezenas de pontos (um técnico tem 0 atendimento/dia por definição
        # do processo de trabalho, não por desempenho) e o semáforo muda de
        # cor num relatório que vai para a mão do profissional.
        funcao_av = (base_sel.loc[base_sel["profissional"] == prof_av, "funcao"]
                     .mode().iat[0])
        base_cmp = ind[(ind["competencia"] >= ini) & (ind["competencia"] <= fim)
                       & (ind["funcao"] == funcao_av)]
        rotulo_pares = ("cirurgiões-dentistas" if funcao_av == "dentista"
                        else "técnicos em saúde bucal")
        inds_disp = list(INDICADORES_ROTULOS.keys())
        sel = c_sel2.multiselect(
            "Indicadores (vazio = todos)", inds_disp, default=[],
            format_func=INDICADORES_ROTULOS.get, key="av_inds")
        inds_sel = sel or inds_disp

        medida = st.radio(
            "Referência de comparação com a rede",
            ["Média ± desvio-padrão", "Mediana + intervalo interquartílico (IIQ)"],
            horizontal=True, key="av_medida")
        usa_media = medida.startswith("Média")

        g = base_cmp[base_cmp["profissional"] == prof_av].sort_values("competencia")
        info = g.iloc[-1]
        n_profs = base_cmp["profissional"].nunique()
        st.markdown(f"### {prof_av}")
        st.caption(
            f"{'Cirurgião-dentista' if info['funcao'] == 'dentista' else 'Técnico em saúde bucal'}"
            f" · Unidade: {info['unidade'] or '—'} · "
            f"{g['competencia'].nunique()} competência(s) no período "
            f"({fmt_comp(ini)} a {fmt_comp(fim)}) · "
            f"comparado com {n_profs} {rotulo_pares} da rede")

        # ---------- tabela-síntese com percentil ----------
        por_prof = base_cmp.groupby("profissional")[inds_disp].mean()
        linhas_av = []
        percentis_radar = {}
        for k in inds_sel:
            serie = por_prof[k].dropna()
            if prof_av not in serie.index or len(serie) < 2:
                continue
            valor = serie[prof_av]
            # rank(pct=True) devolve (0, 1]: o melhor recebe 100. Para
            # inverter um indicador em que menor é melhor, ranqueia-se o
            # valor negativo — assim o melhor também chega a 100, em vez do
            # 100 - 100/n que a subtração direta produzia.
            base_rank = -serie if k in MENOR_MELHOR else serie
            pct_ajust = float(base_rank.rank(pct=True)[prof_av] * 100)
            pct = float(serie.rank(pct=True)[prof_av] * 100)
            percentis_radar[k] = pct_ajust
            q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
            if pct_ajust >= 75:
                situacao = "🟢 acima da rede"
            elif pct_ajust >= 25:
                situacao = "🟡 dentro da rede"
            else:
                situacao = "🔴 abaixo da rede"
            rotulo = (INDICADORES_ROTULOS[k]
                      + (" ↓" if k in MENOR_MELHOR else ""))
            linhas_av.append({
                "Indicador": rotulo,
                prof_av: round(valor, 2),
                "Média rede": round(serie.mean(), 2),
                "DP": round(serie.std(), 2),
                "Mediana": round(serie.median(), 2),
                "IIQ (P25–P75)": f"{q1:.2f} – {q3:.2f}",
                "Percentil": f"{pct:.0f}º",
                "Situação": situacao,
            })
        st.dataframe(pd.DataFrame(linhas_av), use_container_width=True,
                     hide_index=True)
        st.caption("↓ = indicador em que valor MENOR é melhor (absenteísmo, "
                   "faltas/dia, % exodontias); a coluna Situação já considera "
                   "isso. Percentil calculado sobre a média de cada "
                   "profissional no período.")

        # estruturas para o relatório PDF
        tabela_pdf = [{
            "Indicador": linha["Indicador"], "valor": str(linha[prof_av]),
            "media": str(linha["Média rede"]), "dp": str(linha["DP"]),
            "mediana": str(linha["Mediana"]), "iiq": linha["IIQ (P25–P75)"],
            "percentil": linha["Percentil"],
            "situacao": linha["Situação"].split(" ", 1)[1],
        } for linha in linhas_av]
        ordenado = sorted(percentis_radar.items(), key=lambda x: x[1])
        fortes_txt = [f"{INDICADORES_ROTULOS[k]} — percentil ajustado {v:.0f}"
                      for k, v in reversed(ordenado[-3:])]
        fracos_txt = [f"{INDICADORES_ROTULOS[k]} — percentil ajustado {v:.0f}"
                      for k, v in ordenado[:3] if v < 50]

        col_radar, col_destaques = st.columns([1, 1])

        # ---------- radar de posição relativa ----------
        with col_radar:
            if len(percentis_radar) >= 3:
                rotulos = [INDICADORES_ROTULOS[k][:28] for k in percentis_radar]
                valores = list(percentis_radar.values())
                fig = go.Figure(go.Scatterpolar(
                    r=valores + valores[:1],
                    theta=rotulos + rotulos[:1],
                    fill="toself", line=dict(color=AZUL),
                    name=prof_av))
                fig.add_trace(go.Scatterpolar(
                    r=[50] * (len(rotulos) + 1),
                    theta=rotulos + rotulos[:1],
                    line=dict(color="#999999", dash="dot"),
                    name="Mediana da rede (P50)"))
                fig.update_layout(
                    title="Posição relativa na rede (percentil ajustado)",
                    polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75])),
                    height=420, legend=dict(orientation="h", y=-0.15),
                    margin=dict(t=60, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Selecione ao menos 3 indicadores para o radar.")

        # ---------- destaques automáticos ----------
        with col_destaques:
            st.markdown("##### Destaques do período")
            for t in fortes_txt:
                st.success(f"**{t}** (ponto forte)")
            for t in fracos_txt:
                st.error(f"**{t}** (oportunidade de melhoria)")
            st.caption("Percentil ajustado: 100 = melhor posição da rede, "
                       "já considerando a direção de cada indicador.")

        # ---------- evolução mensal com banda da rede ----------
        st.markdown("##### Evolução mensal × rede "
                    + ("(média ± 1 DP)" if usa_media else "(mediana + IIQ)"))
        series_pdf = []
        colunas_graf = st.columns(2)
        for i, k in enumerate(inds_sel):
            stats = (base_cmp.groupby("competencia")[k]
                     .agg(media="mean", dp="std", mediana="median",
                          q25=lambda s: s.quantile(0.25),
                          q75=lambda s: s.quantile(0.75))
                     .reindex(sorted(base_cmp["competencia"].unique())))
            if usa_media:
                centro = stats["media"]
                sup = stats["media"] + stats["dp"]
                inf = (stats["media"] - stats["dp"]).clip(lower=0)
                nome_centro = "Média da rede"
            else:
                centro = stats["mediana"]
                sup, inf = stats["q75"], stats["q25"]
                nome_centro = "Mediana da rede"

            fig = go.Figure()
            fig.add_scatter(x=stats.index, y=sup, line=dict(width=0),
                            showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=stats.index, y=inf, line=dict(width=0),
                            fill="tonexty", fillcolor="rgba(100,140,200,0.18)",
                            name="Faixa da rede", hoverinfo="skip")
            fig.add_scatter(x=stats.index, y=centro, name=nome_centro,
                            line=dict(color="#888888", dash="dash", width=1.6))
            fig.add_scatter(x=g["competencia"], y=g[k], name=prof_av,
                            mode="lines+markers",
                            line=dict(color=AZUL, width=2.6))
            titulo_graf = (INDICADORES_ROTULOS[k]
                           + (" (menor é melhor)" if k in MENOR_MELHOR else ""))
            fig.update_layout(
                title=titulo_graf,
                height=300, margin=dict(t=45, b=10),
                legend=dict(orientation="h", y=-0.3),
                xaxis=dict(tickvals=list(stats.index)[::max(1, len(stats)//8)]))
            colunas_graf[i % 2].plotly_chart(fig, use_container_width=True)

            series_pdf.append({
                "titulo": INDICADORES_ROTULOS[k],
                "labels": [fmt_comp(c) for c in stats.index],
                "centro": centro.tolist(),
                "sup": sup.tolist(),
                "inf": inf.tolist(),
                "prof_x": [fmt_comp(c) for c in g["competencia"]],
                "prof_y": g[k].tolist(),
                "menor_melhor": k in MENOR_MELHOR,
            })

        # ---------- relatório em PDF ----------
        st.divider()
        params_pdf = (prof_av, ini, fim, tuple(inds_sel), medida, funcao_av)
        col_b1, col_b2 = st.columns([1, 2])
        if col_b1.button("🖨️ Gerar relatório PDF", key="av_pdf_btn",
                         type="primary"):
            with st.spinner("Montando o relatório..."):
                pdf_bytes = gerar_pdf_avaliacao(
                    profissional=prof_av,
                    funcao=str(info["funcao"]),
                    unidade=str(info["unidade"]),
                    periodo_txt=f"{fmt_comp(ini)} a {fmt_comp(fim)}",
                    n_profs=n_profs,
                    n_competencias=int(g["competencia"].nunique()),
                    tabela_linhas=tabela_pdf,
                    percentis={INDICADORES_ROTULOS[k]: v
                               for k, v in percentis_radar.items()},
                    fortes=fortes_txt, fracos=fracos_txt,
                    series=series_pdf,
                    referencia_txt=("média ± 1 DP" if usa_media
                                    else "mediana + IIQ"),
                )
            st.session_state["av_pdf"] = (params_pdf, pdf_bytes)
        if (st.session_state.get("av_pdf")
                and st.session_state["av_pdf"][0] == params_pdf):
            col_b2.download_button(
                "⬇️ Baixar relatório (PDF)",
                st.session_state["av_pdf"][1],
                file_name=(f"avaliacao_{prof_av.replace(' ', '_')}"
                           f"_{ini}_a_{fim}.pdf"),
                mime="application/pdf", key="av_pdf_dl")

# ======================================================================
# ABA 3 — COMPARATIVO
# ======================================================================
with aba3:
    indicador = st.selectbox(
        "Indicador para comparação",
        list(INDICADORES_ROTULOS.keys()),
        format_func=INDICADORES_ROTULOS.get,
        key="cmp_ind",
    )
    rot = INDICADORES_ROTULOS[indicador]

    col_a, col_b = st.columns(2)
    with col_a:
        med = (f.groupby("profissional")[indicador].mean()
               .sort_values(ascending=True).reset_index())
        fig = px.bar(med, x=indicador, y="profissional", orientation="h",
                     title=f"Ranking — {rot} (média no período)",
                     color_discrete_sequence=[AZUL])
        fig.update_layout(height=max(400, 22 * len(med)),
                          xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        ordem = med.sort_values(indicador, ascending=False)["profissional"]
        fig = px.box(f, x=indicador, y="profissional",
                     category_orders={"profissional": list(ordem)},
                     title=f"Distribuição mensal — {rot}",
                     color_discrete_sequence=["#2e8b6e"])
        fig.update_layout(height=max(400, 22 * len(med)),
                          xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Matriz indicador × profissional "
                "(média no período, escala normalizada por indicador)")
    cols_matriz = ["media_atend_dia", "media_proc_dia", "taxa_absenteismo_pct",
                   "razao_tc", "media_prev_dia", "pct_exodontias", "razao_rest_exo"]
    mat = f.groupby("profissional")[cols_matriz].mean()
    mat_norm = (mat - mat.min()) / (mat.max() - mat.min())
    mat_norm.columns = [INDICADORES_ROTULOS[c] for c in cols_matriz]
    fig = px.imshow(mat_norm.T, aspect="auto", color_continuous_scale="RdYlGn",
                    labels=dict(color="0–1"))
    fig.update_layout(height=340, xaxis_title=None, yaxis_title=None,
                      margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Atenção: absenteísmo e % exodontias — quanto MAIOR, pior. "
               "A normalização é apenas visual; consulte os valores brutos na aba Dados.")

# ======================================================================
# ABA 4 — INDICADORES CLÍNICOS
# ======================================================================
with aba4:
    st.subheader("Perfil clínico-assistencial")

    col_a, col_b = st.columns(2)
    with col_a:
        serie_tc = (f.groupby("competencia")
                    .agg(tc=("trat_completados", "sum"),
                         pc=("primeiras_consultas", "sum"))
                    .reset_index())
        serie_tc["razao"] = serie_tc["tc"] / serie_tc["pc"].replace(0, pd.NA)
        fig = px.line(serie_tc, x="competencia", y="razao", markers=True,
                      title="Razão de tratamento completado (rede)",
                      color_discrete_sequence=[AZUL])
        fig.add_hline(y=1.0, line_dash="dot", line_color="#2e8b6e",
                      annotation_text="meta: 1,0")
        fig.update_layout(height=340, xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

        disp = f.groupby("profissional").agg(
            prev=("media_prev_dia", "mean"),
            exo=("pct_exodontias", "mean"),
            atend=("media_atend_dia", "mean")).reset_index().dropna()
        fig = px.scatter(disp, x="prev", y="exo", size="atend",
                         hover_name="profissional",
                         title="Preventivos/dia × % exodontias (tamanho = atend/dia)",
                         labels={"prev": "Preventivos/dia",
                                 "exo": "% exodontias"},
                         color_discrete_sequence=["#2e8b6e"])
        fig.update_layout(height=360, margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        serie_cx = (f.groupby("competencia")
                    .agg(exod=("exodontias", "sum"),
                         rest=("restauracoes", "sum"),
                         art=("art", "sum"))
                    .reset_index())
        fig = go.Figure()
        fig.add_bar(x=serie_cx["competencia"], y=serie_cx["rest"],
                    name="Restaurações", marker_color=AZUL)
        fig.add_bar(x=serie_cx["competencia"], y=serie_cx["exod"],
                    name="Exodontias", marker_color="#c0504d")
        fig.add_bar(x=serie_cx["competencia"], y=serie_cx["art"],
                    name="ART", marker_color="#2e8b6e")
        fig.update_layout(barmode="group", height=340,
                          title="Restaurações × exodontias × ART (rede)",
                          legend=dict(orientation="h", y=-0.25),
                          margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

        rk = (f.groupby("profissional")["razao_tc"].mean()
              .dropna().sort_values(ascending=True).reset_index())
        fig = px.bar(rk, x="razao_tc", y="profissional", orientation="h",
                     title="Razão TC média por profissional",
                     color="razao_tc", color_continuous_scale="RdYlGn")
        fig.add_vline(x=1.0, line_dash="dot", line_color="#555555")
        fig.update_layout(height=max(360, 20 * len(rk)),
                          xaxis_title=None, yaxis_title=None,
                          coloraxis_showscale=False, margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ABA — PRODUÇÃO CONSOLIDADA DA REDE
# ======================================================================
with aba_prod:
    st.subheader("Produção consolidada da rede no período")
    st.caption(f"Período: {fmt_comp(ini)} a {fmt_comp(fim)} · rede completa "
               "(este módulo ignora os filtros de função e profissional). "
               "Consultas/agenda (sem código SIGTAP), preventivos e "
               "curativos são totalizados SEPARADAMENTE — nunca somados.")

    base_rede = prod[(prod["competencia"] >= ini)
                     & (prod["competencia"] <= fim)]
    base_rede = aplicar_grupos(base_rede)
    grupos_presentes = [g for g in ORDEM_GRUPOS
                        if g in set(base_rede["grupo"])]

    # ---------- KPIs por grupo principal ----------
    def _total(grupo=None, chaves=None):
        m = base_rede["grupo"] == grupo if grupo else \
            base_rede["chave"].isin(chaves)
        return int(base_rede.loc[m, "quantidade"].sum())

    consultas_realizadas = _total(chaves=["consulta_no_dia",
                                          "consulta_retorno",
                                          "consulta_manutencao"])
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Consultas realizadas (agenda)",
              f"{consultas_realizadas:,}".replace(",", "."))
    c2.metric("Atendimentos SIGTAP",
              f"{_total('Atendimentos e consultas (SIGTAP)'):,}".replace(",", "."))
    c3.metric("Preventivos",
              f"{_total('Preventivos e ações coletivas'):,}".replace(",", "."))
    c4.metric("Curativos",
              f"{_total('Curativos e reabilitadores'):,}".replace(",", "."))
    c5.metric("Cirúrgicos",
              f"{_total('Cirúrgicos'):,}".replace(",", "."))
    c6.metric("Diagnósticos",
              f"{_total('Diagnósticos (radiografias, biópsias)'):,}".replace(",", "."))

    # ---------- evolução mensal por grupo (empilhado) ----------
    serie_g = (base_rede.groupby(["competencia", "grupo"])["quantidade"]
               .sum().unstack(fill_value=0)
               .reindex(columns=grupos_presentes, fill_value=0)
               .sort_index())
    fig = go.Figure()
    for g in grupos_presentes:
        fig.add_bar(x=[fmt_comp(c) for c in serie_g.index],
                    y=serie_g[g], name=g)
    fig.update_layout(barmode="stack", height=420,
                      title="Produção mensal por grupo — totalizações separadas",
                      legend=dict(orientation="h", y=-0.35),
                      margin=dict(t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------- tabela detalhada: todos os itens da planilha ----------
    st.markdown("##### Detalhamento por item da planilha (tudo o que foi registrado)")
    detalhe = (base_rede.groupby(["grupo", "codigo_sigtap", "procedimento"],
                                 dropna=False)["quantidade"]
               .sum().reset_index()
               .rename(columns={"codigo_sigtap": "código SIGTAP",
                                "quantidade": "total no período"}))
    detalhe["_ordem"] = detalhe["grupo"].map(
        {g: i for i, g in enumerate(ORDEM_GRUPOS)})
    detalhe = (detalhe.sort_values(["_ordem", "total no período"],
                                   ascending=[True, False])
               .drop(columns="_ordem"))
    detalhe["total no período"] = detalhe["total no período"].astype(int)
    st.dataframe(detalhe, use_container_width=True, height=420,
                 hide_index=True)

    # ---------- exportações ----------
    col_e1, col_e2, col_e3 = st.columns([1, 1, 2])
    col_e1.download_button(
        "⬇️ Baixar detalhamento (CSV)",
        detalhe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=f"producao_rede_{ini}_a_{fim}.csv", mime="text/csv",
        key="prod_csv")

    params_prod = (ini, fim)
    if col_e2.button("🖨️ Gerar relatório PDF", key="prod_pdf_btn",
                     type="primary"):
        with st.spinner("Montando o relatório..."):
            total_geral = float(base_rede["quantidade"].sum())
            resumo = [{"grupo": g,
                       "total": float(serie_g[g].sum()),
                       "participacao": 100 * float(serie_g[g].sum()) / total_geral}
                      for g in grupos_presentes]
            pdf_bytes = gerar_pdf_producao(
                periodo_txt=f"{fmt_comp(ini)} a {fmt_comp(fim)}",
                n_profissionais=base_rede["profissional"].nunique(),
                resumo_grupos=resumo,
                labels_serie=[fmt_comp(c) for c in serie_g.index],
                series_grupos={g: serie_g[g].tolist()
                               for g in grupos_presentes},
                detalhe=[{"grupo": r["grupo"],
                          "codigo": r["código SIGTAP"],
                          "procedimento": r["procedimento"],
                          "total": r["total no período"]}
                         for _, r in detalhe.iterrows()],
            )
        st.session_state["prod_pdf"] = (params_prod, pdf_bytes)
    if (st.session_state.get("prod_pdf")
            and st.session_state["prod_pdf"][0] == params_prod):
        col_e3.download_button(
            "⬇️ Baixar relatório de produção (PDF)",
            st.session_state["prod_pdf"][1],
            file_name=f"producao_rede_{ini}_a_{fim}.pdf",
            mime="application/pdf", key="prod_pdf_dl")

# ======================================================================
# ABA 5 — DADOS & EXPORTAÇÃO
# ======================================================================
with aba5:
    st.subheader("Matriz de indicadores (profissional × competência)")
    st.dataframe(f.sort_values(["competencia", "profissional"]),
                 use_container_width=True, height=420)

    c1, c2 = st.columns(2)
    c1.download_button(
        "⬇️ Baixar indicadores filtrados (CSV)",
        f.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=f"indicadores_{ini}_a_{fim}.csv",
        mime="text/csv",
    )
    c2.download_button(
        "⬇️ Baixar lançamentos brutos filtrados (CSV)",
        fp.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=f"producao_{ini}_a_{fim}.csv",
        mime="text/csv",
    )

    # ------------------------------------------------------------------
    # Upload de novas planilhas de produção
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("📤 Enviar planilhas de produção")
    st.caption("Modo calculadora (demonstração): aceita os dois templates "
               "(2022-2024 e Mapa 2025+), .ods ou .xlsx. Os arquivos são "
               "processados apenas nesta sessão e descartados — nada é "
               "armazenado. Envie planilhas de teste ou anonimizadas.")

    col_u1, col_u2 = st.columns(2)
    ano_padrao = col_u1.selectbox(
        "Ano (usado se o arquivo não informar)", list(range(2022, 2031)),
        index=list(range(2022, 2031)).index(2026))
    mes_padrao = col_u2.selectbox(
        "Mês (usado se o arquivo não informar)", list(range(1, 13)),
        format_func=lambda m: MESES_ABREV[m - 1])

    uploads = st.file_uploader("Arquivos", type=["ods", "xlsx"],
                               accept_multiple_files=True)

    if uploads:
        import tempfile

        resultados = []
        for up in uploads:
            sufixo = Path(up.name).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
                tmp.write(up.getbuffer())
                caminho_tmp = Path(tmp.name)
            try:
                engine = "odf" if sufixo == ".ods" else "openpyxl"
                sheets = pd.ExcelFile(caminho_tmp, engine=engine).sheet_names
                if eh_template_v2(sheets):
                    rs = parse_arquivo_v2(caminho_tmp)
                else:
                    rs = [parse_arquivo(caminho_tmp)]
            except Exception as e:
                st.error(f"{up.name}: falha ao abrir — {type(e).__name__}: {e}")
                continue
            finally:
                caminho_tmp.unlink(missing_ok=True)

            for r in rs:
                # nome do profissional: fallback = nome do arquivo enviado
                # (os parsers usam o nome do arquivo TEMPORÁRIO como último
                # recurso — 'tmpXXXX' — que aqui trocamos pelo nome real)
                if (not r.profissional.strip(" :.-")
                        or r.profissional.lower().startswith("tmp")):
                    r.profissional = Path(up.name).stem.strip().title()
                    if not r.dados.empty:
                        r.dados["profissional"] = r.profissional
                if not r.dados.empty:
                    if (r.dados["ano"] == 0).all():
                        r.dados["ano"] = ano_padrao
                    if (r.dados["mes"] == 0).all():
                        r.dados["mes"] = mes_padrao
                r.arquivo = f"{up.name}" + (f" [{r.arquivo.split('[')[-1]}"
                                            if "[" in r.arquivo else "")
                resultados.append(r)

        validos = [r for r in resultados if r.ok]
        st.markdown(f"**{len(validos)}** competência(s) válida(s) de "
                    f"**{len(uploads)}** arquivo(s):")
        linhas_resumo = []
        for r in resultados:
            d = r.dados
            linhas_resumo.append({
                "arquivo": r.arquivo,
                "status": "✅ ok" if r.ok else ("❌ " + "; ".join(r.erros)[:60]
                                               if r.erros else "vazio"),
                "profissional": r.profissional,
                "função": r.funcao,
                "competência": (f"{int(d['mes'].iat[0]):02d}/{int(d['ano'].iat[0])}"
                                if not d.empty else "—"),
                "lançamentos": len(d),
                "avisos": len(r.avisos),
            })
        st.dataframe(pd.DataFrame(linhas_resumo), use_container_width=True,
                     hide_index=True)

        avisos_todos = [f"{r.arquivo}: {a}" for r in resultados for a in r.avisos]
        if avisos_todos:
            with st.expander(f"⚠️ Avisos de qualidade ({len(avisos_todos)})"):
                for a in avisos_todos:
                    st.caption(a)

        if validos:
            st.markdown("##### Indicadores calculados a partir dos arquivos enviados")
            novos = pd.concat([r.dados for r in validos], ignore_index=True)
            ind_upload = calcular_serie(novos)
            st.dataframe(ind_upload, use_container_width=True, hide_index=True)
            st.caption("🔒 Nada foi armazenado: processamento em memória, "
                       "descartado ao fim da sessão.")

    st.divider()
    st.caption(
        "OdontoProd — TCC MBA em Data Science & Analytics (USP/Esalq). "
        "Demonstração com dados anonimizados. Fonte: planilhas mensais de produção (2022–2026), "
        "processadas por pipeline auditável. Indicadores calculados a partir "
        "dos lançamentos diários; totais sempre recalculados."
    )
