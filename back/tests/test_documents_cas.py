"""T5 (lecture TXT / PDF / DOCX) et T7 (dépôt de documents, création d'un cas). Mistral est simulé."""
import pytest
from fastapi.testclient import TestClient

from back import extraction, service
from back.api import app
from back.service import Erreur
from contracts.valider import erreurs_dossier

client = TestClient(app)
DESCRIPTION = "Les livreurs choisissent leurs créneaux. L'application les géolocalise pendant les courses."
PIECE = "Contrat : le prix de chaque course est fixé par la plateforme."


def reponse_cas(_messages):
    """Ce que Mistral pourrait renvoyer pour un cas, avec une citation inventée à éliminer."""
    return {"faits": {
        "liberte_horaires": {"valeur": True, "extrait": "Les livreurs choisissent leurs créneaux", "confiance": 1},
        "geolocalisation_suivi": {"valeur": True, "extrait": "les géolocalise pendant les courses", "confiance": 0.9},
        "tarif_impose": {"valeur": True, "extrait": "le prix de chaque course est fixé par la plateforme", "confiance": 1},
        "sanction_deconnexion": {"valeur": True, "extrait": "désactivés après trois refus", "confiance": 0.9},
        "facteur_imaginaire": {"valeur": True, "extrait": None, "confiance": 1},
    }}


@pytest.fixture
def mistral_simule(monkeypatch):
    monkeypatch.setattr(extraction, "appeler_mistral", reponse_cas)
    monkeypatch.setattr(extraction, "ocr", lambda octets, mime: f"[ocr {mime}] {octets.decode()}")


# ---------------------------------------------------------------- T5

def test_txt_lu_en_utf8():
    assert extraction.lire_document("piece.TXT", "Équipement imposé".encode()) == "Équipement imposé"


@pytest.mark.parametrize("nom, octets, code", [
    ("photo.png", b"x", "format_refuse"),
    ("piece.txt", "é".encode("latin-1"), "encodage"),
    ("vide.txt", b"   ", "document_vide"),
])
def test_documents_refuses(nom, octets, code):
    with pytest.raises(Erreur) as e:
        extraction.lire_document(nom, octets)
    assert (e.value.statut, e.value.code) == (400, code)


@pytest.mark.parametrize("nom, mime", [("arret.pdf", "application/pdf"), ("contrat.docx", "wordprocessingml")])
def test_pdf_et_docx_passent_par_l_ocr(mistral_simule, nom, mime):
    assert mime in extraction.lire_document(nom, b"texte")


# ---------------------------------------------------------------- T7

def test_depot_d_une_piece_du_client(data_vide, mistral_simule):
    r = client.post("/documents", files={"file": ("contrat.txt", PIECE.encode(), "text/plain")}, data={"type": "cas"})

    assert r.status_code == 200
    corps = r.json()
    assert corps["type"] == "cas" and corps["decision_id"] is None
    assert service.lire_texte("documents", corps["document_id"]) == PIECE


def test_depot_d_une_decision_donne_une_fiche_a_relire(data_vide, monkeypatch):
    fiche = {"id": "x", "validee": False}
    monkeypatch.setattr(extraction, "extraire_decision", lambda texte, id_: {**fiche, "id": id_})

    r = client.post("/documents", files={"file": ("arret.txt", b"Attendu que...", "text/plain")}, data={"type": "decision"})

    corps = r.json()
    assert r.status_code == 200 and corps["decision_id"].startswith("dec_")
    assert service.lire("fiches", corps["decision_id"])["validee"] is False


def test_depot_type_ou_format_invalide_donne_400(data_vide, mistral_simule):
    assert client.post("/documents", files={"file": ("a.txt", b"x", "text/plain")}, data={"type": "autre"}).status_code == 400
    assert client.post("/documents", files={"file": ("a.png", b"x", "image/png")}, data={"type": "cas"}).status_code == 400


def test_creer_un_cas_depuis_description_et_pieces(data_vide, mistral_simule):
    doc = client.post("/documents", files={"file": ("contrat.txt", PIECE.encode(), "text/plain")},
                      data={"type": "cas"}).json()["document_id"]

    r = client.post("/cas", json={"description": DESCRIPTION, "ressort": "CA Paris", "document_ids": [doc],
                                  "question": "Risque de requalification ?"})

    cas = r.json()
    assert r.status_code == 200 and cas["id"].startswith("cas_")
    assert cas["facteurs"]["geolocalisation_suivi"] is True
    assert cas["facteurs"]["tarif_impose"] is True                      # extrait trouvé dans la pièce
    assert cas["preuves"]["sanction_deconnexion"]["extrait"] is None     # citation inventée éliminée
    assert "sanction_deconnexion" in cas["a_confirmer"]                 # donc à confirmer
    assert "facteur_imaginaire" not in cas["facteurs"]
    assert set(cas["facteurs"]) == {f["id"] for f in service.grille()["facteurs"]}


def test_le_cas_cree_s_analyse(data_vide, mistral_simule):
    cas = client.post("/cas", json={"description": DESCRIPTION}).json()

    r = client.post(f"/cas/{cas['id']}/analyse")

    assert r.status_code == 200 and erreurs_dossier(r.json()) == []


def test_document_inconnu_donne_404(data_vide, mistral_simule):
    assert client.post("/cas", json={"description": DESCRIPTION, "document_ids": ["doc_absent"]}).status_code == 404


def test_description_vide_donne_400(data_vide, mistral_simule):
    assert client.post("/cas", json={"description": "  "}).status_code == 400


def test_panne_de_mistral_donne_502(data_vide, monkeypatch):
    def panne(_):
        raise Erreur(502, "mistral", "quota dépassé")
    monkeypatch.setattr(extraction, "appeler_mistral", panne)

    r = client.post("/cas", json={"description": DESCRIPTION})

    assert r.status_code == 502 and r.json()["erreur"]["code"] == "mistral"


def test_le_pays_du_cas_pondere_l_analyse(data_vide, mistral_simule):
    cas = client.post("/cas", json={"description": DESCRIPTION, "pays": "Royaume-Uni"}).json()
    assert cas["pays"] == "Royaume-Uni"

    dossier = client.post(f"/cas/{cas['id']}/analyse").json()

    assert dossier["cas"]["pays"] == "Royaume-Uni"
    assert erreurs_dossier(dossier) == []
