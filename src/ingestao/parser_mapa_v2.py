# -*- coding: utf-8 -*-
"""
OdontoProd — Parser do template v2 (2025+): "MAPA DE PRODUÇÃO ODONTOLÓGICA".

Diferenças em relação ao template v1 (2022-2024, ver parser_ods.py):
  - Pasta de trabalho com abas nomeadas: 'CIRURGIÃO-DENTISTA' e
    'TÉCNICA_EM_SAÚDE_BUCAL' (e, nos .xlsx multi-mês, uma aba por
    competência: 'ABRIL 2025', 'MAIO 2025', ...).
  - Cabeçalho de dias na linha de seção '1- CONSULTAS' (dias podem vir
    como texto); células de fim de semana/feriado marcadas com S/D/F.
  - Metadados: 'MÊS/ANO: <texto livre>', 'NOME CIRURGIÃO-DENTISTA: ...',
    'UNIDADE DE SAUDE: ...'.
  - Linhas de seção numeradas ('2 - ACOLHIMENTO...'), TOTAL por seção e
    coluna extra 'MÉDIA FALTAS / DIA' ao final.

Um arquivo v2 pode gerar VÁRIOS resultados (um por aba com lançamentos).
"""

import re
from pathlib import Path

import pandas as pd

from .parser_ods import (ResultadoParse, ROTULOS_AGENDA, SIGTAP_RE,
                         _reparar_dias, _sem_acento, ano_do_caminho)

MESES_NOME = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5,
    "JUNHO": 6, "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

ROTULOS_IGNORAR_V2 = {"TOTAL", "DIAS"}
SECAO_RE = re.compile(r"^\d+\s*-\s")  # '1- CONSULTAS', '2 - ACOLHIMENTO...'


def eh_template_v2(sheet_names: list[str]) -> bool:
    """v2 = tem aba de função (CD/TSB) OU abas nomeadas por competência
    (ex.: 'AGOSTO 2025', 'JULHO25')."""
    for s in sheet_names:
        plano = _sem_acento(s)
        if "CIRURGI" in plano or "TECNIC" in plano or "TSB" in plano:
            return True
        if any(nome in plano for nome in MESES_NOME):
            return True
    return False


def _mes_ano_de_texto(txt: str) -> tuple[int, int]:
    """Extrai (mes, ano) de texto livre: 'AGOSTO DE 2025', 'Janeiro 25'..."""
    plano = _sem_acento(txt)
    mes = 0
    for nome, num in MESES_NOME.items():
        if nome in plano:
            mes = num
            break
    ano = 0
    m4 = re.search(r"20\d{2}", plano)
    if m4:
        ano = int(m4.group(0))
    else:
        # '25' isolado ou colado ao nome do mês (ex.: 'JULHO25')
        m2 = re.search(r"\b(2[2-9])\b", plano) or re.search(r"(2[2-9])\s*$", plano)
        if m2:
            ano = 2000 + int(m2.group(1))
    return mes, ano


def _mes_da_pasta(nome: str) -> int:
    m = re.match(r"^(\d{1,2})\b", nome.strip())
    if m:
        return int(m.group(1))
    mes, _ = _mes_ano_de_texto(nome)
    return mes


def _linha_dias_v2(df: pd.DataFrame, avisos: list) -> tuple[int | None, dict]:
    """Dias na linha '1- CONSULTAS' (ou 1ª linha com sequência 1..N).

    No v2 os dias podem vir como TEXTO ('1','2',...): coerção numérica.
    """
    candidatas = []
    for i in range(min(20, len(df))):
        rotulo = df.iloc[i, 0]
        if pd.notna(rotulo) and SECAO_RE.match(str(rotulo).strip()):
            candidatas.append(i)
            break  # a 1ª seção é o cabeçalho de dias
    candidatas += [i for i in range(min(20, len(df))) if i not in candidatas]

    for i in candidatas:
        mapa = {}
        for j in range(1, df.shape[1]):
            v = pd.to_numeric(df.iloc[i, j], errors="coerce")
            if pd.notna(v) and 1 <= v <= 31 and float(v).is_integer():
                mapa[j] = int(v)
        dias = [mapa[j] for j in sorted(mapa)]
        if len(dias) >= 15 or (len(dias) >= 3 and i == candidatas[0]):
            if dias and dias[0] <= 3:
                return i, _reparar_dias(mapa, avisos)
    return None, {}


def _col_total_v2(df: pd.DataFrame, linha_hdr: int) -> int | None:
    for j in range(df.shape[1] - 1, 0, -1):
        v = df.iloc[linha_hdr, j]
        if isinstance(v, str) and _sem_acento(v) == "TOTAL":
            return j
    return None


def _parse_aba(df: pd.DataFrame, res: ResultadoParse) -> None:
    """Extrai metadados e lançamentos de uma aba v2 para dentro de `res`."""
    # metadados (primeiras ~6 linhas, colunas 0-1)
    for i in range(min(6, len(df))):
        for j in range(min(2, df.shape[1])):
            cel = df.iloc[i, j]
            if pd.isna(cel):
                continue
            txt = str(cel)
            plano = _sem_acento(txt)
            if plano.startswith("MES/ANO"):
                mes, ano = _mes_ano_de_texto(txt)
                if mes:
                    res.mes = mes
                if ano:
                    res.ano = ano
            # função pelo rótulo do campo de nome ('NOME TSB:', 'NOME
            # CIRURGIÃO-DENTISTA:'), mesmo quando o nome vem em branco
            if re.search(r"NOME\s+(TSB|ASB|TECNIC)", plano):
                res.funcao = "tecnico"
            elif re.search(r"NOME\s+CIRURGI|NOME\s+DENTISTA", plano):
                res.funcao = "dentista"
            m = re.search(r"(DENTISTA|TSB|ASB|TECNIC[OA](?:\s+EM)?[_ ]?"
                          r"(?:SAUDE)?[_ ]?(?:BUCAL)?)\s*:\s*(.+)", plano)
            if m and m.group(2).strip(" :.-"):
                nome = m.group(2).strip(" :.-")
                # descarta se o campo foi preenchido com mês/ano por engano
                if not any(k in nome for k in MESES_NOME):
                    res.profissional = nome
            if "UNIDADE" in plano and "SAUDE" in plano:
                m = re.search(r"UNIDADE DE SAUDE\s*:?\s*(.*?)$", plano)
                if m and m.group(1).strip():
                    res.unidade = m.group(1).strip().title()

    linha_hdr, mapa_dias = _linha_dias_v2(df, res.avisos)
    if linha_hdr is None:
        res.erros.append("v2: cabeçalho de dias não encontrado")
        return
    col_total = _col_total_v2(df, linha_hdr)

    registros = []
    for i in range(linha_hdr + 1, len(df)):
        rotulo = df.iloc[i, 0]
        if pd.isna(rotulo):
            continue
        rotulo = str(rotulo).strip()
        plano = _sem_acento(rotulo)
        if plano in ROTULOS_IGNORAR_V2 or SECAO_RE.match(rotulo):
            continue

        m_sig = SIGTAP_RE.search(rotulo)
        if m_sig:
            codigo = m_sig.group(1)
            nome = SIGTAP_RE.sub("", rotulo).strip(" -–")
            categoria, chave = "procedimento", codigo
        elif plano in ROTULOS_AGENDA:
            codigo, nome = None, rotulo
            categoria, chave = "agenda", ROTULOS_AGENDA[plano]
        else:
            codigo, nome = None, rotulo
            categoria = "outros"
            chave = plano.lower().replace(" ", "_")[:60]

        soma = 0.0
        for j, dia in mapa_dias.items():
            v = pd.to_numeric(df.iloc[i, j], errors="coerce")  # S/D/F -> NaN
            if pd.notna(v) and v != 0:
                registros.append({
                    "profissional": res.profissional,
                    "funcao": res.funcao,
                    "unidade": res.unidade,
                    "ano": res.ano, "mes": res.mes, "dia": dia,
                    "categoria": categoria, "codigo_sigtap": codigo,
                    "chave": chave, "procedimento": nome,
                    "quantidade": float(v),
                })
                soma += float(v)

        if col_total is not None and categoria == "procedimento":
            v_tot = pd.to_numeric(df.iloc[i, col_total], errors="coerce")
            declarado = 0.0 if pd.isna(v_tot) else float(v_tot)
            if soma != declarado:
                res.avisos.append(f"TOTAL divergente em {nome!r}: "
                                  f"declarado={declarado:g}, recalculado={soma:g}")

    res.dados = pd.DataFrame(registros)
    if not res.dados.empty:
        clinico = res.dados[~res.dados["chave"].isin(["agendados", "faltosos"])]
        res.dias_trabalhados = sorted(clinico["dia"].unique().tolist())


def parse_arquivo_v2(caminho: str | Path) -> list[ResultadoParse]:
    """Parseia um arquivo do template v2. Devolve um resultado por aba
    com lançamentos (CD, TSB e/ou abas mensais dos .xlsx multi-mês)."""
    caminho = Path(caminho)
    engine = "odf" if caminho.suffix.lower() == ".ods" else "openpyxl"
    ano_pasta = ano_do_caminho(caminho)
    mes_pasta = _mes_da_pasta(caminho.parent.name)
    prof_arquivo = caminho.stem.strip().title()

    try:
        xl = pd.ExcelFile(caminho, engine=engine)
    except Exception as e:
        r = ResultadoParse(arquivo=caminho.name)
        r.erros.append(f"Falha ao abrir: {type(e).__name__}: {e}")
        return [r]

    resultados = []
    for aba in xl.sheet_names:
        plano_aba = _sem_acento(aba)
        if "CIRURGI" in plano_aba:
            funcao = "dentista"
            mes_aba = ano_aba = 0
        elif "TECNIC" in plano_aba or "TSB" in plano_aba:
            funcao = "tecnico"
            mes_aba = ano_aba = 0
        else:
            mes_aba, ano_aba = _mes_ano_de_texto(aba)
            if not mes_aba:
                continue  # aba não reconhecida (instruções etc.)
            funcao = "dentista"  # abas mensais dos .xlsx são do CD titular

        try:
            df = xl.parse(aba, header=None)
        except Exception as e:
            r = ResultadoParse(arquivo=f"{caminho.name}[{aba}]")
            r.erros.append(f"Falha na aba: {type(e).__name__}: {e}")
            resultados.append(r)
            continue
        if df.empty:
            continue

        res = ResultadoParse(arquivo=f"{caminho.name}[{aba}]")
        res.funcao = funcao
        res.mes, res.ano = mes_aba, ano_aba
        _parse_aba(df, res)

        # o NOME DA ABA prevalece sobre o metadado interno (abas copiadas
        # costumam manter o cabeçalho MÊS/ANO desatualizado)
        if mes_aba and res.mes != mes_aba:
            res.avisos.append(f"MÊS/ANO interno ({res.mes:02d}) difere do "
                              f"nome da aba ({aba!r}) — usando o da aba")
            res.mes = mes_aba
        if ano_aba:
            res.ano = ano_aba

        if res.dados.empty:
            continue  # aba de template sem lançamentos: ignora em silêncio

        # resolução final de competência: aba > metadado > pasta
        if not res.mes:
            res.mes = mes_pasta
        elif mes_aba == 0 and mes_pasta and res.mes != mes_pasta:
            res.avisos.append(
                f"Competência do arquivo ({res.mes:02d}/{res.ano or '?'}) "
                f"difere da pasta ({mes_pasta:02d}/{ano_pasta or '?'}) — "
                f"usando a da pasta")
            res.mes = mes_pasta
            if ano_pasta:
                res.ano = ano_pasta
        if not res.ano:
            res.ano = ano_pasta
        # plausibilidade temporal: template v2 existe desde 2025
        if res.ano and not (2022 <= res.ano <= 2035):
            res.avisos.append(f"Ano implausível no arquivo ({res.ano}) — "
                              f"usando o da pasta ({ano_pasta})")
            res.ano = ano_pasta
        if not res.profissional.strip(" :.-"):
            res.profissional = prof_arquivo
        res.profissional = res.profissional.title()
        if res.mes:
            res.dados["mes"] = res.mes
        if res.ano:
            res.dados["ano"] = res.ano
        res.dados["profissional"] = res.profissional
        res.dados["funcao"] = res.funcao
        res.dados["unidade"] = res.unidade
        resultados.append(res)

    if not resultados:
        r = ResultadoParse(arquivo=caminho.name)
        r.avisos.append("v2: nenhuma aba com lançamentos")
        resultados.append(r)
    return resultados
