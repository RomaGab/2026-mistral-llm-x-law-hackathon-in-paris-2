"""T5 (lecture TXT / PDF / DOCX) et T7 (dépôt de documents, création d'un cas). Mistral est simulé."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from back import extraction, service
from back.api import app
from back.service import Erreur
from contracts.valider import erreurs_dossier

client = TestClient(app)
DESCRIPTION = "Les livreurs choisissent leurs créneaux. L'application les géolocalise pendant les courses."
PIECE = "Contrat : le prix de chaque course est fixé par la plateforme."


def reponse_cas(_messages, *_):
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


def pdf_texte(texte: str) -> bytes:
    """Un PDF « texte » minimal (une page, Helvetica), sans dépendance."""
    flux = f"BT /F1 12 Tf 72 720 Td ({texte}) Tj ET".encode("latin-1")
    objets = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
              b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
              b"<< /Length %d >>\nstream\n" % len(flux) + flux + b"\nendstream",
              b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    sortie, positions = b"%PDF-1.4\n", []
    for i, objet in enumerate(objets, 1):
        positions.append(len(sortie))
        sortie += b"%d 0 obj\n" % i + objet + b"\nendobj\n"
    xref = len(sortie)
    sortie += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1) + b"".join(b"%010d 00000 n \n" % x for x in positions)
    return sortie + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)


def docx(*paragraphes: str) -> bytes:
    corps = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphes)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
           f'wordprocessingml/2006/main"><w:body>{corps}</w:body></w:document>')
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return tampon.getvalue()


def test_pdf_texte_lu_localement_sans_ocr(monkeypatch):
    def interdit(*_):
        raise AssertionError("l'OCR ne doit pas être appelé pour un PDF texte")
    monkeypatch.setattr(extraction, "ocr", interdit)
    phrase = "Le prix de chaque course est fixe par la plateforme. " * 5

    assert "Le prix de chaque course" in extraction.lire_document("contrat.pdf", pdf_texte(phrase))


def test_pdf_sans_texte_passe_par_l_ocr(mistral_simule):
    assert "application/pdf" in extraction.lire_document("scan.pdf", b"pas un vrai pdf")


def test_docx_lu_localement(monkeypatch):
    monkeypatch.setattr(extraction, "ocr", lambda *_: pytest.fail("pas d'OCR pour un DOCX"))

    texte = extraction.lire_document("cgu.docx", docx("Article 4.2", "Le coursier peut travailler pour des concurrents."))

    assert texte == "Article 4.2\nLe coursier peut travailler pour des concurrents."


def test_docx_illisible_donne_400():
    with pytest.raises(Erreur) as e:
        extraction.lire_document("cgu.docx", b"pas un zip")
    assert (e.value.statut, e.value.code) == (400, "docx_illisible")


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
    def panne(*_):
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
