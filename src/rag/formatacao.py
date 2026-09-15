"""Formatacao de citacoes. Modulo sem dependencia de banco ou de rede, para que
a montagem do prompt possa ser testada isoladamente."""
from __future__ import annotations

from typing import Any


def formatar_referencia(trecho: dict[str, Any]) -> str:
    """Ex.: 'MAN-MTX220-PT, pag. 2' - o que o tecnico usa para conferir a fonte."""
    paginas = (
        f"pag. {trecho['pagina_inicial']}"
        if trecho["pagina_inicial"] == trecho["pagina_final"]
        else f"pag. {trecho['pagina_inicial']}-{trecho['pagina_final']}"
    )
    codigo = trecho.get("codigo") or trecho["arquivo"]
    return f"{codigo}, {paginas}"
