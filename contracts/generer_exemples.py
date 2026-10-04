"""Génère contracts/exemples/*.json, cohérents avec le contrat v1.2.

ATTENTION : le modèle ci-dessous est un modèle JOUET (régression logistique bayésienne
minimale) qui sert uniquement à produire des exemples dont tous les chiffres sont
cohérents entre eux. Ce n'est PAS le calculateur, et ses chiffres ne veulent rien dire
juridiquement. Les décisions sont fictives.

Usage :
    uv run --with numpy --with scipy --with jsonschema python contracts/generer_exemples.py
"""
import copy
import itertools
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
from scipy.stats import norm

ICI = Path(__file__).parent
grille = json.loads((ICI / "grille.json").read_text(encoding="utf-8"))
IDS = [f["id"] for f in grille["facteurs"]]
RANG = {i: k for k, i in enumerate(IDS)}
IMP = {f["id"]: f["importance"] for f in grille["facteurs"]}
ORI = {f["id"]: f["oriente"] for f in grille["facteurs"]}
LIB = {f["id"]: f["libelle"] for f in grille["facteurs"]}
ACTIFS = [i for i in IDS if IMP[i] > 0]

PARAMETRES = {"modele": "logistique_bayesienne", "niveau_intervalle": 0.8, "date_reference": "2026-10-04",
              "seuil_exception": 0.15, "seuil_sensibilite": 0.10, "marge_pivot": 0.15}
K, SIGMA = 1.0, 0.5
EPS = 1e-9  # comparaisons sur valeurs arrondies : tolérance flottante  # a priori du modèle jouet : moyenne = sens × importance × K, écart-type SIGMA


def facteurs(**vals):
    assert not set(vals) - set(IDS), set(vals) - set(IDS)
    return {i: vals.get(i) for i in IDS}


# ------------------------------------------------------------------ données FICTIVES
def decision(id, intitule, juridiction, formation, ressort, d, publication, dispositif, issue, determinants, **vals):
    fa = facteurs(**vals)
    return {
        "id": id, "intitule": intitule, "juridiction": juridiction, "formation": formation, "ressort": ressort,
        "date": d, "numero": None, "publication": publication, "dispositif": dispositif, "issue": issue,
        "textes": ["C. trav., art. L. 1221-1", "C. trav., art. L. 8221-6"], "remise_en_cause": None, "url": None,
        "validee": True, "facteurs": fa, "determinants": determinants,
        "preuves": {k: {"extrait": "[FICTIF] extrait de la motivation", "confiance": 1.0, "source": "juriste"}
                    for k, v in fa.items() if v is not None},
    }


DECISIONS = [
    decision("exemple-cass-1", "[FICTIF] Cass. soc., 2018", "Cour de cassation, chambre sociale", "cass", None,
             "2018-11-28", "B", "cassation", True, ["geolocalisation_suivi", "sanction_deconnexion"],
             service_organise=True, geolocalisation_suivi=True, sanction_deconnexion=True, penalites_bonus=True,
             tarif_impose=True, clientele_attribuee=True, execution_dirigee=True, liberte_horaires=True, immatriculation=True),
    decision("exemple-cass-2", "[FICTIF] Cass. soc., 2020", "Cour de cassation, chambre sociale", "cass", None,
             "2020-03-04", "B", "rejet", True, ["service_organise", "sanction_deconnexion"],
             service_organise=True, sanction_deconnexion=True, tarif_impose=True, clientele_attribuee=True,
             info_masquee=True, liberte_horaires=True, execution_dirigee=True, immatriculation=True),
    decision("exemple-ca-paris-1", "[FICTIF] CA Paris, 2021", "Cour d'appel de Paris", "ca", "CA Paris",
             "2021-06-15", "na", "confirmation", False, ["sanction_deconnexion"],
             geolocalisation_suivi=True, sanction_deconnexion=False, penalites_bonus=False, liberte_horaires=True,
             multi_plateformes=True, remplacement_possible=True, immatriculation=True, moyens_propres=True, tarif_impose=True),
    decision("exemple-ca-lyon-1", "[FICTIF] CA Lyon, 2022", "Cour d'appel de Lyon", "ca", "CA Lyon",
             "2022-01-20", "na", "infirmation", False, ["geolocalisation_suivi"],
             geolocalisation_suivi=False, sanction_deconnexion=False, liberte_horaires=True, multi_plateformes=True,
             immatriculation=True, moyens_propres=True),
    decision("exemple-ca-paris-2", "[FICTIF] CA Paris, 2023", "Cour d'appel de Paris", "ca", "CA Paris",
             "2023-09-12", "na", "confirmation", False, [],
             geolocalisation_suivi=True, liberte_horaires=True, multi_plateformes=True, remplacement_possible=True,
             tarif_impose=False, immatriculation=True),
]

CAS = {
    "id": "cas_exemple1",
    "question": "Notre modèle de livraison résiste-t-il au risque de requalification ?",
    "description": "[FICTIF] Plateforme de livraison. Les livreurs choisissent leurs créneaux, l'application les "
                   "géolocalise pendant les courses, le prix de chaque course est fixé par la plateforme, ils peuvent "
                   "travailler pour d'autres applications, peuvent confier une course à un autre livreur inscrit et sont "
                   "micro-entrepreneurs.",
    "ressort": "CA Paris",
    "documents": [],
    "facteurs": facteurs(geolocalisation_suivi=True, tarif_impose=True, multi_plateformes=True,
                         remplacement_possible=True, liberte_horaires=True, immatriculation=True),
    "preuves": {
        "geolocalisation_suivi": {"extrait": "l'application les géolocalise pendant les courses", "confiance": 1.0, "source": "extraction"},
        "tarif_impose": {"extrait": "le prix de chaque course est fixé par la plateforme", "confiance": 1.0, "source": "extraction"},
        "multi_plateformes": {"extrait": "ils peuvent travailler pour d'autres applications", "confiance": 0.8, "source": "extraction"},
        "remplacement_possible": {"extrait": "peuvent confier une course à un autre livreur inscrit", "confiance": 0.7, "source": "extraction"},
        "liberte_horaires": {"extrait": "Les livreurs choisissent leurs créneaux", "confiance": 1.0, "source": "extraction"},
        "immatriculation": {"extrait": "sont micro-entrepreneurs", "confiance": 1.0, "source": "extraction"},
        "sanction_deconnexion": {"extrait": None, "confiance": 0.4, "source": "extraction"},
    },
    "a_confirmer": ["service_organise", "sanction_deconnexion", "penalites_bonus"],
}


# ------------------------------------------------------------------ modèle jouet
def r2(x):
    return round(float(x), 2) + 0.0  # + 0.0 : évite -0.0


def code(v):
    return 0.0 if v is None else (1.0 if v else -1.0)


def sig(z):
    return 1.0 / (1.0 + math.exp(-z))


def exclusion(fc, d):
    if d["remise_en_cause"]:
        return f"Solution remise en cause : {d['remise_en_cause']}"
    for k in d["determinants"]:
        if IMP[k] > 0 and fc[k] is not None and fc[k] != d["facteurs"][k]:
            return f"Fait déterminant divergent : {LIB[k]}"
    return None


AUT = {"ass_pleniere": 1.0, "ch_mixte": 1.0, "cass": 0.85, "ca": 0.5, "premiere_instance": 0.25}
POR = {"R": 1.0, "B": 0.8, "inedit": 0.4, "na": 0.3}


def detail_poids(cas, d):
    age = (date.fromisoformat(PARAMETRES["date_reference"]) - date.fromisoformat(d["date"])).days / 365.25
    geo = 1.0 if d["ressort"] is None or d["ressort"] == cas["ressort"] else 0.5
    return {"autorite": AUT[d["formation"]], "portee": POR[d["publication"]],
            "actualite": r2(math.exp(-age / 10)), "geographie": geo}


def poids(dp):
    return r2(0.5 * dp["autorite"] + 0.2 * dp["portee"] + 0.15 * dp["actualite"] + 0.15 * dp["geographie"])


def proximite(fc, fd):
    num = den = 0.0
    for i in ACTIFS:
        a, b = fc[i], fd[i]
        num += IMP[i] * (0.5 if a is None or b is None else float(a == b))
        den += IMP[i]
    return r2(num / den)


def ajuster(retenues, cas):
    n = 1 + len(ACTIFS)
    X = np.array([[1.0] + [code(d["facteurs"][f]) for f in ACTIFS] for d in retenues]).reshape(-1, n)
    y = np.array([1.0 if d["issue"] else 0.0 for d in retenues])
    w = np.array([poids(detail_poids(cas, d)) for d in retenues])
    mu = np.array([0.0] + [(1.0 if ORI[f] else -1.0) * IMP[f] * K for f in ACTIFS])
    prec = np.full(n, 1.0 / SIGMA ** 2)
    b = mu.copy()
    for _ in range(100):
        p = 1.0 / (1.0 + np.exp(-(X @ b)))
        g = X.T @ (w * (y - p)) - prec * (b - mu)
        H = X.T @ (X * (w * p * (1 - p))[:, None]) + np.diag(prec)
        pas = np.linalg.solve(H, g)
        b = b + pas
        if np.max(np.abs(pas)) < 1e-12:
            break
    p = 1.0 / (1.0 + np.exp(-(X @ b)))
    H = X.T @ (X * (w * p * (1 - p))[:, None]) + np.diag(prec)
    return b, np.linalg.inv(H)


def predire(fc, cas):
    exclues = [d["id"] for d in DECISIONS if exclusion(fc, d)]
    retenues = [d for d in DECISIONS if d["id"] not in exclues]
    b, cov = ajuster(retenues, cas)
    x = np.array([1.0] + [code(fc[f]) for f in ACTIFS])
    z, s = float(x @ b), math.sqrt(float(x @ cov @ x))
    q = norm.ppf(0.5 + PARAMETRES["niveau_intervalle"] / 2)
    return {"p": r2(sig(z)), "lo": r2(sig(z - q * s)), "hi": r2(sig(z + q * s)), "exclues": exclues, "b": b}


def completer(cas):
    fc = cas["facteurs"]
    base = predire(fc, cas)
    p = base["p"]
    issue = p > 0.5
    minor = not issue

    analyse, ecarts = {}, {}
    for f in IDS:
        v = fc[f]
        typ = "a_documenter" if v is None else "levier"
        if IMP[f] == 0:
            analyse[f] = {"est_pivot": False, "niveau": "neutralise", "type": typ,
                          "probabilite_si_vrai": p, "probabilite_si_faux": p, "contribution": 0.0,
                          "ecartees_si_vrai": base["exclues"], "ecartees_si_faux": base["exclues"]}
            continue
        res = {}
        for val in (True, False):
            if v == val:
                res[val] = (p, base["exclues"])
            else:
                pr = predire({**fc, f: val}, cas)
                res[val] = (pr["p"], pr["exclues"])
        pv, pf = res[True][0], res[False][0]
        est_pivot = any((q > 0.5) != issue and abs(q - 0.5) >= PARAMETRES["marge_pivot"] - EPS for q in (pv, pf))
        ecarts[f] = max(abs(pv - p), abs(pf - p))
        niveau = "pivot" if est_pivot else ("sensible" if ecarts[f] >= PARAMETRES["seuil_sensibilite"] - EPS else "faible")
        contribution = r2(base["b"][1 + ACTIFS.index(f)] * code(v))
        analyse[f] = {"est_pivot": est_pivot, "niveau": niveau, "type": typ,
                      "probabilite_si_vrai": pv, "probabilite_si_faux": pf, "contribution": contribution,
                      "ecartees_si_vrai": res[True][1], "ecartees_si_faux": res[False][1]}

    pivots = sorted([f for f in ACTIFS if analyse[f]["est_pivot"]], key=lambda f: (-ecarts[f], RANG[f]))

    combines = []
    if not pivots:
        def autres(f):
            return [True, False] if fc[f] is None else [not fc[f]]
        for f, g in itertools.combinations(ACTIFS, 2):
            for vf in autres(f):
                for vg in autres(g):
                    q = predire({**fc, f: vf, g: vg}, cas)["p"]
                    if (q > 0.5) != issue and abs(q - 0.5) >= PARAMETRES["marge_pivot"] - EPS:
                        combines.append({"facteurs": [f, g], "valeurs": [vf, vg], "probabilite_si": q})
        combines.sort(key=lambda c: (-abs(c["probabilite_si"] - p), RANG[c["facteurs"][0]], RANG[c["facteurs"][1]]))
        combines = combines[:5]

    lignes = []
    for d in DECISIONS:
        motif = exclusion(fc, d)
        dp = detail_poids(cas, d)
        lignes.append({"id": d["id"], "retenue": motif is None, "motif_exclusion": motif,
                       "proximite": proximite(fc, d["facteurs"]), "poids": 0.0 if motif else poids(dp),
                       "detail_poids": dp,
                       "alignement": {i: "inconnu" if fc[i] is None or d["facteurs"][i] is None
                                      else ("identique" if fc[i] == d["facteurs"][i] else "oppose") for i in IDS}})
    issue_de = {d["id"]: d["issue"] for d in DECISIONS}
    retenues = [l for l in lignes if l["retenue"]]

    maj_p = r2(max(p, 1 - p))
    majeure = {"issue": issue, "probabilite": maj_p,
               "decisions": [l["id"] for l in sorted((l for l in retenues if issue_de[l["id"]] == issue),
                                                     key=lambda l: -l["poids"] * l["proximite"])]}

    conditions = []
    for f in ACTIFS:
        for val in (True, False):
            if fc[f] == val:
                continue
            q = analyse[f]["probabilite_si_vrai" if val else "probabilite_si_faux"]
            if (q > p) if minor else (q < p):
                conditions.append({"facteur": f, "valeur": val, "probabilite_si": q})
    conditions.sort(key=lambda c: (-abs(c["probabilite_si"] - p), RANG[c["facteur"]]))
    refs = sorted((l for l in retenues if issue_de[l["id"]] == minor), key=lambda l: -l["proximite"])
    exception = None
    if (1 - maj_p) >= PARAMETRES["seuil_exception"] or pivots or combines:
        exception = {"issue": minor, "probabilite": r2(1 - maj_p), "conditions": conditions[:3],
                     "decision_reference": refs[0]["id"] if refs else None}

    return {
        "modele": PARAMETRES["modele"],
        "version_calculateur": "0.0.0-exemple-jouet",
        "prediction": {"probabilite": p, "intervalle": [base["lo"], base["hi"]], "issue": issue,
                       "incertain": base["lo"] <= 0.5 <= base["hi"]},
        "majeure": majeure,
        "exception": exception,
        "pivots": pivots,
        "pivots_combines": combines,
        "facteurs": analyse,
        "decisions": lignes,
        "avertissements": [
            "Exemple généré par un modèle jouet (contracts/generer_exemples.py) : chiffres cohérents mais sans valeur juridique.",
            "Directive (UE) 2024/2831 : présomption légale de salariat — vérifier la transposition.",
        ],
    }


def dossier(cas, simulation, avec_resultat):
    return {
        "meta": {"version_format": "1.2", "dossier_id": cas["id"], "genere_le": "2026-10-04T14:00:00+02:00",
                 "simulation": simulation},
        "grille": grille, "cas": cas, "decisions": DECISIONS, "parametres": PARAMETRES,
        "resultat": completer(cas) if avec_resultat else None,
    }


def dump(obj, nom):
    (ICI / "exemples" / nom).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    (ICI / "exemples").mkdir(exist_ok=True)
    apres = copy.deepcopy(CAS)
    apres["facteurs"]["sanction_deconnexion"] = True
    apres["preuves"]["sanction_deconnexion"] = {"extrait": "les livreurs sont désactivés après trois refus",
                                                "confiance": 1.0, "source": "utilisateur"}
    apres["a_confirmer"] = ["service_organise", "penalites_bonus"]

    dump(dossier(CAS, False, False), "dossier_entree.json")
    dump(dossier(CAS, False, True), "dossier_complet.json")
    dump(dossier(apres, True, True), "dossier_apres_bascule.json")

    sys.path.insert(0, str(ICI))
    from valider import erreurs_dossier
    for nom in ("dossier_entree.json", "dossier_complet.json", "dossier_apres_bascule.json"):
        errs = erreurs_dossier(json.loads((ICI / "exemples" / nom).read_text(encoding="utf-8")))
        print(("OK " if not errs else "KO ") + nom, *errs, sep="\n   - ")
