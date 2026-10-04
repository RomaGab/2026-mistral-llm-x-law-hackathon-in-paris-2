"""T8 : outils MCP pivot_*. Les outils sont des fonctions Python : on les appelle directement."""
import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from back import extraction, serveur_mcp, service

CAS = "cas_exemple1"


def test_les_trois_outils_sont_declares():
    noms = {t.name for t in anyio.run(serveur_mcp.mcp.list_tools)}
    assert noms == {"pivot_structurer_cas", "pivot_etat_du_droit", "pivot_arbitrer"}


def test_arbitrer_bloque_tant_que_la_sanction_est_inconnue(donnees_exemple):
    r = serveur_mcp.pivot_arbitrer(CAS)

    assert r["definitif"] is False
    assert "sanction_deconnexion" in [f["id"] for f in r["faits_manquants"]]
    assert r["probabilite_salariat"] + r["indice_liceite"] == 100
    assert r["position_majeure"]["libelle"] == "Indépendance"
    assert all(isinstance(x, int) for x in r["position_majeure"]["intervalle"])


def test_arbitrer_avec_un_fait_confirme_l_enregistre_et_fait_basculer(donnees_exemple):
    avant = serveur_mcp.pivot_arbitrer(CAS)

    apres = serveur_mcp.pivot_arbitrer(CAS, {"sanction_deconnexion": True})

    assert apres["position_majeure"]["libelle"] == "Salariat"
    assert apres["indice_liceite"] < avant["indice_liceite"]
    assert service.lire("cas", CAS)["facteurs"]["sanction_deconnexion"] is True


def test_hypothese_n_enregistre_rien(donnees_exemple):
    r = serveur_mcp.pivot_arbitrer(CAS, {"sanction_deconnexion": True}, hypothese=True)

    assert r["hypothese"] is True and r["position_majeure"]["libelle"] == "Salariat"
    assert service.lire("cas", CAS)["facteurs"]["sanction_deconnexion"] is None


def test_facteur_inconnu_liste_les_identifiants_valides(donnees_exemple):
    with pytest.raises(ToolError, match="sanction_deconnexion"):
        serveur_mcp.pivot_arbitrer(CAS, {"shadow_banning": True})


def test_leviers_et_decisions(donnees_exemple):
    r = serveur_mcp.pivot_arbitrer(CAS)

    assert 0 < len(r["leviers"]) <= 3
    assert all(l["valeur_actuelle"] in ("Oui", "Non") for l in r["leviers"])
    assert r["decisions_retenues"]["nombre"] == 4
    assert [d["motif"] for d in r["decisions_ecartees"]] == ["Fait déterminant divergent : Géolocalisation en temps réel"]


def test_etat_du_droit(donnees_exemple):
    r = serveur_mcp.pivot_etat_du_droit()

    assert len(r["grille"]) == 18 and len(r["corpus"]) == 5
    assert {g["sens"] for g in r["grille"]} == {"Salariat", "Indépendance", "neutre"}


def test_structurer_cas(data_vide, monkeypatch):
    monkeypatch.setattr(extraction, "appeler_mistral", lambda _: {"faits": {
        "geolocalisation_suivi": {"valeur": True, "extrait": "géolocalisés en continu", "confiance": 1}}})

    r = serveur_mcp.pivot_structurer_cas("Les livreurs sont géolocalisés en continu.", ["Pièce 1 : contrat."], "CA Paris")

    assert r["cas_id"].startswith("cas_")
    geoloc = next(f for f in r["faits"] if f["id"] == "geolocalisation_suivi")
    assert geoloc["valeur"] == "Oui" and geoloc["extrait"] == "géolocalisés en continu"
    assert "sanction_deconnexion" in [f["id"] for f in r["a_confirmer"]]
    assert len(service.lire("cas", r["cas_id"])["documents"]) == 1
