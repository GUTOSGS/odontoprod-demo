# -*- coding: utf-8 -*-
"""
OdontoProd — Classificação dos lançamentos em grupos de produção.

Regra central: consultas/agenda (sem código SIGTAP) e procedimentos
preventivos NUNCA são somados com procedimentos curativos/cirúrgicos.
A classificação usa o prefixo do código SIGTAP (grupo da tabela SUS):
  01 = ações de promoção e prevenção      02 = diagnóstico
  03.01 = consultas/atendimentos          03.07 = clínicos (dentística,
  endodontia, periodontia, prótese)       04 = cirúrgicos
"""

# ordem de exibição dos grupos
ORDEM_GRUPOS = [
    "Consultas e agenda (sem código SIGTAP)",
    "Atendimentos e consultas (SIGTAP)",
    "Preventivos e ações coletivas",
    "Diagnósticos (radiografias, biópsias)",
    "Curativos e reabilitadores",
    "Cirúrgicos",
    "Demais procedimentos SIGTAP",
    "Outros registros (sem código SIGTAP)",
]

# profilaxia/remoção de placa é 03.07 mas de natureza preventiva
_PREVENTIVOS_FORA_01 = {"03.07.03.004-0"}


def classificar(codigo_sigtap, categoria: str) -> str:
    """Devolve o grupo de produção de um lançamento."""
    if categoria == "agenda":
        return "Consultas e agenda (sem código SIGTAP)"
    if categoria == "outros" or not codigo_sigtap:
        return "Outros registros (sem código SIGTAP)"
    c = str(codigo_sigtap)
    if c in _PREVENTIVOS_FORA_01:
        return "Preventivos e ações coletivas"
    if c.startswith("01."):
        return "Preventivos e ações coletivas"
    if c.startswith("02."):
        return "Diagnósticos (radiografias, biópsias)"
    if c.startswith("03.01."):
        return "Atendimentos e consultas (SIGTAP)"
    if c.startswith("03.07.") or c.startswith("07."):
        return "Curativos e reabilitadores"
    if c.startswith("04."):
        return "Cirúrgicos"
    return "Demais procedimentos SIGTAP"


def _normalizar_codigo(valor) -> str:
    """Devolve o código como texto, com qualquer forma de vazio virando "".

    Necessário porque a coluna pode trazer None, NaN do numpy ou NaN do
    pandas conforme a origem (parquet, CSV, upload, concatenação). Como
    NaN != NaN, usar o valor cru como chave de dicionário levanta KeyError
    quando dois nulos de origens diferentes convivem na mesma coluna.
    """
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() in ("nan", "none", "<na>") else texto


def aplicar_grupos(df):
    """Adiciona a coluna 'grupo' a um DataFrame de lançamentos."""
    df = df.copy()
    codigos = [_normalizar_codigo(c) for c in df["codigo_sigtap"]]
    categorias = [str(cat) for cat in df["categoria"]]
    mapa = {par: classificar(par[0] or None, par[1])
            for par in set(zip(codigos, categorias))}
    df["grupo"] = [mapa[par] for par in zip(codigos, categorias)]
    return df
