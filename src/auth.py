# -*- coding: utf-8 -*-
"""
OdontoProd — Autenticação por perfil (admin / gestor / profissional).

Credenciais em .streamlit/secrets.toml (hash SHA-256 com salt), fora do
código e fora de versionamento. Perfis:
  - admin:        acesso total (todas as abas, todos os profissionais)
  - gestor:       acesso total de leitura (reservado para uso futuro)
  - profissional: visão individual restrita (reservado para uso futuro)
"""

import hashlib
import hmac

import streamlit as st


def _hash(senha: str) -> str:
    salt = st.secrets["auth"]["salt"]
    return hashlib.sha256((salt + senha).encode()).hexdigest()


def _verificar(usuario: str, senha: str) -> dict | None:
    usuarios = st.secrets["auth"]["usuarios"]
    if usuario not in usuarios:
        return None
    cad = usuarios[usuario]
    if hmac.compare_digest(_hash(senha), cad["senha_hash"]):
        return {"usuario": usuario, "nome": cad["nome"], "papel": cad["papel"]}
    return None


def exigir_login() -> dict:
    """Bloqueia o app até autenticar. Devolve dados do usuário logado."""
    if "sessao" in st.session_state:
        return st.session_state["sessao"]

    st.markdown("## 🦷 OdontoProd")
    st.caption("Painel de Produtividade em Saúde Bucal — demonstração com dados anonimizados")

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
    if st.sidebar.button("Sair", use_container_width=True):
        del st.session_state["sessao"]
        st.rerun()
