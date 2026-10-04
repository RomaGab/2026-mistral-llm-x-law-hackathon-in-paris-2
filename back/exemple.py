"""Charge le cas et les décisions FICTIVES de contracts/exemples/ dans un dossier de données séparé,
pour faire tourner le back et le calculateur en local sans clé Mistral.

    uv run python -m back.exemple                      # → data-exemple/
    DISTINGUO_DATA=data-exemple uv run uvicorn back.api:app --port 8000

Refuse d'écrire dans data/ : aucune décision [FICTIF] ne doit entrer dans le vrai corpus.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from back import service

ENTREE = service.RACINE / "contracts" / "exemples" / "dossier_entree.json"


def charger(dossier: Path) -> list[str]:
    dossier = dossier.resolve()
    if dossier == (service.RACINE / "data").resolve():
        raise SystemExit("Refusé : data/ est le vrai corpus. Choisir un autre dossier (ex. data-exemple).")
    os.environ["DISTINGUO_DATA"] = str(dossier)
    exemple = json.loads(ENTREE.read_text(encoding="utf-8"))
    for fiche in exemple["decisions"]:
        service.ecrire("fiches", fiche["id"], fiche)
    cas = service.ecrire_cas(exemple["cas"])
    return [cas["id"], *(f["id"] for f in exemple["decisions"])]


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m back.exemple", description=__doc__.splitlines()[0])
    parser.add_argument("dossier", nargs="?", type=Path, default=service.RACINE / "data-exemple")
    args = parser.parse_args()
    ids = charger(args.dossier)
    print(f"Chargé dans {args.dossier} : cas {ids[0]}, {len(ids) - 1} décisions fictives validées.")
    print(f"Lancer : DISTINGUO_DATA={args.dossier} uv run uvicorn back.api:app --port 8000")
    print(f"Puis    : curl -X POST localhost:8000/cas/{ids[0]}/analyse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
