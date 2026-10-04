import json
from pathlib import Path

import pytest

from back import extraction, ingerer, service
from back.service import Erreur
from contracts.valider import erreurs_dossier

RACINE = Path(__file__).resolve().parents[2]
GRILLE = service.grille()["facteurs"]
IDS = [f["id"] for f in GRILLE]
TEXTE = (
    "La société disposait d'un système de géolocalisation permettant le suivi en temps réel "
    "par la société de la position du coursier. Le coursier pouvait librement choisir ses horaires."
)


def decision_brute(**changements):
    """Réponse Mistral plausible pour une décision ; chaque test change ce qu'il éprouve."""
    brut = {
        "intitule": "Cass. soc., 28 nov. 2018, n° 17-20.079",
        "juridiction": "Cour de cassation, chambre sociale",
        "formation": "cass",
        "ressort": None,
        "date": "2018-11-28",
        "numero": "17-20.079",
        "publication": "B",
        "dispositif": "cassation",
        "issue": True,
        "textes": ["C. trav., art. L. 8221-6"],
        "faits": {
            "geolocalisation_suivi": {
                "valeur": True,
                "extrait": "système de géolocalisation permettant le suivi en temps réel",
                "confiance": 0.9,
            },
            "liberte_horaires": {"valeur": True, "extrait": "pouvait librement choisir ses horaires", "confiance": 0.8},
        },
        "determinants": ["geolocalisation_suivi"],
    }
    brut.update(changements)
    return brut


# ---- normaliser_faits : la frontière de confiance


def test_valeur_non_booleenne_devient_null():
    brut = {"geolocalisation_suivi": {"valeur": "oui"}, "tarif_impose": {"valeur": 1}, "liberte_horaires": {"valeur": "true"}}

    facteurs, _ = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert facteurs["geolocalisation_suivi"] is None
    assert facteurs["tarif_impose"] is None
    assert facteurs["liberte_horaires"] is None


def test_facteur_manquant_vaut_null_et_tous_les_facteurs_sont_presents():
    facteurs, _ = extraction.normaliser_faits({}, TEXTE, GRILLE)

    assert list(facteurs) == IDS
    assert set(facteurs.values()) == {None}


def test_cle_hors_grille_ignoree():
    facteurs, preuves = extraction.normaliser_faits({"facteur_invente": {"valeur": True, "extrait": "x"}}, TEXTE, GRILLE)

    assert "facteur_invente" not in facteurs
    assert "facteur_invente" not in preuves


def test_sortie_mal_formee_ne_plante_pas():
    facteurs, preuves = extraction.normaliser_faits(["pas", "un", "objet"], TEXTE, GRILLE)
    assert set(facteurs.values()) == {None} and preuves == {}

    facteurs, preuves = extraction.normaliser_faits({"geolocalisation_suivi": "oui"}, TEXTE, GRILLE)
    assert facteurs["geolocalisation_suivi"] is None and preuves == {}


def test_extrait_retrouve_malgre_espaces_et_apostrophes_typographiques():
    texte = "Le livreur   ne pouvait\nrefuser l’offre"
    brut = {"service_organise": {"valeur": True, "extrait": "ne pouvait refuser l'offre", "confiance": 0.9}}

    _, preuves = extraction.normaliser_faits(brut, texte, GRILLE)

    assert preuves["service_organise"] == {"extrait": "ne pouvait refuser l'offre", "confiance": 0.9, "source": "extraction"}


def test_citation_entre_guillemets_suivie_d_un_commentaire_nettoyee():
    brut = {"geolocalisation_suivi": {
        "valeur": True, "confiance": 0.9,
        "extrait": '"système de géolocalisation permettant le suivi en temps réel" (sous-entendu : contrôle)'}}

    _, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert preuves["geolocalisation_suivi"]["extrait"] == "système de géolocalisation permettant le suivi en temps réel"
    assert preuves["geolocalisation_suivi"]["confiance"] == 0.9


def test_citation_avec_ellipses_acceptee_si_chaque_fragment_est_dans_le_texte():
    brut = {"geolocalisation_suivi": {"valeur": True, "confiance": 0.9,
                                      "extrait": "La société disposait [...] de la position du coursier"}}

    _, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert preuves["geolocalisation_suivi"]["extrait"] == "La société disposait [...] de la position du coursier"


def test_citation_avec_ellipses_refusee_si_un_fragment_est_invente():
    brut = {"geolocalisation_suivi": {"valeur": True, "confiance": 0.9,
                                      "extrait": "La société disposait [...] d'un algorithme de tarification"}}

    _, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert preuves["geolocalisation_suivi"]["extrait"] is None


def test_casse_et_type_de_guillemets_ignores():
    texte = 'Un système de "strikes" était mis en place.'
    brut = {"penalites_bonus": {"valeur": True, "confiance": 0.9, "extrait": "un système de 'strikes' était mis en place"}}

    _, preuves = extraction.normaliser_faits(brut, texte, GRILLE)

    assert preuves["penalites_bonus"]["extrait"] == "un système de 'strikes' était mis en place"


def test_citation_qui_enjambe_des_lignes_a_puces_acceptee():
    texte = "ELEMENTS :\n- Un système de strikes était mis en place.\n- L'accumulation entraînait la désactivation."
    brut = {"sanction_deconnexion": {"valeur": True, "confiance": 1,
                                     "extrait": "Un système de strikes était mis en place. L'accumulation entraînait la désactivation."}}

    _, preuves = extraction.normaliser_faits(brut, texte, GRILLE)

    assert preuves["sanction_deconnexion"]["extrait"] is not None


def test_extrait_introuvable_supprime_et_confiance_plafonnee():
    brut = {"sanction_deconnexion": {"valeur": True, "extrait": "la plateforme désactive les comptes", "confiance": 0.95}}

    facteurs, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert facteurs["sanction_deconnexion"] is True
    assert preuves["sanction_deconnexion"]["extrait"] is None
    assert preuves["sanction_deconnexion"]["confiance"] <= 0.5


def test_fait_sans_extrait_finit_sous_le_seuil_de_confirmation():
    _, preuves = extraction.normaliser_faits({"tarif_impose": {"valeur": False, "confiance": 1.0}}, TEXTE, GRILLE)

    assert preuves["tarif_impose"]["confiance"] < 0.6


@pytest.mark.parametrize("brute, attendue", [(1.7, 1.0), (-0.2, 0.0), (0.42, 0.42)])
def test_confiance_ramenee_dans_0_1(brute, attendue):
    brut = {"geolocalisation_suivi": {"valeur": True, "extrait": "position du coursier", "confiance": brute}}

    _, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert preuves["geolocalisation_suivi"]["confiance"] == attendue


@pytest.mark.parametrize("brute", ["haute", True, None, [0.9]])
def test_confiance_non_numerique_vaut_0(brute):
    brut = {"geolocalisation_suivi": {"valeur": True, "extrait": "position du coursier", "confiance": brute}}

    _, preuves = extraction.normaliser_faits(brut, TEXTE, GRILLE)

    assert preuves["geolocalisation_suivi"]["confiance"] == 0.0


def test_pas_de_preuve_pour_un_fait_inconnu_sans_extrait():
    _, preuves = extraction.normaliser_faits({"tarif_impose": {"valeur": None, "confiance": 0.3}}, TEXTE, GRILLE)

    assert preuves == {}


# ---- normaliser_decision


def test_decision_normalisee_jamais_validee_ni_remise_en_cause():
    brut = decision_brute(validee=True, remise_en_cause="revirement", url="http://x")

    fiche = extraction.normaliser_decision(brut, TEXTE, GRILLE, "dec-1")

    assert fiche["id"] == "dec-1"
    assert fiche["validee"] is False
    assert fiche["remise_en_cause"] is None
    assert fiche["url"] is None


def test_determinants_null_hors_grille_ou_en_double_retires():
    brut = decision_brute(determinants=["geolocalisation_suivi", "sanction_deconnexion", "invente", "geolocalisation_suivi", 3])

    fiche = extraction.normaliser_decision(brut, TEXTE, GRILLE, "dec-1")

    assert fiche["determinants"] == ["geolocalisation_suivi"]  # sanction_deconnexion vaut null


def test_determinants_donnes_sous_forme_d_objets_acceptes():
    brut = decision_brute(determinants=[{"identifiant": "geolocalisation_suivi", "extrait": "..."}, {"id": "liberte_horaires"}])

    fiche = extraction.normaliser_decision(brut, TEXTE, GRILLE, "dec-1")

    assert fiche["determinants"] == ["geolocalisation_suivi", "liberte_horaires"]


def test_determinant_sans_extrait_verifie_retire():
    faits = decision_brute()["faits"] | {"tarif_impose": {"valeur": True, "extrait": "le prix est fixé par la plateforme"}}
    brut = decision_brute(faits=faits, determinants=["geolocalisation_suivi", "tarif_impose"])

    fiche = extraction.normaliser_decision(brut, TEXTE, GRILLE, "dec-1")

    assert fiche["facteurs"]["tarif_impose"] is True  # le fait reste, à confirmer par le juriste
    assert fiche["determinants"] == ["geolocalisation_suivi"]  # mais pas comme motif décisif sans citation


@pytest.mark.parametrize(
    "champ, valeur",
    [("issue", "salariat"), ("issue", None), ("formation", "chambre sociale"), ("date", "28/11/2018"),
     ("publication", "publié"), ("intitule", ""), ("juridiction", None)],
)
def test_metadonnee_obligatoire_invalide_rejetee(champ, valeur):
    with pytest.raises(Erreur) as e:
        extraction.normaliser_decision(decision_brute(**{champ: valeur}), TEXTE, GRILLE, "dec-1")

    assert e.value.statut == 502
    assert champ in e.value.message


def test_metadonnees_facultatives_invalides_mises_a_null():
    brut = decision_brute(dispositif="annulation", ressort=12, numero=["17-20.079"], textes=["art. L. 1221-1", 4])

    fiche = extraction.normaliser_decision(brut, TEXTE, GRILLE, "dec-1")

    assert fiche["dispositif"] is None
    assert fiche["ressort"] is None
    assert fiche["numero"] is None
    assert fiche["textes"] == ["art. L. 1221-1"]


def test_ressort_toujours_null_pour_la_cour_de_cassation():
    fiche = extraction.normaliser_decision(decision_brute(ressort="CA Paris"), TEXTE, GRILLE, "dec-1")

    assert fiche["ressort"] is None  # portée nationale : sinon le critère géographique pénalise l'arrêt


def test_date_impossible_rejetee():
    with pytest.raises(Erreur):
        extraction.normaliser_decision(decision_brute(date="2018-13-45"), TEXTE, GRILLE, "dec-1")


def test_fiche_acceptee_par_le_validateur_une_fois_validee():
    fiche = extraction.normaliser_decision(decision_brute(), TEXTE, GRILLE, "dec-1")
    dossier = json.loads((RACINE / "contracts" / "exemples" / "dossier_entree.json").read_text(encoding="utf-8"))
    dossier["decisions"] = [dict(fiche, validee=True)]

    assert erreurs_dossier(dossier) == []


# ---- appeler_mistral : seul point réseau


class FauxClient:
    def __init__(self, contenu=None, exception=None):
        self.contenu, self.exception, self.appels = contenu, exception, []
        self.chat = self

    def complete(self, **kwargs):
        self.appels.append(kwargs)
        if self.exception:
            raise self.exception
        message = type("M", (), {"content": self.contenu})
        return type("R", (), {"choices": [type("C", (), {"message": message})]})


def test_appeler_mistral_demande_du_json_deterministe(monkeypatch):
    client = FauxClient(contenu='{"ok": true}')
    monkeypatch.setattr(extraction, "_client", lambda: client)

    assert extraction.appeler_mistral([{"role": "user", "content": "x"}]) == {"ok": True}
    assert client.appels[0]["temperature"] == 0
    assert client.appels[0]["random_seed"] == 0
    assert client.appels[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("client", [FauxClient(exception=RuntimeError("timeout")), FauxClient(contenu="pas du json")])
def test_echec_de_mistral_donne_502(monkeypatch, client):
    monkeypatch.setattr(extraction, "_client", lambda: client)

    with pytest.raises(Erreur) as e:
        extraction.appeler_mistral([{"role": "user", "content": "x"}])

    assert e.value.statut == 502


def test_extraire_decision_transmet_les_notes_et_normalise(monkeypatch):
    messages_recus = []
    monkeypatch.setattr(extraction, "appeler_mistral", lambda m: messages_recus.append(m) or decision_brute(validee=True))

    fiche = extraction.extraire_decision(TEXTE, "dec-1", notes={"fait_pivot_censure": "géolocalisation ET sanction"})

    assert fiche["validee"] is False
    contenu = json.dumps(messages_recus[0], ensure_ascii=False)
    assert "géolocalisation ET sanction" in contenu
    assert TEXTE in contenu


# ---- ingerer : ingestion en lot du dataset Legora


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    monkeypatch.setenv("DISTINGUO_DATA", str(tmp_path / "data"))
    racine = tmp_path / "sources"
    (racine / "01_France").mkdir(parents=True)
    (racine / "02_UK").mkdir()
    (racine / "01_France" / "2018-11-28_Cass_Soc_17-20.079_TakeEatEasy.txt").write_text(TEXTE, encoding="utf-8")
    (racine / "01_France" / "2020-03-04_Cass_Soc_19-13.316_Uber.txt").write_text(TEXTE, encoding="utf-8")
    (racine / "02_UK" / "2021-02-19_UKSC5_Uber_BV_v_Aslam.txt").write_text("judgment", encoding="utf-8")
    (racine / "README.txt").write_text("contenu du dossier", encoding="utf-8")
    tableau = [
        {"juridiction_pays": "France - Cour de cassation (Chambre sociale)", "fait_pivot_censure": "géoloc ET sanction",
         "fichier_source_brute": "01_France/2018-11-28_Cass_Soc_17-20.079_TakeEatEasy.txt"},
        {"juridiction_pays": "Royaume-Uni - UK Supreme Court",
         "fichier_source_brute": "02_UK/2021-02-19_UKSC5_Uber_BV_v_Aslam.txt"},
    ]
    (racine / "00_Tableau_synthese_structure.json").write_text(json.dumps(tableau), encoding="utf-8")
    appels = []
    monkeypatch.setattr(extraction, "appeler_mistral", lambda m: appels.append(m) or decision_brute())
    return racine, tmp_path / "data", appels


def test_ingerer_extrait_les_decisions_francaises_et_saute_le_reste(dataset):
    racine, data, appels = dataset

    rapport = ingerer.ingerer(racine)

    assert sorted(p.name for p in (data / "fiches").iterdir()) == [
        "2018-11-28_cass_soc_17-20-079_takeeateasy.json",
        "2020-03-04_cass_soc_19-13-316_uber.json",
    ]
    assert (data / "decisions" / "2018-11-28_cass_soc_17-20-079_takeeateasy.txt").read_text(encoding="utf-8") == TEXTE
    assert len(appels) == 2
    assert "géoloc ET sanction" in json.dumps(appels[0], ensure_ascii=False)  # notes du tableau transmises
    assert any("UKSC5" in ligne and "étrang" in ligne for ligne in rapport)
    assert all("README" not in ligne or "ignoré" in ligne for ligne in rapport)


def test_ingerer_saute_les_fiches_existantes_et_respecte_la_limite(dataset):
    racine, _data, appels = dataset

    ingerer.ingerer(racine, limite=1)
    assert len(appels) == 1
    ingerer.ingerer(racine, limite=1)
    assert len(appels) == 2
    ingerer.ingerer(racine)
    assert len(appels) == 2  # tout est déjà extrait : aucun nouvel appel


def test_ingerer_continue_apres_un_echec(dataset, monkeypatch):
    racine, data, _ = dataset
    reponses = iter([decision_brute(issue="?"), decision_brute()])
    monkeypatch.setattr(extraction, "appeler_mistral", lambda m: next(reponses))

    rapport = ingerer.ingerer(racine)

    assert len(list((data / "fiches").iterdir())) == 1
    assert any("échec" in ligne for ligne in rapport)


def test_slug_compatible_avec_les_ids_du_service():
    slug = ingerer.slug("2023-11-21_UKSC43_IWGB_v_CAC_Deliveroo_extrait_pages1-10 (copie).txt")

    assert service.ID_VALIDE.match(slug)
    assert slug == "2023-11-21_uksc43_iwgb_v_cac_deliveroo_extrait_pages1-10-copie"
    assert ingerer.slug("Décision été.txt") == "decision-ete"
