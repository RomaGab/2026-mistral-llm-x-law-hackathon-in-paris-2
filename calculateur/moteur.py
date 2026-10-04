"""completer(dossier) -> dossier : remplit le bloc `resultat` du contrat (v1.3).

Règles du contrat appliquées ici :
- toutes les probabilités sont arrondies à 2 décimales AVANT de calculer les drapeaux
  (issue, incertain, pivot, niveau), pour que front et validateur voient la même chose ;
- un dossier invalide en entrée lève ErreurDossier ; une sortie invalide est un bug et lève RuntimeError.
"""

import copy
import itertools
import math

from contracts.valider import erreurs_dossier

from .modeles import creer_modele
from .precedents import (
    TRADITIONS,
    Grille,
    a_fortiori,
    alignement,
    detail_poids,
    exclusion,
    pays,
    poids,
    proximite,
)

VERSION = "0.1.0"
EPS = 1e-9  # tolérance flottante sur les seuils, comparés sur valeurs arrondies
MAX_COMBINES = 5
MAX_CONDITIONS = 3


class ErreurDossier(ValueError):
    """Dossier refusé par le validateur du contrat. `problemes` liste tout ce qui ne va pas."""

    def __init__(self, problemes: list[str]):
        self.problemes = problemes
        super().__init__("Dossier invalide :\n- " + "\n- ".join(problemes))


def r2(x: float) -> float:
    return round(float(x), 2) + 0.0  # + 0.0 : pas de -0.0 dans le JSON


def _logit(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def completer(dossier: dict) -> dict:
    d = copy.deepcopy(dossier)
    d["resultat"] = None
    problemes = erreurs_dossier(d)
    if problemes:
        raise ErreurDossier(problemes)

    g = Grille(d["grille"])
    params = d["parametres"]
    seuil_s = params.get("seuil_sensibilite", 0.10)
    marge = params.get("marge_pivot", 0.15)
    seuil_exc = params.get("seuil_exception", 0.15)
    modele = creer_modele(d, g)
    cas, decisions = d["cas"], d["decisions"]
    fc = cas["facteurs"]

    base = modele.predire(fc)
    p, lo, hi = r2(base["p"]), r2(base["lo"]), r2(base["hi"])
    issue = p > 0.5
    minoritaire = not issue

    def franchit(q: float) -> bool:
        return (q > 0.5) != issue and abs(q - 0.5) >= marge - EPS

    # ---- analyse facteur par facteur
    analyse, ecarts = {}, {}
    for f in g.ids:
        v = fc[f]
        type_ = "a_documenter" if v is None else "levier"
        if g.importance[f] == 0:
            analyse[f] = {
                "est_pivot": False,
                "niveau": "neutralise",
                "type": type_,
                "probabilite_si_vrai": p,
                "probabilite_si_faux": p,
                "contribution": 0.0,
                "ecartees_si_vrai": base["exclues"],
                "ecartees_si_faux": base["exclues"],
            }
            continue
        res = {}
        for val in (True, False):
            if v is val:
                res[val] = (p, base["exclues"])
            else:
                pr = modele.predire({**fc, f: val})
                res[val] = (r2(pr["p"]), pr["exclues"])
        pv, pf = res[True][0], res[False][0]
        est_pivot = franchit(pv) or franchit(pf)
        ecarts[f] = max(abs(pv - p), abs(pf - p))
        niveau = "pivot" if est_pivot else ("sensible" if ecarts[f] >= seuil_s - EPS else "faible")
        # contribution : ce que le fait apporte au score par rapport à « inconnu »
        contribution = 0.0 if v is None else r2(_logit(base["p"]) - _logit(modele.predire({**fc, f: None})["p"]))
        analyse[f] = {
            "est_pivot": est_pivot,
            "niveau": niveau,
            "type": type_,
            "probabilite_si_vrai": pv,
            "probabilite_si_faux": pf,
            "contribution": contribution,
            "ecartees_si_vrai": res[True][1],
            "ecartees_si_faux": res[False][1],
        }

    pivots = sorted((f for f in g.actifs if analyse[f]["est_pivot"]), key=lambda f: (-ecarts[f], g.rang[f]))

    # ---- paires, seulement si aucun fait ne fait basculer seul
    combines = []
    if not pivots:

        def autres(f):
            return [True, False] if fc[f] is None else [not fc[f]]

        for f, h in itertools.combinations(g.actifs, 2):
            for vf in autres(f):
                for vh in autres(h):
                    q = r2(modele.predire({**fc, f: vf, h: vh})["p"])
                    if franchit(q):
                        combines.append({"facteurs": [f, h], "valeurs": [vf, vh], "probabilite_si": q})
        combines.sort(key=lambda c: (-abs(c["probabilite_si"] - p), g.rang[c["facteurs"][0]], g.rang[c["facteurs"][1]]))
        combines = combines[:MAX_COMBINES]

    # ---- une ligne par décision, dans l'ordre du dossier
    lignes = []
    for dec in decisions:
        motif = exclusion(fc, dec, g)
        dp = detail_poids(cas, dec, params["date_reference"])
        lignes.append(
            {
                "id": dec["id"],
                "retenue": motif is None,
                "motif_exclusion": motif,
                "proximite": proximite(fc, dec, g),
                "poids": 0.0 if motif else poids(dp),
                "detail_poids": dp,
                "alignement": alignement(fc, dec, g),
                **a_fortiori(fc, dec, g),
            }
        )
    issue_de = {dec["id"]: dec["issue"] for dec in decisions}
    retenues = [l for l in lignes if l["retenue"]]

    maj_p = r2(max(p, 1 - p))
    majeure = {
        "issue": issue,
        "probabilite": maj_p,
        "decisions": [
            l["id"]
            for l in sorted(
                (l for l in retenues if issue_de[l["id"]] == issue), key=lambda l: -l["poids"] * l["proximite"]
            )
        ],
    }

    conditions = []
    for f in g.actifs:
        for val in (True, False):
            if fc[f] is val:
                continue
            q = analyse[f]["probabilite_si_vrai" if val else "probabilite_si_faux"]
            if (q > p) if minoritaire else (q < p):
                conditions.append({"facteur": f, "valeur": val, "probabilite_si": q})
    conditions.sort(key=lambda c: (-abs(c["probabilite_si"] - p), g.rang[c["facteur"]]))
    refs = sorted((l for l in retenues if issue_de[l["id"]] == minoritaire), key=lambda l: -l["proximite"])
    exception = None
    if (1 - maj_p) >= seuil_exc - EPS or pivots or combines:
        exception = {
            "issue": minoritaire,
            "probabilite": r2(1 - maj_p),
            "conditions": conditions[:MAX_CONDITIONS],
            "decision_reference": refs[0]["id"] if refs else None,
        }

    d["resultat"] = {
        "modele": params["modele"],
        "version_calculateur": VERSION,
        "prediction": {"probabilite": p, "intervalle": [lo, hi], "issue": issue, "incertain": lo <= 0.5 <= hi},
        "majeure": majeure,
        "exception": exception,
        "pivots": pivots,
        "pivots_combines": combines,
        "facteurs": analyse,
        "decisions": lignes,
        "avertissements": _avertissements(cas, decisions, retenues, issue_de),
    }

    problemes = erreurs_dossier(d)
    if problemes:
        raise RuntimeError("Bug du calculateur : résultat contraire au contrat :\n- " + "\n- ".join(problemes))
    return d


def _avertissements(cas: dict, decisions: list, retenues: list, issue_de: dict) -> list[str]:
    out = []
    if not retenues:
        out.append("Aucune décision retenue : le résultat ne repose que sur la grille du juriste.")
    elif len({issue_de[l["id"]] for l in retenues}) == 1:
        out.append("Toutes les décisions retenues vont dans le même sens : l'autre issue n'a aucun précédent.")
    etrangeres = [dec for dec in decisions if pays(dec) != pays(cas)]
    if etrangeres:
        out.append(
            f"{len(etrangeres)} décision(s) d'un autre système juridique que le cas ({pays(cas)}) : "
            "poids fortement réduit (×0,35 même tradition, ×0,08 tradition opposée)."
        )
    inconnus = sorted({pays(dec) for dec in decisions} - set(TRADITIONS))
    if inconnus:
        out.append(f"Pays absents de la table des traditions juridiques : {', '.join(inconnus)} (coefficient minimal).")
    if any("[FICTIF]" in dec.get("intitule", "") for dec in decisions):
        out.append("Le dossier contient des décisions fictives ([FICTIF]) : à ne pas utiliser en démo.")
    return out
