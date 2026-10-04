"""Cas d'usage du back, partagés par l'API et le serveur MCP (cf. SPEC-back.md)."""
import json
import os
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ID_VALIDE = re.compile(r"^[a-z0-9_-]{1,64}$")


class Erreur(Exception):
    """Erreur métier, traduite en réponse HTTP par api.py : {"erreur": {"code", "message"}}."""

    def __init__(self, statut: int, code: str, message: str):
        super().__init__(message)
        self.statut, self.code, self.message = statut, code, message


def _dossier(genre: str) -> Path:
    return Path(os.environ.get("DISTINGUO_DATA", RACINE / "data")) / genre


def _chemin(genre: str, id_: str, extension: str = "json") -> Path:
    # Vérifié avant tout accès disque : un id sert de nom de fichier (pas de traversée de chemin).
    if not ID_VALIDE.match(id_):
        raise Erreur(400, "id_invalide", f"Identifiant invalide : {id_!r}")
    return _dossier(genre) / f"{id_}.{extension}"


def existe(genre: str, id_: str) -> bool:
    return _chemin(genre, id_).exists()


def ecrire_texte(genre: str, id_: str, texte: str) -> None:
    chemin = _chemin(genre, id_, "txt")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")


def lire(genre: str, id_: str) -> dict:
    chemin = _chemin(genre, id_)
    if not chemin.exists():
        raise Erreur(404, "introuvable", f"{genre}/{id_} introuvable")
    return json.loads(chemin.read_text(encoding="utf-8"))


def ecrire(genre: str, id_: str, obj: dict) -> None:
    chemin = _chemin(genre, id_)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lister(genre: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(_dossier(genre).glob("*.json"))]


def grille() -> dict:
    return json.loads((RACINE / "contracts" / "grille.json").read_text(encoding="utf-8"))
