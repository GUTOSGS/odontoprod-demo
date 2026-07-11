# -*- coding: utf-8 -*-
"""
OdontoProd — Módulo 1: Parser de planilhas de produção odontológica (.ods)

Estrutura esperada (template municipal de Varginha):
  - Metadados nas primeiras linhas: MÊS, UNIDADE DE SAÚDE, DENTISTA
  - Linha de cabeçalho com os dias do mês (1..31) + coluna TOTAL
  - Bloco de agenda (sem código SIGTAP): AGENDADOS, FALTOSOS, CONSULTA NO DIA,
    CONSULTA DE RETORNO, CONSULTA DE MANUTENÇÃO, TRATAMENTO COMPLETADO (TC)
  - Linhas de procedimentos identificadas por código SIGTAP (XX.XX.XX.XXX-X)
  - Linhas TOTAL / DIAS intercaladas (ignoradas; totais são recalculados)

O parser é imune a linhas removidas/reordenadas: procedimentos são localizados
pelo código SIGTAP e o bloco de agenda pelo nome da linha.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SIGTAP_RE = re.compile(r"(\d{2}\.\d{2}\.\d{2}\.\d{3}-\d)")

# Rótulos do bloco de agenda (comparados sem acento/caixa)
ROTULOS_AGENDA = {
    "AGENDADOS": "agendados",
    "FALTOSOS": "faltosos",
    "CONSULTA NO DIA": "consulta_no_dia",
    "CONSULTA DE RETORNO": "consulta_retorno",
    "CONSULTA DE MANUTENCAO": "consulta_manutencao",
    "TRATAMENTO COMPLETADO (TC)": "tratamento_completado",
    "TRATAMENTO COMPLETADO": "tratamento_completado",
}

ROTULOS_IGNORAR = {"TOTAL", "DIAS", "PRODUCAO ODONTOLOGIA"}


def _sem_acento(txt: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(txt))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def ano_do_caminho(caminho: Path) -> int:
    """Extrai o ano do segmento de pasta mais profundo que cite UM único ano.

    Evita o falso positivo da raiz 'PRODUÇÃO MENSAL 2022_2023_2024', que
    citaria 2022 para qualquer arquivo: só aceita segmentos com exatamente
    um ano distinto (ex.: 'PRODUÇÃO MENSAL 2023').
    """
    for parte in reversed(Path(caminho).parent.parts):
        anos = set(re.findall(r"20\d{2}", parte))
        if len(anos) == 1:
            return int(anos.pop())
    return 0


@dataclass
class ResultadoParse:
    """Saída do parser para um arquivo."""
    arquivo: str
    profissional: str = ""
    funcao: str = ""          # 'dentista' | 'tecnico' | ''
    unidade: str = ""
    mes: int = 0
    ano: int = 0
    dados: pd.DataFrame = field(default_factory=pd.DataFrame)  # formato longo
    dias_trabalhados: list = field(default_factory=list)
    avisos: list = field(default_factory=list)   # qualidade de dados
    erros: list = field(default_factory=list)    # falhas de leitura

    @property
    def ok(self) -> bool:
        return not self.erros and not self.dados.empty


def _extrair_metadados(df: pd.DataFrame, res: ResultadoParse) -> None:
    """Varre as primeiras linhas atrás de MÊS, UNIDADE e DENTISTA."""
    for i in range(min(8, len(df))):
        for j in range(min(3, df.shape[1])):
            cel = df.iloc[i, j]
            if pd.isna(cel):
                continue
            txt = str(cel)
            plano = _sem_acento(txt)
            m = re.search(r"(DENTISTA|TECNIC[OA]|TSB|ASB)\s*:?\s*(.+)", plano)
            if m and m.group(2).strip(" :.-"):
                res.profissional = m.group(2).strip(" :.-")
                res.funcao = ("dentista" if m.group(1) == "DENTISTA"
                              else "tecnico")
            if "UNIDADE" in plano and "SAUDE" in plano:
                m = re.search(
                    r"UNIDADE DE SAUDE\s*:?\s*(.*?)(?:DENTISTA|TECNIC|TSB\b|ASB\b|$)",
                    plano)
                if m and m.group(1).strip():
                    res.unidade = m.group(1).strip().title()
            if plano.startswith("MES"):
                m = re.search(r"MES\s*:?\s*([A-ZÇ]+)", plano)
                if m:
                    meses = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO",
                             "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO",
                             "NOVEMBRO", "DEZEMBRO"]
                    nome = m.group(1)
                    if nome in meses:
                        res.mes = meses.index(nome) + 1


def _dias_da_linha(df: pd.DataFrame, i: int) -> dict:
    """Extrai o mapa coluna -> dia de uma linha candidata a cabeçalho."""
    mapa = {}
    for j in range(1, df.shape[1]):
        v = df.iloc[i, j]
        if isinstance(v, (int, float)) and not pd.isna(v) and 1 <= v <= 31:
            mapa[j] = int(v)
    return mapa


def _reparar_dias(mapa: dict, avisos: list) -> dict:
    """Conserta dias digitados errado quando os vizinhos permitem inferir.

    Ex.: cabeçalho ...7, 8, 4, 10... -> o 4 fora de sequência vira 9.
    """
    cols = sorted(mapa)
    dias = [mapa[j] for j in cols]
    for k in range(1, len(dias) - 1):
        fora = not (dias[k - 1] < dias[k] < dias[k + 1])
        if fora and dias[k - 1] + 2 == dias[k + 1]:
            certo = dias[k - 1] + 1
            avisos.append(
                f"Dia fora de sequência no cabeçalho: {dias[k]} entre "
                f"{dias[k-1]} e {dias[k+1]} — corrigido para {certo}"
            )
            dias[k] = certo
    # o que ainda estiver fora de ordem é descartado com aviso
    mapa_ok = {}
    ultimo = 0
    for j, d in zip(cols, dias):
        if d > ultimo:
            mapa_ok[j] = d
            ultimo = d
        else:
            avisos.append(f"Dia {d} fora de ordem no cabeçalho — coluna ignorada")
    return mapa_ok


def _linha_dias(df: pd.DataFrame, avisos: list) -> tuple[int | None, dict]:
    """Encontra a linha de cabeçalho dos dias e mapeia coluna -> dia.

    Estratégia em duas passadas:
    1. Âncora: linha cujo rótulo contém 'PRODUCAO' (ex.: PRODUÇÃO ODONTOLOGIA)
       — aceita qualquer quantidade de dias (profissionais chegam a deixar
       só os dias trabalhados).
    2. Fallback: qualquer linha com >= 15 valores crescentes entre 1 e 31.
    """
    for i in range(min(15, len(df))):
        rotulo = df.iloc[i, 0]
        if pd.notna(rotulo) and "PRODUCAO" in _sem_acento(rotulo):
            mapa = _dias_da_linha(df, i)
            if len(mapa) >= 3:
                return i, _reparar_dias(mapa, avisos)
    for i in range(min(15, len(df))):
        mapa = _dias_da_linha(df, i)
        dias = [mapa[j] for j in sorted(mapa)]
        if len(dias) >= 15 and all(a < b for a, b in zip(dias, dias[1:])):
            return i, mapa
    return None, {}


def _col_total(df: pd.DataFrame, linha_hdr: int) -> int | None:
    for j in range(df.shape[1] - 1, 0, -1):
        v = df.iloc[linha_hdr, j]
        if isinstance(v, str) and _sem_acento(v) == "TOTAL":
            return j
    return None


def parse_arquivo(caminho: str | Path) -> ResultadoParse:
    """Lê um .ods de produção e devolve dados em formato longo + avisos."""
    caminho = Path(caminho)
    res = ResultadoParse(arquivo=caminho.name)

    # ano e mês pelo caminho (fallback/confirmação)
    res.ano = ano_do_caminho(caminho)
    m_mes = re.match(r"^(\d{1,2})\s", caminho.parent.name)
    if m_mes:
        res.mes = int(m_mes.group(1))

    # profissional pelo nome do arquivo (fallback; metadados têm prioridade)
    prof_arquivo = caminho.stem.strip().title()

    try:
        engine = "odf" if caminho.suffix.lower() == ".ods" else "openpyxl"
        xl = pd.ExcelFile(caminho, engine=engine)
        df = xl.parse(xl.sheet_names[0], header=None)
    except Exception as e:
        res.erros.append(f"Falha ao abrir: {type(e).__name__}: {e}")
        return res

    mes_pasta = res.mes
    _extrair_metadados(df, res)
    if not res.profissional.strip(" :.-"):
        res.profissional = prof_arquivo
    res.profissional = res.profissional.title()
    if mes_pasta and res.mes and mes_pasta != res.mes:
        res.avisos.append(
            f"Mês do arquivo ({res.mes}) difere da pasta ({mes_pasta}) — "
            f"usando o da pasta"
        )
        res.mes = mes_pasta

    linha_hdr, mapa_dias = _linha_dias(df, res.avisos)
    if linha_hdr is None:
        res.erros.append("Cabeçalho de dias (1..31) não encontrado")
        return res
    col_total = _col_total(df, linha_hdr)

    registros = []
    for i in range(linha_hdr + 1, len(df)):
        rotulo = df.iloc[i, 0]
        if pd.isna(rotulo):
            continue
        rotulo = str(rotulo).strip()
        plano = _sem_acento(rotulo)
        if plano in ROTULOS_IGNORAR:
            continue

        m_sig = SIGTAP_RE.search(rotulo)
        if m_sig:
            codigo = m_sig.group(1)
            nome = SIGTAP_RE.sub("", rotulo).strip(" -–")
            categoria = "procedimento"
            chave = codigo
        elif plano in ROTULOS_AGENDA:
            codigo = None
            nome = rotulo
            categoria = "agenda"
            chave = ROTULOS_AGENDA[plano]
        else:
            codigo = None
            nome = rotulo
            categoria = "outros"
            chave = plano.lower().replace(" ", "_")
            res.avisos.append(f"Linha não reconhecida (mantida como 'outros'): {rotulo!r}")

        soma = 0.0
        for j, dia in mapa_dias.items():
            v = pd.to_numeric(df.iloc[i, j], errors="coerce")
            if pd.notna(v) and v != 0:
                registros.append({
                    "profissional": res.profissional,
                    "funcao": res.funcao,
                    "unidade": res.unidade,
                    "ano": res.ano,
                    "mes": res.mes,
                    "dia": dia,
                    "categoria": categoria,
                    "codigo_sigtap": codigo,
                    "chave": chave,
                    "procedimento": nome,
                    "quantidade": float(v),
                })
                soma += float(v)

        # auditoria da coluna TOTAL (recalculado tem prioridade)
        if col_total is not None:
            v_tot = pd.to_numeric(df.iloc[i, col_total], errors="coerce")
            declarado = 0.0 if pd.isna(v_tot) else float(v_tot)
            if soma != declarado:
                res.avisos.append(
                    f"TOTAL divergente em {nome!r}: declarado={declarado:g}, "
                    f"recalculado={soma:g}"
                )

    res.dados = pd.DataFrame(registros)

    # dias trabalhados = dias com qualquer lançamento clínico
    # (exclui 'agendados' e 'faltosos', que registram agenda e não presença)
    if not res.dados.empty:
        clinico = res.dados[~res.dados["chave"].isin(["agendados", "faltosos"])]
        res.dias_trabalhados = sorted(clinico["dia"].unique().tolist())

    if res.dados.empty:
        res.avisos.append("Nenhum lançamento encontrado (planilha vazia ou modelo)")

    return res


def parse_pasta(pasta: str | Path, ignorar: tuple = ("PRODUÇÃO MENSAL",)) -> list[ResultadoParse]:
    """Varre uma pasta e parseia todos os .ods (exceto modelos em branco)."""
    pasta = Path(pasta)
    resultados = []
    for arq in sorted(pasta.glob("*.ods")):
        if any(_sem_acento(p) in _sem_acento(arq.stem) for p in ignorar):
            continue
        resultados.append(parse_arquivo(arq))
    return resultados
