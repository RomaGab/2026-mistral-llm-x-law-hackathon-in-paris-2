import pytest

from back import exemple


@pytest.fixture
def data_vide(tmp_path, monkeypatch):
    """Données temporaires vides (aucun cas, aucune décision)."""
    monkeypatch.setenv("DISTINGUO_DATA", str(tmp_path / "data"))
    return tmp_path / "data"


@pytest.fixture
def donnees_exemple(tmp_path, monkeypatch):
    """Données temporaires chargées avec le cas et les 5 décisions fictives de contracts/exemples/."""
    dossier = tmp_path / "data"
    monkeypatch.setenv("DISTINGUO_DATA", str(dossier))
    exemple.charger(dossier)
    return dossier
