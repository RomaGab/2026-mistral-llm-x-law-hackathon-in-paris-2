"""Valide un dossier Distinguo : schéma JSON + règles de cohérence.

Usage :
    uv run --with jsonschema python contracts/valider.py chemin/dossier.json [...]
ou, depuis Python :
    from contracts.valider import erreurs_dossier
    problemes = erreurs_dossier(dossier)   # liste vide = dossier valide
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).parent / "dossier.schema.json").read_text(encoding="utf-8"))
TOL = 0.011  # tolérance d'arrondi (probabilités à 2 décimales)


def erreurs_dossier(d: dict) -> list[str]:
    errs = [f"schéma : {'/'.join(map(str, e.absolute_path)) or '(racine)'} — {e.message}"
            for e in Draft202012Validator(SCHEMA).iter_errors(d)]
    if errs:
        return errs  # inutile de vérifier la cohérence d'un dossier mal formé

    ids = [f["id"] for f in d["grille"]["facteurs"]]
    S = set(ids)
    if len(ids) != len(S):
        errs.append("grille : identifiants de facteurs en double")

    def verifier_facteurs(where, facteurs, preuves=None):
        if set(facteurs) != S:
            manquants, inconnus = S - set(facteurs), set(facteurs) - S
            if manquants:
                errs.append(f"{where}.facteurs : manquants {sorted(manquants)}")
            if inconnus:
                errs.append(f"{where}.facteurs : hors grille {sorted(inconnus)}")
        if preuves and set(preuves) - S:
            errs.append(f"{where}.preuves : hors grille {sorted(set(preuves) - S)}")

    cas = d["cas"]
    verifier_facteurs("cas", cas["facteurs"], cas.get("preuves"))
    if set(cas.get("a_confirmer", [])) - S:
        errs.append(f"cas.a_confirmer : hors grille {sorted(set(cas['a_confirmer']) - S)}")

    dec_ids = [x["id"] for x in d["decisions"]]
    if len(dec_ids) != len(set(dec_ids)):
        errs.append("decisions : identifiants en double")
    issue_de = {x["id"]: x["issue"] for x in d["decisions"]}
    for x in d["decisions"]:
        w = f"decisions[{x['id']}]"
        verifier_facteurs(w, x["facteurs"], x.get("preuves"))
        if not x["validee"]:
            errs.append(f"{w} : decision non validée envoyée au calculateur")
        for k in x["determinants"]:
            if k not in S:
                errs.append(f"{w}.determinants : {k} hors grille")
            elif x["facteurs"].get(k) is None:
                errs.append(f"{w}.determinants : {k} est déterminant mais vaut null")

    r = d["resultat"]
    if r is None:
        return errs

    if r["modele"] != d["parametres"]["modele"]:
        errs.append("resultat.modele différent de parametres.modele")

    p = r["prediction"]["probabilite"]
    lo, hi = r["prediction"]["intervalle"]
    if not lo <= p <= hi:
        errs.append(f"prediction : probabilite {p} hors de l'intervalle [{lo}, {hi}]")
    if r["prediction"]["issue"] != (p > 0.5):
        errs.append("prediction.issue incohérente avec probabilite (> 0,5)")
    if r["prediction"]["incertain"] != (lo <= 0.5 <= hi):
        errs.append("prediction.incertain incohérent avec l'intervalle")

    maj = r["majeure"]
    if maj["issue"] != r["prediction"]["issue"]:
        errs.append("majeure.issue différente de prediction.issue")
    if abs(maj["probabilite"] - max(p, 1 - p)) > TOL:
        errs.append("majeure.probabilite doit valoir max(p, 1 - p)")

    lignes = {x["id"]: x for x in r["decisions"]}
    if [x["id"] for x in r["decisions"]] != dec_ids:
        errs.append("resultat.decisions : mêmes identifiants et même ordre que dossier.decisions attendus")
    for x in r["decisions"]:
        w = f"resultat.decisions[{x['id']}]"
        if x["retenue"] == (x["motif_exclusion"] is not None):
            errs.append(f"{w} : retenue = false si et seulement si motif_exclusion est renseigné")
        if set(x["alignement"]) != S:
            errs.append(f"{w}.alignement : doit couvrir exactement les facteurs de la grille")
    for i in maj["decisions"]:
        if i not in lignes or not lignes[i]["retenue"] or issue_de.get(i) != maj["issue"]:
            errs.append(f"majeure.decisions : {i} doit être retenue et avoir l'issue de la majeure")

    exc = r["exception"]
    if exc is not None:
        if exc["issue"] == maj["issue"]:
            errs.append("exception.issue doit être l'inverse de majeure.issue")
        if abs(exc["probabilite"] - (1 - maj["probabilite"])) > TOL:
            errs.append("exception.probabilite doit valoir 1 - majeure.probabilite")
        ref = exc["decision_reference"]
        if ref is not None and issue_de.get(ref) != exc["issue"]:
            errs.append("exception.decision_reference doit avoir l'issue de l'exception")
        for c in exc["conditions"]:
            if c["facteur"] not in S:
                errs.append(f"exception.conditions : {c['facteur']} hors grille")

    impacts = r["impacts"] + ([r["fait_pivot"]] if r["fait_pivot"] else [])
    for im in impacts:
        w = f"impact {im['facteur']}={im['valeur']}"
        if im["facteur"] not in S:
            errs.append(f"{w} : hors grille")
        if abs(im["delta"] - (im["probabilite_si"] - p)) > TOL:
            errs.append(f"{w} : delta doit valoir probabilite_si - probabilite")
        if im["bascule"] != ((im["probabilite_si"] > 0.5) != r["prediction"]["issue"]):
            errs.append(f"{w} : bascule incohérente")
    deltas = [abs(im["delta"]) for im in r["impacts"]]
    if deltas != sorted(deltas, reverse=True):
        errs.append("impacts : à trier par |delta| décroissant")
    if r["fait_pivot"] is not None and (not r["impacts"] or r["fait_pivot"] != r["impacts"][0]):
        errs.append("fait_pivot doit être le premier élément de impacts")
    return errs


if __name__ == "__main__":
    code = 0
    for chemin in sys.argv[1:]:
        errs = erreurs_dossier(json.loads(Path(chemin).read_text(encoding="utf-8")))
        print(f"{'OK ' if not errs else 'KO '} {chemin}")
        for e in errs:
            print(f"   - {e}")
        code |= bool(errs)
    sys.exit(code)
