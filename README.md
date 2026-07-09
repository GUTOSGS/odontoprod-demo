# OdontoProd — Demonstração

Painel de produtividade em saúde bucal na Atenção Primária à Saúde (APS),
desenvolvido como produto do TCC do MBA em Data Science & Analytics
(USP/Esalq).

**Todos os dados desta demonstração são anonimizados** (profissionais e
unidades identificados por códigos). A versão operacional roda em ambiente
local do município, em conformidade com a LGPD.

## Módulos

1. **Visão Geral** — indicadores-síntese da rede, evolução mensal, heatmap
2. **Produtividade Individual** — perfil do profissional vs. média da rede
3. **Comparativo** — rankings, boxplots e matriz indicador × profissional
4. **Indicadores Clínicos** — razão de tratamento completado, restaurações × exodontias × ART
5. **Dados & Exportação** — tabela analítica e download CSV

## Stack

Python · Streamlit · Plotly · pandas · Parquet

## Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configure as credenciais em `.streamlit/secrets.toml` (ver `src/auth.py`).
