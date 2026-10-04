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
from jsonschema.exceptions import best_match

SCHEMA = json.loads((Path(__file__).parent / "dossier.schema.json").read_text(encoding="utf-8"))
TOL = 0.011  # tolérance d'arrondi (probabilités à 2 décimales)
EPS = 1e-9   # seuils (pivot, sensible) : comparés sur les valeurs arrondies


def erreurs_dossier(d: dict) -> list[str]:
    errs = []
    for e in Draft202012Validator(SCHEMA).iter_errors(d):
        e = best_match(e.context) if e.context else e  # oneOf : on remonte à l'erreur précise
        chemin = "/".join(map(str, e.absolute_path)) or "(racine)"
        errs.append(f"schéma : {chemin} — {e.message[:200]}")
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
        if ref is not None and (issue_de.get(ref) != exc["issue"] or not lignes.get(ref, {}).get("retenue")):
            errs.append("exception.decision_reference doit être une décision retenue, de l'issue de l'exception")
    # ---- analyse par facteur (v1.2)
    params = d["parametres"]
    seuil_s = params.get("seuil_sensibilite", 0.10)
    marge = params.get("marge_pivot", 0.15)
    issue = r["prediction"]["issue"]
    imp = {f["id"]: f["importance"] for f in d["grille"]["facteurs"]}
    exclues = [x["id"] for x in r["decisions"] if not x["retenue"]]
    af = r["facteurs"]

    def franchit(q):
        return (q > 0.5) != issue and abs(q - 0.5) >= marge - EPS

    if set(af) != S:
        errs.append("resultat.facteurs : doit couvrir exactement les facteurs de la grille")
    ecart = {}
    for f in ids:
        if f not in af:
            continue
        a, v, w = af[f], cas["facteurs"].get(f), f"resultat.facteurs[{f}]"
        pv, pf = a["probabilite_si_vrai"], a["probabilite_si_faux"]
        ecart[f] = max(abs(pv - p), abs(pf - p))
        for liste in ("ecartees_si_vrai", "ecartees_si_faux"):
            if set(a[liste]) - set(dec_ids):
                errs.append(f"{w}.{liste} : décisions inconnues {sorted(set(a[liste]) - set(dec_ids))}")
        if a["type"] != ("a_documenter" if v is None else "levier"):
            errs.append(f"{w}.type : a_documenter si le fait vaut null, levier sinon")
        if v is None and a["contribution"] != 0:
            errs.append(f"{w}.contribution : doit valoir 0 pour un fait inconnu")
        if v is not None:
            cote = "vrai" if v else "faux"
            if abs(a[f"probabilite_si_{cote}"] - p) > TOL:
                errs.append(f"{w}.probabilite_si_{cote} : doit valoir prediction.probabilite (c'est la valeur actuelle)")
            if sorted(a[f"ecartees_si_{cote}"]) != sorted(exclues):
                errs.append(f"{w}.ecartees_si_{cote} : doit être la liste actuelle des décisions écartées")
        if imp.get(f) == 0:
            if a["niveau"] != "neutralise" or a["est_pivot"] or a["contribution"] != 0 or ecart[f] > TOL:
                errs.append(f"{w} : facteur neutralisé (niveau neutralise, pas pivot, contribution 0, sans effet sur P)")
            continue
        attendu_pivot = franchit(pv) or franchit(pf)
        if a["est_pivot"] != attendu_pivot:
            errs.append(f"{w}.est_pivot : pivot si une inversion fait passer P de l'autre côté de 0,5 avec une marge de {marge}")
        if a["niveau"] == "neutralise" or (a["niveau"] == "pivot") != a["est_pivot"]:
            errs.append(f"{w}.niveau : incohérent avec est_pivot / importance")
        elif a["niveau"] == "sensible" and ecart[f] < seuil_s - EPS:
            errs.append(f"{w}.niveau : sensible exige un écart de P d'au moins {seuil_s}")
        elif a["niveau"] == "faible" and ecart[f] >= seuil_s - EPS:
            errs.append(f"{w}.niveau : faible exige un écart de P inférieur à {seuil_s}")

    pivots = r["pivots"]
    attendus = [f for f in ids if f in af and af[f]["est_pivot"]]
    if sorted(pivots) != sorted(attendus):
        errs.append("pivots : doit lister exactement les facteurs avec est_pivot = true")
    elif [ecart[f] for f in pivots] != sorted((ecart[f] for f in pivots), reverse=True):
        errs.append("pivots : à trier du plus influent au moins influent")

    if pivots and r["pivots_combines"]:
        errs.append("pivots_combines : doit être vide quand il existe des pivots simples")
    for c in r["pivots_combines"]:
        a_, b_ = c["facteurs"]
        if a_ == b_ or a_ not in S or b_ not in S or imp.get(a_) == 0 or imp.get(b_) == 0:
            errs.append(f"pivots_combines {c['facteurs']} : deux facteurs distincts et non neutralisés attendus")
        if not franchit(c["probabilite_si"]):
            errs.append(f"pivots_combines {c['facteurs']} : la combinaison doit faire basculer franchement")

    # ---- lecture a fortiori (v1.3, champs facultatifs)
    champs = ("s_applique_a_fortiori", "arguments_manquants", "arguments_contraires")
    ori = {f["id"]: f["oriente"] for f in d["grille"]["facteurs"]}

    def litteraux(faits):
        """Faits connus et non neutralisés, rangés par camp : True = favorise l'issue vraie."""
        camps = {True: [], False: []}
        for f in ids:
            v = faits.get(f)
            if v is None or imp.get(f) == 0:
                continue
            camps[ori[f] if v else not ori[f]].append({"facteur": f, "valeur": v})
        return camps

    X = litteraux(cas["facteurs"])
    for ligne in r["decisions"]:
        presents = [c in ligne for c in champs]
        if not any(presents):
            continue
        w = f"resultat.decisions[{ligne['id']}]"
        if not all(presents):
            errs.append(f"{w} : {', '.join(champs)} vont ensemble")
            continue
        dec = next((x for x in d["decisions"] if x["id"] == ligne["id"]), None)
        if dec is None:
            continue
        P, s = litteraux(dec["facteurs"]), dec["issue"]
        manquants = [l for l in P[s] if l not in X[s]]
        contraires = [l for l in X[not s] if l not in P[not s]]
        if ligne["arguments_manquants"] != manquants:
            errs.append(f"{w}.arguments_manquants : attendu {manquants}")
        if ligne["arguments_contraires"] != contraires:
            errs.append(f"{w}.arguments_contraires : attendu {contraires}")
        if ligne["s_applique_a_fortiori"] != (not manquants and not contraires):
            errs.append(f"{w}.s_applique_a_fortiori : true si et seulement si rien ne manque et rien ne s'oppose")

    seuil_exc = params.get("seuil_exception", 0.15)
    exception_attendue = bool(pivots or r["pivots_combines"] or (1 - maj["probabilite"]) >= seuil_exc - EPS)
    if (exc is not None) != exception_attendue:
        errs.append("exception : présente si et seulement s'il y a des pivots, des pivots combinés, "
                    f"ou si l'issue minoritaire atteint seuil_exception ({seuil_exc})")

    if exc is not None:
        for c in exc["conditions"]:
            f = c["facteur"]
            if f not in af:
                errs.append(f"exception.conditions : {f} hors grille")
                continue
            q = af[f]["probabilite_si_vrai" if c["valeur"] else "probabilite_si_faux"]
            if abs(c["probabilite_si"] - q) > TOL:
                errs.append(f"exception.conditions[{f}] : probabilite_si différente de resultat.facteurs")
            if (c["probabilite_si"] > p) != exc["issue"]:
                errs.append(f"exception.conditions[{f}] : doit rapprocher de l'issue de l'exception")
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
