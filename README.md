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

## Testes

A suíte cobre o motor de indicadores, o classificador de grupos de produção,
o parser das planilhas municipais (incluindo planilha com defeito proposital:
mês divergente, dia fora de sequência, total que não fecha e linha criada à
mão) e a **anonimização dos dados publicados aqui**.

```bash
pip install -r requirements-dev.txt
python verificar.py          # flake8 + pytest
python -m pytest             # só os testes
```

O teste de anonimização (`tests/test_anonimizacao.py`) falha se algum
identificador real, ou algum arquivo do ambiente local com dado nominal,
chegar a este repositório — é a guarda que mantém a demonstração publicável.
