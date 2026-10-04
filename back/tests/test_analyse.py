"""T3 (analyse, simulation), T4 (correction des faits), T6 (relecture des décisions)."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from back import service
from back.api import app
from back.service import Erreur
from contracts.valider import erreurs_dossier

CAS = "cas_exemple1"
client = TestClient(app)


# ---------------------------------------------------------------- T3 : analyse


def test_analyse_renvoie_un_dossier_complete_et_valide(donnees_exemple):
    dossier = service.analyser(CAS)

    assert erreurs_dossier(dossier) == []
    assert dossier["resultat"] is not None
    assert dossier["meta"]["simulation"] is False
    assert len(dossier["decisions"]) == 5


def test_une_decision_non_validee_n_entre_pas_dans_le_dossier(donnees_exemple):
    fiche = service.lire("fiches", "exemple-ca-paris-2")
    service.ecrire("fiches", fiche["id"], {**fiche, "validee": False})

    ids = [d["id"] for d in service.analyser(CAS)["decisions"]]

    assert "exemple-ca-paris-2" not in ids and len(ids) == 4


def test_simulation_fait_basculer_sans_rien_ecrire(donnees_exemple):
    avant = (donnees_exemple / "cas" / f"{CAS}.json").read_text(encoding="utf-8")

    base = service.analyser(CAS)["resultat"]["prediction"]
    simule = service.analyser(CAS, {"sanction_deconnexion": True})

    assert simule["meta"]["simulation"] is True
    assert base["issue"] is False and simule["resultat"]["prediction"]["issue"] is True
    assert (donnees_exemple / "cas" / f"{CAS}.json").read_text(encoding="utf-8") == avant


def test_une_fiche_validee_mais_invalide_donne_422(donnees_exemple):
    fiche = service.lire("fiches", "exemple-cass-1")
    fiche["facteurs"]["geolocalisation_suivi"] = "oui"
    service.ecrire("fiches", fiche["id"], fiche)

    with pytest.raises(Erreur) as e:
        service.analyser(CAS)

    assert e.value.statut == 422 and e.value.code == "dossier_invalide_entree"


def test_analyse_rapide(donnees_exemple):
    t = time.perf_counter()
    client.post(f"/cas/{CAS}/analyse")
    assert time.perf_counter() - t < 1.0


def test_api_analyse_et_simulation(donnees_exemple):
    r = client.post(f"/cas/{CAS}/analyse")
    s = client.post(f"/cas/{CAS}/analyse", json={"facteurs": {"sanction_deconnexion": True}})

    assert r.status_code == 200 and erreurs_dossier(r.json()) == []
    assert s.status_code == 200 and s.json()["meta"]["simulation"] is True


@pytest.mark.parametrize(
    "corps",
    [
        {"facteurs": {"sanction_deconnexion": "oui"}},
        {"facteurs": {"facteur_imaginaire": True}},
        {"facteurs": {"sanction_deconnexion": 1}},
    ],
)
def test_api_simulation_invalide_donne_400(donnees_exemple, corps):
    r = client.post(f"/cas/{CAS}/analyse", json=corps)

    assert r.status_code == 400
    assert set(r.json()["erreur"]) == {"code", "message"}


def test_api_cas_inconnu_donne_404(donnees_exemple):
    assert client.post("/cas/cas_absent/analyse").status_code == 404
    assert client.get("/cas/cas_absent").status_code == 404


# ---------------------------------------------------------------- T4 : correction des faits


def test_corriger_un_fait_l_enregistre_et_le_sort_de_a_confirmer(donnees_exemple):
    assert "sanction_deconnexion" in client.get(f"/cas/{CAS}").json()["a_confirmer"]

    r = client.patch(f"/cas/{CAS}", json={"facteurs": {"sanction_deconnexion": True}})

    cas = r.json()
    assert r.status_code == 200
    assert cas["facteurs"]["sanction_deconnexion"] is True
    assert cas["preuves"]["sanction_deconnexion"] == {"extrait": None, "confiance": 1.0, "source": "utilisateur"}
    assert "sanction_deconnexion" not in cas["a_confirmer"]
    assert service.analyser(CAS)["resultat"]["prediction"]["issue"] is True


def test_corriger_garde_l_extrait_existant(donnees_exemple):
    cas = client.patch(f"/cas/{CAS}", json={"facteurs": {"tarif_impose": False}}).json()

    assert cas["preuves"]["tarif_impose"]["extrait"] == "le prix de chaque course est fixé par la plateforme"


def test_correction_invalide_n_ecrit_rien(donnees_exemple):
    avant = client.get(f"/cas/{CAS}").json()

    r = client.patch(f"/cas/{CAS}", json={"facteurs": {"sanction_deconnexion": "oui"}})

    assert r.status_code == 400
    assert client.get(f"/cas/{CAS}").json() == avant


# ---------------------------------------------------------------- T6 : relecture des décisions


def test_lister_et_lire_les_decisions(donnees_exemple):
    assert len(client.get("/decisions").json()) == 5
    assert client.get("/decisions/exemple-cass-1").json()["issue"] is True


def test_valider_une_fiche_la_fait_entrer_dans_l_analyse(donnees_exemple):
    fiche = service.lire("fiches", "exemple-ca-paris-2")
    service.ecrire("fiches", fiche["id"], {**fiche, "validee": False})

    r = client.patch("/decisions/exemple-ca-paris-2", json={"validee": True})

    assert r.status_code == 200
    assert "exemple-ca-paris-2" in [d["id"] for d in service.analyser(CAS)["decisions"]]


@pytest.mark.parametrize(
    "champs",
    [
        {"facteurs": {"geolocalisation_suivi": None}},  # déterminant de exemple-cass-1 mis à null
        {"facteurs": {"facteur_imaginaire": True}},
        {"issue": "salariat"},
        {"id": "autre-id"},
    ],
)
def test_patch_qui_rendrait_la_fiche_invalide_donne_400_sans_ecrire(donnees_exemple, champs):
    avant = (donnees_exemple / "fiches" / "exemple-cass-1.json").read_text(encoding="utf-8")

    r = client.patch("/decisions/exemple-cass-1", json=champs)

    assert r.status_code == 400
    assert (donnees_exemple / "fiches" / "exemple-cass-1.json").read_text(encoding="utf-8") == avant


def test_exemple_refuse_d_ecrire_dans_le_vrai_corpus():
    from back import exemple

    with pytest.raises(SystemExit):
        exemple.charger(service.RACINE / "data")
    assert not any(
        "FICTIF" in json.dumps(f)
        for f in (
            json.loads(p.read_text(encoding="utf-8")) for p in (service.RACINE / "data" / "fiches").glob("*.json")
        )
    )
