# -*- coding: utf-8 -*-
"""
OdontoProd — Autenticação por perfil (admin / gestor / profissional).

Credenciais em .streamlit/secrets.toml (fora do código e fora de
versionamento). Perfis:
  - admin:        acesso total (todas as abas, todos os profissionais)
  - gestor:       acesso total de leitura (reservado para uso futuro)
  - profissional: visão individual restrita (reservado para uso futuro)

Formato do hash
---------------
Atual: PBKDF2-HMAC-SHA256, gravado como

    pbkdf2$<iteracoes>$<salt_hex>$<hash_hex>

Cada senha tem o próprio salt aleatório, e a derivação é lenta de
propósito: é o que torna inviável testar um dicionário de senhas contra o
arquivo, caso ele vaze.

Legado: hash SHA-256 simples com salt único, gravado como 64 caracteres
hexadecimais. Continua sendo aceito para não derrubar instalações
existentes, mas cada verificação bem-sucedida avisa que a senha precisa ser
regerada com `python gerar_senha.py`.
"""

import hashlib
import hmac
import os

import streamlit as st

ITERACOES = 240_000


def gerar_hash(senha: str, iteracoes: int = ITERACOES) -> str:
    """Deriva o hash de uma senha nova, com salt próprio."""
    salt = os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, iteracoes)
    return f"pbkdf2${iteracoes}${salt.hex()}${derivado.hex()}"


def _confere_legado(senha: str, guardado: str) -> bool:
    """SHA-256 com salt global — formato antigo, mantido por compatibilidade."""
    try:
        salt = st.secrets["auth"]["salt"]
    except Exception:
        return False
    calculado = hashlib.sha256((salt + senha).encode()).hexdigest()
    return hmac.compare_digest(calculado, guardado)


def conferir_senha(senha: str, guardado: str) -> tuple[bool, bool]:
    """Devolve (senha_confere, precisa_regerar)."""
    if guardado.startswith("pbkdf2$"):
        try:
            _, iteracoes, salt_hex, hash_hex = guardado.split("$")
            derivado = hashlib.pbkdf2_hmac(
                "sha256", senha.encode(), bytes.fromhex(salt_hex),
                int(iteracoes))
        except (ValueError, TypeError):
            return False, False
        return hmac.compare_digest(derivado.hex(), hash_hex), False
    return _confere_legado(senha, guardado), True


def _verificar(usuario: str, senha: str) -> dict | None:
    usuarios = st.secrets["auth"]["usuarios"]
    if usuario not in usuarios:
        return None
    cad = usuarios[usuario]
    confere, legado = conferir_senha(senha, cad["senha_hash"])
    if not confere:
        return None
    return {"usuario": usuario, "nome": cad["nome"], "papel": cad["papel"],
            "hash_legado": legado}


def exigir_login() -> dict:
    """Bloqueia o app até autenticar. Devolve dados do usuário logado."""
    if "sessao" in st.session_state:
        return st.session_state["sessao"]

    st.markdown("## 🦷 OdontoProd")
    st.caption("Painel de Produtividade em Saúde Bucal — APS Varginha/MG")

    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

    if entrar:
        sessao = _verificar(usuario.strip().lower(), senha)
        if sessao:
            st.session_state["sessao"] = sessao
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    st.stop()


def barra_usuario() -> None:
    """Mostra usuário logado e botão de sair na barra lateral."""
    sessao = st.session_state.get("sessao")
    if not sessao:
        return
    st.sidebar.divider()
    st.sidebar.caption(f"👤 **{sessao['nome']}** ({sessao['papel']})")
    if sessao.get("hash_legado"):
        st.sidebar.warning("Senha no formato antigo. Regere com "
                           "`python gerar_senha.py`.", icon="🔑")
    if st.sidebar.button("Sair", use_container_width=True):
        del st.session_state["sessao"]
        st.rerun()
