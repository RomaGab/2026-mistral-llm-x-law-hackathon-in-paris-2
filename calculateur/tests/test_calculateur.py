import copy
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from calculateur import ErreurDossier, completer
from calculateur.evaluation import evaluer
from contracts.valider import erreurs_dossier

RACINE = Path(__file__).resolve().parents[2]
ENTREE = RACINE / "contracts" / "exemples" / "dossier_entree.json"


@pytest.fixture
def dossier():
    return json.loads(ENTREE.read_text(encoding="utf-8"))


def avec(dossier, **parametres):
    d = copy.deepcopy(dossier)
    d["parametres"].update(parametres)
    return d


@pytest.mark.parametrize("modele", ["logistique_bayesienne", "vote_pondere"])
def test_sortie_conforme_au_contrat(dossier, modele):
    sortie = completer(avec(dossier, modele=modele))
    assert erreurs_dossier(sortie) == []
    assert sortie["resultat"]["modele"] == modele


def test_deterministe_et_entree_intacte(dossier):
    avant = copy.deepcopy(dossier)
    assert completer(dossier) == completer(dossier)
    assert dossier == avant


@pytest.mark.parametrize("abimer", [
    lambda d: d["cas"]["facteurs"].pop("tarif_impose"),
    lambda d: d["cas"]["facteurs"].__setitem__("tarif_impose", "oui"),
    lambda d: d["decisions"][0].__setitem__("validee", False),
])
def test_dossier_invalide(dossier, abimer):
    abimer(dossier)
    with pytest.raises(ErreurDossier) as e:
        completer(dossier)
    assert e.value.problemes


def test_scenario_de_demo_la_sanction_fait_basculer(dossier):
    avant = completer(dossier)["resultat"]
    dossier["cas"]["facteurs"]["sanction_deconnexion"] = True
    apres = completer(dossier)["resultat"]
    assert avant["prediction"]["issue"] is False
    assert apres["prediction"]["issue"] is True
    assert "sanction_deconnexion" in avant["pivots"]
    ecartees = {l["id"] for l in apres["decisions"] if not l["retenue"]}
    assert "exemple-ca-paris-1" in ecartees


def test_facteur_neutralise_et_fait_inconnu(dossier):
    r = completer(dossier)["resultat"]
    charte = r["facteurs"]["charte_sociale"]
    assert charte["niveau"] == "neutralise" and not charte["est_pivot"] and charte["contribution"] == 0
    assert r["facteurs"]["sanction_deconnexion"]["contribution"] == 0  # inconnu dans le cas
    # changer un facteur neutralisé ne change rien
    d = copy.deepcopy(dossier)
    d["cas"]["facteurs"]["charte_sociale"] = True
    assert completer(d)["resultat"]["prediction"] == r["prediction"]


def test_pivots_combines(dossier):
    r = completer(avec(dossier, marge_pivot=0.25))["resultat"]
    assert r["pivots"] == []
    assert r["pivots_combines"]


def test_aucune_decision(dossier):
    dossier["decisions"] = []
    r = completer(dossier)["resultat"]
    assert erreurs_dossier({**dossier, "resultat": r}) == []
    assert any("Aucune décision" in a for a in r["avertissements"])


def test_corpus_d_un_seul_cote(dossier):
    dossier["decisions"] = [x for x in dossier["decisions"] if x["issue"]]
    r = completer(dossier)["resultat"]
    assert any("même sens" in a for a in r["avertissements"])


def test_performance_20_decisions(dossier):
    base = dossier["decisions"]
    d = copy.deepcopy(dossier)
    d["decisions"] = [{**copy.deepcopy(base[k % len(base)]), "id": f"dec-{k}"} for k in range(20)]
    for marge in (0.15, 0.40):  # 0,40 : aucun pivot simple, donc calcul des paires
        t = time.perf_counter()
        completer(avec(d, marge_pivot=marge))
        assert time.perf_counter() - t < 1.0


def _poids(sortie, decision_id):
    return next(l for l in sortie["resultat"]["decisions"] if l["id"] == decision_id)


@pytest.mark.parametrize("pays_decision, coefficient", [
    ("France", 1.0), ("Espagne", 0.35), ("CJUE", 0.6), ("Royaume-Uni", 0.08), ("USA", 0.08), ("Atlantide", 0.08),
])
def test_systeme_juridique_d_un_cas_francais(dossier, pays_decision, coefficient):
    dossier["decisions"][0]["pays"] = pays_decision
    ligne = _poids(completer(dossier), "exemple-cass-1")
    assert ligne["detail_poids"]["systeme_juridique"] == coefficient


def test_common_law_fortement_devaluee_pour_un_cas_de_civil_law(dossier):
    francais = _poids(completer(dossier), "exemple-cass-1")["poids"]
    dossier["decisions"][0]["pays"] = "Royaume-Uni"
    sortie = completer(dossier)
    assert _poids(sortie, "exemple-cass-1")["poids"] < francais / 10
    assert any("autre système juridique" in a for a in sortie["resultat"]["avertissements"])


def test_et_inversement_pour_un_cas_de_common_law(dossier):
    dossier["cas"]["pays"] = "Royaume-Uni"
    dossier["decisions"][0]["pays"] = "Royaume-Uni"
    sortie = completer(dossier)
    anglaise = _poids(sortie, "exemple-cass-1")
    francaise = _poids(sortie, "exemple-cass-2")
    assert anglaise["detail_poids"]["systeme_juridique"] == 1.0
    assert francaise["detail_poids"]["systeme_juridique"] == 0.08
    assert erreurs_dossier(sortie) == []


def test_sans_pays_tout_est_francais(dossier):
    assert "pays" not in dossier["cas"]
    assert all(l["detail_poids"]["systeme_juridique"] == 1.0 for l in completer(dossier)["resultat"]["decisions"])


def test_evaluation(dossier):
    lignes = evaluer(dossier)
    assert [nom for nom, _ in lignes][-1] == "classe majoritaire"
    assert all(s["n"] == len(dossier["decisions"]) for _, s in lignes)


@pytest.mark.parametrize("module", ["calculateur", "calculateur.evaluation"])
def test_lignes_de_commande(module):
    r = subprocess.run([sys.executable, "-m", module, str(ENTREE)], cwd=RACINE, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
