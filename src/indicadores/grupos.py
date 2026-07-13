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

# grupos que representam produção CLÍNICA curativa (para totalizações)
GRUPOS_CURATIVOS = {"Curativos e reabilitadores", "Cirúrgicos"}

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


def aplicar_grupos(df):
    """Adiciona a coluna 'grupo' a um DataFrame de lançamentos."""
    df = df.copy()
    pares = df[["codigo_sigtap", "categoria"]].drop_duplicates()
    mapa = {(c, cat): classificar(c, cat)
            for c, cat in pares.itertuples(index=False)}
    df["grupo"] = [mapa[(c, cat)] for c, cat in
                   zip(df["codigo_sigtap"], df["categoria"])]
    return df
