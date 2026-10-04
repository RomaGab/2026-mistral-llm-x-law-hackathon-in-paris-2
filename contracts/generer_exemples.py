"""Génère contracts/exemples/*.json avec le VRAI calculateur (calculateur.completer).

Les décisions et le cas sont fictifs ([FICTIF]) : ils servent à développer, pas à la démo.
Si le contrat ou le calculateur change, relancer ce script depuis la racine du dépôt :

    uv run python contracts/generer_exemples.py
"""
import copy
import json
import sys
from pathlib import Path

ICI = Path(__file__).parent
sys.path.insert(0, str(ICI.parent))  # racine du dépôt : rend calculateur et contracts importables

from calculateur import completer  # noqa: E402
from contracts.valider import erreurs_dossier  # noqa: E402

grille = json.loads((ICI / "grille.json").read_text(encoding="utf-8"))
IDS = [f["id"] for f in grille["facteurs"]]

PARAMETRES = {"modele": "logistique_bayesienne", "niveau_intervalle": 0.95, "date_reference": "2026-10-04",
              "seuil_exception": 0.15, "seuil_sensibilite": 0.10, "marge_pivot": 0.15}


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


def dossier(cas, simulation):
    return {
        "meta": {"version_format": "1.3", "dossier_id": cas["id"], "genere_le": "2026-10-04T14:00:00+02:00",
                 "simulation": simulation},
        "grille": grille, "cas": cas, "decisions": DECISIONS, "parametres": PARAMETRES, "resultat": None,
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

    dump(dossier(CAS, False), "dossier_entree.json")
    dump(completer(dossier(CAS, False)), "dossier_complet.json")
    dump(completer(dossier(apres, True)), "dossier_apres_bascule.json")

    for nom in ("dossier_entree.json", "dossier_complet.json", "dossier_apres_bascule.json"):
        errs = erreurs_dossier(json.loads((ICI / "exemples" / nom).read_text(encoding="utf-8")))
        print(("OK " if not errs else "KO ") + nom, *errs, sep="\n   - ")
