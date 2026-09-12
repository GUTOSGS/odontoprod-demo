# -*- coding: utf-8 -*-
"""Testes da verificação de senha (src/auth.py).

Não testam a tela de login (isso é Streamlit): testam a regra que decide se
uma senha confere — a parte que, se estiver errada, deixa o painel aberto.
"""
import hashlib

import pytest

from src.auth import ITERACOES, conferir_senha, gerar_hash


def test_senha_correta_confere():
    guardado = gerar_hash("uma senha qualquer")
    confere, legado = conferir_senha("uma senha qualquer", guardado)
    assert confere is True
    assert legado is False


@pytest.mark.parametrize("tentativa", [
    "uma senha qualquer ",      # espaço no fim
    "Uma senha qualquer",       # caixa diferente
    "uma senha qualqer",        # erro de digitação
    "",                         # vazia
])
def test_senha_errada_nao_confere(tentativa):
    guardado = gerar_hash("uma senha qualquer")
    assert conferir_senha(tentativa, guardado)[0] is False


def test_cada_hash_tem_salt_proprio():
    """Dois usuários com a mesma senha não podem ter o mesmo hash — senão o
    arquivo denuncia quem repetiu senha."""
    a, b = gerar_hash("mesma senha"), gerar_hash("mesma senha")
    assert a != b
    assert conferir_senha("mesma senha", a)[0]
    assert conferir_senha("mesma senha", b)[0]


def test_formato_do_hash_declara_algoritmo_e_custo():
    partes = gerar_hash("x").split("$")
    assert partes[0] == "pbkdf2"
    assert int(partes[1]) == ITERACOES >= 200_000     # custo mínimo aceitável
    assert len(bytes.fromhex(partes[2])) == 16        # salt de 128 bits


@pytest.mark.parametrize("guardado", [
    "pbkdf2$naoumnumero$aabb$ccdd",
    "pbkdf2$1000$zz$ccdd",
    "pbkdf2$sem-partes-suficientes",
    "",
])
def test_hash_malformado_nao_derruba_o_login(guardado):
    assert conferir_senha("qualquer", guardado) == (False, False) or \
        conferir_senha("qualquer", guardado)[0] is False


def test_hash_legado_e_aceito_mas_sinalizado(monkeypatch):
    """O formato antigo continua entrando (para não travar quem já usa),
    mas precisa avisar que deve ser regerado."""
    import src.auth as auth

    class SecretsFalso(dict):
        def __getitem__(self, chave):
            return {"salt": "salt-antigo"}

    monkeypatch.setattr(auth.st, "secrets", SecretsFalso())
    antigo = hashlib.sha256(("salt-antigo" + "senha").encode()).hexdigest()

    assert conferir_senha("senha", antigo) == (True, True)
    assert conferir_senha("outra", antigo)[0] is False
