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

# ----------------------------------------------------------------------
# Barra lateral: filtros globais
# ----------------------------------------------------------------------
st.sidebar.title("🦷 OdontoProd")
st.sidebar.caption("Demonstração pública — **dados anonimizados** · TCC MBA DSA USP/Esalq")

ini, fim = st.sidebar.select_slider(
    "Período (competência)",
    options=competencias,
    value=(competencias[0], competencias[-1]),
)

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

# ----------------------------------------------------------------------
titulo_abas = ["📊 Visão Geral", "👤 Produtividade Individual",
               "⚖️ Comparativo", "🩺 Indicadores Clínicos",
               "📁 Dados & Exportação"]
aba1, aba2, aba3, aba4, aba5 = st.tabs(titulo_abas)


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
# ABA 2 — PRODUTIVIDADE INDIVIDUAL
# ======================================================================
with aba2:
    prof = st.selectbox("Profissional",
                        sorted(f["profissional"].unique()))
    g = f[f["profissional"] == prof].sort_values("competencia")
    gp = fp[fp["profissional"] == prof]

    info = g.iloc[-1]
    st.subheader(f"{prof}")
    st.caption(f"{'Cirurgião-dentista' if info['funcao'] == 'dentista' else 'Técnico em saúde bucal'}"
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

    st.markdown("##### Matriz indicador × profissional (média no período, escala normalizada por indicador)")
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
# ABA 5 — DADOS & EXPORTAÇÃO
# ======================================================================
with aba5:
    st.subheader("Matriz de indicadores (profissional × competência)")
    st.dataframe(f.sort_values(["competencia", "profissional"]),
                 use_container_width=True, height=420)

    @st.cache_data(max_entries=3, show_spinner=False)
    def _csv_bytes(df_hashavel: pd.DataFrame) -> bytes:
        return df_hashavel.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    c1, c2 = st.columns(2)
    c1.download_button(
        "⬇️ Baixar indicadores filtrados (CSV)",
        _csv_bytes(f),
        file_name=f"indicadores_{ini}_a_{fim}.csv",
        mime="text/csv",
    )
    c2.download_button(
        "⬇️ Baixar lançamentos brutos filtrados (CSV)",
        _csv_bytes(fp),
        file_name=f"producao_{ini}_a_{fim}.csv",
        mime="text/csv",
    )

    st.divider()
    st.caption(
        "OdontoProd — TCC MBA em Data Science & Analytics (USP/Esalq). "
        "Demonstração com dados anonimizados. Fonte: planilhas mensais de produção (2022–2024), "
        "processadas por pipeline auditável. Indicadores calculados a partir "
        "dos lançamentos diários; totais sempre recalculados."
    )
