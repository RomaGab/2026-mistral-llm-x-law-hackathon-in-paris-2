"""Évaluation en retirant chaque décision tour à tour (leave-one-out).

    python -m calculateur.evaluation dossier.json

Pour chaque décision : on la retire du dossier, on prend ses faits comme cas, et on prédit
son issue avec les autres décisions. Limite à garder en tête : les faits d'une décision
viennent de sa propre motivation, ce qui avantage tous les modèles (fuite).
"""
import argparse
import copy
import json
from pathlib import Path

from contracts.valider import erreurs_dossier

from .modeles import creer_modele
from .moteur import ErreurDossier, r2
from .precedents import Grille

CONFIGURATIONS = [
    ("logistique σ=0,2", {"modele": "logistique_bayesienne", "sigma_a_priori": 0.2}),
    ("logistique σ=0,3", {"modele": "logistique_bayesienne", "sigma_a_priori": 0.3}),
    ("logistique σ=0,5", {"modele": "logistique_bayesienne", "sigma_a_priori": 0.5}),
    ("vote pondéré κ=2", {"modele": "vote_pondere", "kappa": 2.0}),
]


def _predictions(dossier: dict, params: dict) -> list[tuple[float, bool, bool]]:
    """(p, incertain, issue réelle) pour chaque décision retirée tour à tour."""
    sortie = []
    decisions = dossier["decisions"]
    for k, dec in enumerate(decisions):
        sous = copy.deepcopy(dossier)
        sous["decisions"] = decisions[:k] + decisions[k + 1:]
        sous["cas"] = {"id": f"loo_{dec['id']}", "description": "", "ressort": dec["ressort"],
                       "facteurs": dict(dec["facteurs"])}
        sous["parametres"] = {**dossier["parametres"], **params}
        pr = creer_modele(sous, Grille(sous["grille"])).predire(sous["cas"]["facteurs"])
        p, lo, hi = r2(pr["p"]), r2(pr["lo"]), r2(pr["hi"])
        sortie.append((p, lo <= 0.5 <= hi, dec["issue"]))
    return sortie


def _majoritaire(dossier: dict) -> list[tuple[float, bool, bool]]:
    decisions = dossier["decisions"]
    sortie = []
    for k, dec in enumerate(decisions):
        autres = decisions[:k] + decisions[k + 1:]
        p = sum(a["issue"] for a in autres) / len(autres) if autres else 0.5
        sortie.append((r2(p), False, dec["issue"]))
    return sortie


def _scores(preds: list[tuple[float, bool, bool]]) -> dict:
    n = len(preds)
    nets = [(p, y) for p, inc, y in preds if not inc]
    return {
        "n": n,
        "justes": sum((p > 0.5) == y for p, _, y in preds),
        "nets": len(nets),
        "justes_nets": sum((p > 0.5) == y for p, y in nets),
        "brier": sum((p - float(y)) ** 2 for p, _, y in preds) / n if n else float("nan"),
    }


def evaluer(dossier: dict) -> list[tuple[str, dict]]:
    d = copy.deepcopy(dossier)
    d["resultat"] = None
    problemes = erreurs_dossier(d)
    if problemes:
        raise ErreurDossier(problemes)
    lignes = [(nom, _scores(_predictions(d, params))) for nom, params in CONFIGURATIONS]
    lignes.append(("classe majoritaire", _scores(_majoritaire(d))))
    return lignes


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m calculateur.evaluation", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dossier", type=Path)
    args = parser.parse_args()
    lignes = evaluer(json.loads(args.dossier.read_text(encoding="utf-8")))

    print(f"{'modèle':22s} {'justes':>8s} {'nets':>6s} {'justes/nets':>12s} {'brier':>7s}")
    for nom, s in lignes:
        print(f"{nom:22s} {s['justes']:>4d}/{s['n']:<3d} {s['nets']:>6d} {s['justes_nets']:>7d}/{s['nets']:<4d} {s['brier']:>7.3f}")
    logistiques = [(nom, s) for nom, s in lignes if nom.startswith("logistique")]
    meilleur = min(logistiques, key=lambda x: x[1]["brier"])
    print(f"\nσ recommandé (meilleur Brier) : {meilleur[0]}")
    if lignes[0][1]["n"] < 15:
        print("Attention : moins de 15 décisions, ces chiffres sont très instables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
