# -*- coding: utf-8 -*-
"""Temporário (capturar_prints.py) — abre a demo já autenticada."""
from pathlib import Path

import streamlit as st

st.session_state.setdefault("sessao", {"usuario": "demo",
                                       "nome": "Demonstração",
                                       "papel": "admin"})
APP = Path(__file__).parent / "app.py"
exec(compile(APP.read_text(encoding="utf-8"), str(APP), "exec"))
