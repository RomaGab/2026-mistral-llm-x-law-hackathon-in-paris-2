import pytest

from back import service
from back.service import Erreur


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("DISTINGUO_DATA", str(tmp_path / "data"))
    return tmp_path / "data"


def test_ecrire_puis_lire_redonne_le_meme_objet(data):
    service.ecrire("cas", "cas_1", {"id": "cas_1", "ressort": "CA Paris"})

    assert service.lire("cas", "cas_1") == {"id": "cas_1", "ressort": "CA Paris"}


def test_lister_renvoie_tous_les_objets_tries_par_id(data):
    service.ecrire("fiches", "b", {"id": "b"})
    service.ecrire("fiches", "a", {"id": "a"})

    assert service.lister("fiches") == [{"id": "a"}, {"id": "b"}]


def test_lister_un_genre_vide_renvoie_une_liste_vide(data):
    assert service.lister("fiches") == []


def test_lire_un_id_absent_leve_404(data):
    with pytest.raises(Erreur) as e:
        service.lire("cas", "cas_absent")

    assert e.value.statut == 404


@pytest.mark.parametrize("mauvais_id", ["../x", "CAS", "a/b", "", "x" * 65])
def test_id_invalide_refuse_avant_tout_acces_disque(data, mauvais_id):
    data.mkdir(parents=True)
    (data / "x.json").write_text('{"secret": true}', encoding="utf-8")  # cible de ../x

    with pytest.raises(Erreur) as e:
        service.lire("cas", mauvais_id)

    assert e.value.statut == 400


def test_ecrire_refuse_aussi_un_id_invalide(data):
    with pytest.raises(Erreur) as e:
        service.ecrire("cas", "../x", {})

    assert e.value.statut == 400
    assert not data.exists()
