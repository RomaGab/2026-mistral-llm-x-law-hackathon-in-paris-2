"""Ingestion en lot des décisions d'un dossier (format Legora) → data/fiches/, toujours validee: false.

    uv run --env-file .env python -m back.ingerer dataset-legora/sources_jurisprudence_plateformes/sources_brutes [--limite N]
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from back import extraction, service
from back.service import Erreur

EXTENSIONS = extraction.EXTENSIONS_DOCUMENT  # TXT, PDF et DOCX (OCR)
TABLEAU = "00_Tableau_synthese_structure.json"


def slug(nom: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", Path(nom).stem).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_-]+", "-", ascii_.lower()).strip("-_")[:64].rstrip("-_")


def _notes_par_fichier(racine: Path) -> dict[str, dict]:
    chemin = racine / TABLEAU
    if not chemin.exists():
        return {}
    entrees = json.loads(chemin.read_text(encoding="utf-8"))
    return {e["fichier_source_brute"]: e for e in entrees if isinstance(e, dict) and "fichier_source_brute" in e}


def ingerer(racine, limite: int | None = None) -> list[str]:
    """Extrait chaque décision française du dossier. Saute les fiches existantes (on ne paie Mistral qu'une fois).
    `limite` borne le nombre d'appels à Mistral. Renvoie le rapport, une ligne par fichier."""
    racine = Path(racine)
    notes_de = _notes_par_fichier(racine)
    rapport, appels = [], 0
    for chemin in sorted(p for p in racine.rglob("*") if p.suffix.lower() in EXTENSIONS):
        rel = chemin.relative_to(racine).as_posix()
        notes = notes_de.get(rel)
        id_ = slug(chemin.name)
        if chemin.name.lower().startswith("readme"):
            rapport.append(f"ignoré      {rel} (README)")
        elif notes and not str(notes.get("juridiction_pays", "")).startswith("France"):
            rapport.append(f"sauté       {rel} : juridiction étrangère ({notes['juridiction_pays']})")
        elif service.existe("fiches", id_):
            rapport.append(f"déjà fait   {rel}")
        elif limite is not None and appels >= limite:
            break
        else:
            appels += 1
            try:
                texte = extraction.lire_document(chemin.name, chemin.read_bytes())
                fiche = extraction.extraire_decision(texte, id_, notes)
            except Erreur as e:
                rapport.append(f"échec       {rel} : {getattr(e, 'message', e)}")
                continue
            service.ecrire_texte("decisions", id_, texte)
            service.ecrire("fiches", id_, fiche)
            rapport.append(f"extrait     {rel} → fiches/{id_}.json")
    return rapport


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m back.ingerer", description=__doc__.splitlines()[0])
    parser.add_argument("dossier", type=Path)
    parser.add_argument("--limite", type=int, help="nombre maximal d'appels à Mistral")
    args = parser.parse_args()
    rapport = ingerer(args.dossier, args.limite)
    print("\n".join(rapport))
    return 1 if any(ligne.startswith("échec") for ligne in rapport) else 0


if __name__ == "__main__":
    sys.exit(main())
