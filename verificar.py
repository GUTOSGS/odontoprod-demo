r"""OdontoProd — verificação local (o "CI" desta esteira).

Este projeto não tem (nem pode ter) repositório remoto: a base tem nomes
reais. Então o papel do CI é feito aqui, na máquina, antes do commit.

Roda, nesta ordem:
  1. flake8   — lint e erros de sintaxe/import
  2. pytest   — a suíte de testes (parser, motor, grupos, regras do projeto)

Uso:
    python verificar.py            # tudo
    python verificar.py --rapido   # só os testes
    python verificar.py --lint     # só o lint

Sai com código 1 se qualquer etapa falhar — é o que o hook de pre-commit lê.
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
PYTHON = sys.executable


def etapa(titulo: str, comando: list[str]) -> bool:
    print(f"\n=== {titulo} " + "=" * max(0, 60 - len(titulo)))
    resultado = subprocess.run(comando, cwd=str(RAIZ))
    ok = resultado.returncode == 0
    print(("OK  " if ok else "FALHOU  ") + titulo)
    return ok


def main() -> int:
    args = sys.argv[1:]
    so_lint = "--lint" in args
    so_teste = "--rapido" in args

    etapas = []
    if not so_teste:
        etapas.append(("flake8 (lint)", [PYTHON, "-m", "flake8", "."]))
    if not so_lint:
        etapas.append(("pytest (testes)", [PYTHON, "-m", "pytest"]))

    falhas = [titulo for titulo, cmd in etapas if not etapa(titulo, cmd)]

    print("\n" + "=" * 66)
    if falhas:
        print("VERIFICAÇÃO FALHOU em: " + ", ".join(falhas))
        return 1
    print("VERIFICAÇÃO OK — pode commitar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
