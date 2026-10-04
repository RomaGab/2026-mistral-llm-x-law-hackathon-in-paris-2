"""Cas d'usage du back, partagés par l'API et le serveur MCP (cf. SPEC-back.md)."""
import copy
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from calculateur import ErreurDossier, completer
from contracts.valider import erreurs_dossier

RACINE = Path(__file__).resolve().parents[1]
ID_VALIDE = re.compile(r"^[a-z0-9_-]{1,64}$")
VERSION_FORMAT = "1.4"
SEUIL_CONFIANCE = 0.6  # en dessous, un fait extrait est à confirmer par l'avocat
# Valeurs par défaut du contrat (§5) ; date_reference est ajoutée à chaque analyse.
PARAMETRES = {"modele": "logistique_bayesienne", "niveau_intervalle": 0.95,
              "seuil_exception": 0.15, "seuil_sensibilite": 0.10, "marge_pivot": 0.15}
PARIS = ZoneInfo("Europe/Paris")


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


def lire_texte(genre: str, id_: str) -> str:
    chemin = _chemin(genre, id_, "txt")
    if not chemin.exists():
        raise Erreur(404, "introuvable", f"{genre}/{id_} introuvable")
    return chemin.read_text(encoding="utf-8")


def nouvel_id(prefixe: str) -> str:
    return f"{prefixe}_{secrets.token_hex(4)}"


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


# ---------------------------------------------------------------- cas

def verifier_facteurs(facteurs: dict) -> None:
    """Identifiants de la grille et valeurs true / false / null uniquement, sinon 400."""
    ids = [f["id"] for f in grille()["facteurs"]]
    inconnus = [k for k in facteurs if k not in ids]
    if inconnus:
        raise Erreur(400, "facteur_inconnu", f"Facteurs hors grille : {inconnus}. Identifiants valides : {ids}")
    mauvais = {k: v for k, v in facteurs.items() if v is not None and not isinstance(v, bool)}
    if mauvais:
        raise Erreur(400, "valeur_invalide", f"Valeurs attendues : true, false ou null. Reçu : {mauvais}")


def calculer_a_confirmer(cas: dict) -> list[str]:
    """Faits inconnus ou de confiance < 0,6, dans l'ordre de la grille."""
    preuves = cas.get("preuves", {})
    return [f["id"] for f in grille()["facteurs"]
            if cas["facteurs"].get(f["id"]) is None
            or preuves.get(f["id"], {}).get("confiance", 1.0) < SEUIL_CONFIANCE]


def ecrire_cas(cas: dict) -> dict:
    cas["a_confirmer"] = calculer_a_confirmer(cas)
    ecrire("cas", cas["id"], cas)
    return cas


TYPES_DOCUMENT = ("cas", "decision")
TAILLE_MAX = 20 * 1024 * 1024  # même garde que le front (20 Mo)


def deposer_document(nom: str, octets: bytes, type_: str) -> dict:
    """Pièce du client → data/documents/ ; décision → extraction, puis fiche validee: false (à relire)."""
    from back import extraction  # import local : extraction importe déjà service

    if type_ not in TYPES_DOCUMENT:
        raise Erreur(400, "type_invalide", f"type doit valoir 'cas' ou 'decision', pas {type_!r}")
    if len(octets) > TAILLE_MAX:
        raise Erreur(400, "trop_volumineux", f"{nom!r} dépasse 20 Mo")
    texte = extraction.lire_document(nom, octets)
    if type_ == "cas":
        id_ = nouvel_id("doc")
        ecrire_texte("documents", id_, texte)
        return {"document_id": id_, "type": "cas", "decision_id": None}
    id_ = nouvel_id("dec")
    fiche = extraction.extraire_decision(texte, id_)
    ecrire_texte("decisions", id_, texte)
    ecrire("fiches", id_, fiche)
    return {"document_id": id_, "type": "decision", "decision_id": id_}


def creer_cas(description: str, ressort: str | None = None, document_ids: list[str] | None = None,
              question: str | None = None, pieces: list[str] | None = None, pays: str | None = None) -> dict:
    """Description + pièces → faits extraits par Mistral, preuves vérifiées, a_confirmer.

    `pieces` (textes bruts, utilisé par le MCP) sont d'abord enregistrées comme documents du cas.
    """
    from back import extraction

    if not (description or "").strip():
        raise Erreur(400, "description_vide", "La description du cas est obligatoire")
    document_ids = list(document_ids or [])
    textes = [lire_texte("documents", d) for d in document_ids]  # 404 si un document est inconnu
    for piece in pieces or []:
        if piece.strip():
            id_ = nouvel_id("doc")
            ecrire_texte("documents", id_, piece)
            document_ids.append(id_)
            textes.append(piece)
    facteurs, preuves = extraction.extraire_cas(description, textes)
    cas = {"id": nouvel_id("cas"), "description": description, "ressort": ressort or None,
           "documents": document_ids, "facteurs": facteurs, "preuves": preuves}
    if question:
        cas["question"] = question
    if pays:
        cas["pays"] = pays  # absent = France (pondération par système juridique)
    return ecrire_cas(cas)


def modifier_cas(cas_id: str, facteurs: dict) -> dict:
    """Corrections de l'avocat : chaque fait modifié reçoit une preuve « utilisateur », confiance 1."""
    verifier_facteurs(facteurs)
    cas = lire("cas", cas_id)
    preuves = cas.setdefault("preuves", {})
    for f, v in facteurs.items():
        cas["facteurs"][f] = v
        preuves[f] = {"extrait": (preuves.get(f) or {}).get("extrait"), "confiance": 1.0, "source": "utilisateur"}
    return ecrire_cas(cas)


# ---------------------------------------------------------------- analyse (calculateur)

def construire_dossier(cas: dict, simulation: bool) -> dict:
    return {
        "meta": {"version_format": VERSION_FORMAT, "dossier_id": cas["id"],
                 "genere_le": datetime.now(PARIS).isoformat(timespec="seconds"), "simulation": simulation},
        "grille": grille(),
        "cas": cas,
        "decisions": [f for f in lister("fiches") if f.get("validee") is True],  # triées par id
        "parametres": {**PARAMETRES, "date_reference": datetime.now(PARIS).date().isoformat()},
        "resultat": None,
    }


def _refus(origine: str, problemes: list[str]) -> Erreur:
    return Erreur(422, f"dossier_invalide_{origine}",
                  f"Dossier refusé par le validateur ({origine}) :\n- " + "\n- ".join(problemes))


def analyser(cas_id: str, facteurs: dict | None = None) -> dict:
    """Construit le dossier, le valide, le fait compléter par le calculateur, valide le retour.

    Avec `facteurs`, c'est une simulation : ils remplacent ceux du cas pour ce calcul seulement,
    et rien n'est écrit. Aucun appel à Mistral ici (objectif : moins d'une seconde).
    """
    cas = lire("cas", cas_id)
    if facteurs is not None:
        verifier_facteurs(facteurs)
        cas = copy.deepcopy(cas)
        cas["facteurs"].update(facteurs)
        cas["a_confirmer"] = calculer_a_confirmer(cas)
    dossier = construire_dossier(cas, simulation=facteurs is not None)

    problemes = erreurs_dossier(dossier)
    if problemes:
        raise _refus("entree", problemes)
    try:
        complet = completer(dossier)
    except ErreurDossier as e:
        raise _refus("entree", e.problemes) from e
    except RuntimeError as e:  # le calculateur refuse de renvoyer un résultat contraire au contrat
        raise _refus("sortie", [str(e)]) from e
    problemes = erreurs_dossier(complet)
    if problemes:
        raise _refus("sortie", problemes)
    return complet


# ---------------------------------------------------------------- décisions (relecture du juriste)

CHAMPS_DECISION = {"intitule", "juridiction", "formation", "ressort", "date", "numero", "publication", "dispositif",
                   "issue", "textes", "remise_en_cause", "url", "validee", "facteurs", "determinants", "preuves"}


def modifier_decision(decision_id: str, champs: dict) -> dict:
    """Fusionne les champs, vérifie la fiche avec le validateur du contrat, puis l'écrit. Rien n'est écrit si elle devient invalide."""
    interdits = set(champs) - CHAMPS_DECISION
    if interdits:
        raise Erreur(400, "champ_inconnu", f"Champs non modifiables : {sorted(interdits)}")
    fiche = {**lire("fiches", decision_id), **champs}
    if "facteurs" in champs:
        fiche["facteurs"] = {**lire("fiches", decision_id)["facteurs"], **champs["facteurs"]}
    # Le validateur exige des décisions validées dans un dossier : on éprouve une copie validée.
    g = grille()
    essai = {
        "meta": {"version_format": VERSION_FORMAT, "dossier_id": "verification", "simulation": False},
        "grille": g,
        "cas": {"id": "verification", "description": "", "ressort": None,
                "facteurs": {f["id"]: None for f in g["facteurs"]}},
        "decisions": [{**fiche, "validee": True}],
        "parametres": {**PARAMETRES, "date_reference": datetime.now(PARIS).date().isoformat()},
        "resultat": None,
    }
    problemes = erreurs_dossier(essai)
    if problemes:
        raise Erreur(400, "fiche_invalide", "La fiche serait invalide :\n- " + "\n- ".join(problemes))
    ecrire("fiches", decision_id, fiche)
    return fiche
