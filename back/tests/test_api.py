import json
from pathlib import Path

from fastapi.testclient import TestClient

from back.api import app

GRILLE = Path(__file__).resolve().parents[2] / "contracts" / "grille.json"
client = TestClient(app)


def test_sante():
    r = client.get("/sante")

    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_grille_est_celle_du_contrat():
    r = client.get("/grille")

    assert r.status_code == 200
    assert r.json() == json.loads(GRILLE.read_text(encoding="utf-8"))


def test_route_inconnue_renvoie_404_au_format_erreur():
    r = client.get("/inconnue")

    assert r.status_code == 404
    assert set(r.json()["erreur"]) == {"code", "message"}


def test_cors_ouvert_au_front():
    r = client.get("/sante", headers={"Origin": "http://localhost:3000"})

    assert r.headers["access-control-allow-origin"] in ("*", "http://localhost:3000")
