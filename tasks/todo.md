# Tâches : Back Distinguo

Spec : [SPEC-back.md](../SPEC-back.md) · Plan : [plan.md](plan.md).
Vérification commune à chaque tâche : `uv run pytest` vert, et aucun dossier produit qui soit refusé par `valider.py`.

## Phase 1 : J1, socle, vraie décision, analyse

- [ ] **T1. Socle : l'API répond et sert la grille** · S · dépend de : rien
  - Faire : `pyproject.toml` racine (stack du spec ; `[tool.pytest.ini_options] pythonpath = ["."]`) ; dans `service.py`, `lire` / `ecrire` / `lister`, le contrôle des ids et `Erreur` ; dans `api.py`, `/sante`, `/grille`, le CORS et les gestionnaires d'erreurs (`Erreur` → son statut, `RequestValidationError` → 400, tout au format `erreur`) ; dans `.gitignore`, `data/cas/`, `data/documents/` et `.DS_Store` (le dataset en contient).
  - Accepté si :
    - `GET /sante` renvoie `{"ok": true}` et `GET /grille` renvoie le contenu de `contracts/grille.json`.
    - `lire("cas", "../x")` lève un 400 sans accéder au disque.
    - Un id inconnu donne un 404 au format `{"erreur": {...}}`.
  - Vérif : `uv run pytest back/tests/test_api.py` ; `uv run uvicorn back.api:app --port 8000` puis `curl localhost:8000/grille`.
  - Fichiers : `pyproject.toml`, `.gitignore`, `back/__init__.py`, `back/service.py`, `back/api.py`, `back/tests/test_api.py`

- [ ] **T2. Une vraie décision devient une fiche** · M · dépend de : T1 · **risque n°1**
  - Faire : dans `extraction.py`, `appeler_mistral` (seul point réseau, JSON mode, `temperature=0`), le prompt de décision (18 questions de la grille + métadonnées du schéma `decision`), `normaliser_faits` et `normaliser_decision` ; dans `ingerer.py`, pour chaque `.txt` du dossier (sous-dossiers compris) : l'entrée du tableau de synthèse est passée en notes, les entrées hors France sont sautées, le texte va dans `data/decisions/`, la fiche `validee: false` dans `data/fiches/`, les fiches existantes sont sautées, option `--limite N`.
  - Accepté si :
    - Chaque règle de normalisation du spec a son test, sans réseau.
    - Sur *Take Eat Easy* 2018 (3 Ko, le moins cher à tester), puis sur *Uber* 2020 (95 Ko, le plus long), la fiche est produite. Relue à la main : l'issue au fond est juste et les déterminants recoupent le tableau de synthèse.
    - Les 5 sources étrangères sont sautées, avec un message.
    - Une fois passée à `validee: true`, la fiche est acceptée par `valider.py` dans un dossier (vérifié en T3).
  - Vérif : `uv run pytest back/tests/test_extraction.py` ; `uv run python -m back.ingerer dataset-legora/sources_jurisprudence_plateformes/sources_brutes --limite 1`.
  - Fichiers : `back/extraction.py`, `back/ingerer.py`, `back/tests/test_extraction.py`, `data/decisions/`, `data/fiches/`

- [ ] **T3. Analyser un cas, simulation comprise** · M · dépend de : T1
  - Faire : `service.analyser(cas_id, facteurs=None)`, selon le spec (construction, validation avant et après, faux calculateur si `calculateur` est absent) ; `GET /cas/{id}` et `POST /cas/{id}/analyse` ; un `conftest.py` qui charge le cas et les décisions de `dossier_entree.json` dans un `DISTINGUO_DATA` temporaire.
  - Accepté si :
    - Le dossier passé à `completer()` est accepté par `erreurs_dossier`, et une décision `validee: false` n'y entre pas.
    - Avec `{"facteurs": {...}}`, `meta.simulation` vaut `true` et le fichier du cas reste inchangé.
    - Un facteur hors grille ou une valeur `"oui"` donne un 400 ; un dossier refusé donne un 422 qui liste les problèmes.
  - Vérif : `uv run pytest` ; à la main, la fiche validée de T2, copiée dans les données, donne un dossier valide.
  - Fichiers : `back/service.py`, `back/api.py`, `back/tests/conftest.py`, `back/tests/test_service.py`, `back/tests/test_api.py`

- [ ] **T4. Corriger les faits d'un cas** · XS · dépend de : T3
  - Faire : `PATCH /cas/{id}` ; une preuve `source: "utilisateur"`, `confiance: 1.0` pour chaque fait modifié ; `a_confirmer` recalculé à chaque écriture du cas.
  - Accepté si :
    - `{"facteurs": {"sanction_deconnexion": true}}` enregistre la valeur, et le facteur sort de `a_confirmer`.
    - Une valeur invalide donne un 400, et rien n'est écrit.
  - Vérif : `uv run pytest back/tests/test_api.py`.
  - Fichiers : `back/service.py`, `back/api.py`, `back/tests/test_api.py`

### Checkpoint J1
- [ ] `uv run pytest` est vert.
- [ ] Une vraie décision extraite, puis validée, donne un dossier valide.
- [ ] Sur le cas exemple : `GET /cas` → `PATCH` → `/analyse` → simulation, tout passe.
- [ ] Commit et push ; pyproject annoncé à Mathis ; l'URL de l'API donnée au front.

## Phase 2 : parcours du front

- [ ] **T5. Lire les PDF et les DOCX** · S · dépend de : T2
  - Faire : `lire_document(nom, octets)`. Un TXT est lu en UTF-8, un PDF ou un DOCX passe par `mistral-ocr-latest` (data URL base64), toute autre extension donne un 400. `ingerer.py` accepte aussi les `.pdf` et les `.docx`.
  - Accepté si :
    - Un vrai PDF de décision donne un texte exploitable par T2.
    - Pour les DOCX, on vérifie **d'abord** que l'OCR les lit ; sinon on les refuse (400) et on le note dans le spec.
  - Vérif : `uv run pytest back/tests/test_extraction.py` (extension refusée, TXT lu) ; à la main, `ingerer` sur un PDF.
  - Fichiers : `back/extraction.py`, `back/ingerer.py`, `back/tests/test_extraction.py`

- [ ] **T6. Relecture par le juriste** · S · dépend de : T2
  - Faire : `GET /decisions`, `GET /decisions/{id}` et `PATCH /decisions/{id}` (fusion, puis contrôle par `valider.py` dans un dossier minimal).
  - Accepté si :
    - `PATCH {"validee": true}` sur une fiche correcte la fait entrer dans le prochain dossier.
    - Si le patch rend la fiche invalide (déterminant `null`, facteur hors grille), on renvoie un 400 qui liste les problèmes, et le fichier n'est pas modifié.
  - Vérif : `uv run pytest back/tests/test_api.py`.
  - Fichiers : `back/service.py`, `back/api.py`, `back/tests/test_api.py`

- [ ] **T7. Créer un cas depuis une description et des documents** · M · dépend de : T2, T4
  - Faire : `POST /documents` (`type=cas` : le texte va dans `data/documents/` ; `type=decision` : extraction, puis fiche `validee: false`) ; `extraire_cas` dans `extraction.py` ; `POST /cas` (description + textes des documents → faits, preuves, `a_confirmer`).
  - Accepté si :
    - Mistral simulé : le cas créé contient tous les facteurs, et ses preuves passent la normalisation.
    - Un `document_ids` inconnu donne un 404 ; un échec de Mistral donne un 502.
    - Clé réelle : la description du cas exemple donne `geolocalisation_suivi: true`, et `sanction_deconnexion` figure dans `a_confirmer`.
  - Vérif : `uv run pytest` ; à la main, `curl -F file=@cas.txt -F type=cas localhost:8000/documents` puis `POST /cas`.
  - Fichiers : `back/extraction.py`, `back/service.py`, `back/api.py`, `back/tests/test_api.py`

### Checkpoint : parcours du front
- [ ] Toutes les routes du §7 répondent avec le faux calculateur.
- [ ] Parcours à la main : dépôt → cas → correction → analyse → simulation.
- [ ] Commit et push ; prévenir le front.

## Phase 3 : MCP (obligatoire en démo)

- [ ] **T8. Serveur MCP local** · S · dépend de : T3, T7
  - Faire : `serveur_mcp.py` avec `distinguo_analyser`, `distinguo_simuler` et `distinguo_expliquer_score`, qui appellent `service.py`. Un résumé avec les libellés de la grille, pas le dossier brut. Transport streamable HTTP sur le port 8001.
  - Accepté si :
    - Dans l'Inspector, `distinguo_analyser` sur la description du cas exemple renvoie `cas_id`, P, l'issue en libellé, les pivots et les faits à confirmer.
    - `distinguo_simuler` avec `sanction_deconnexion: true` montre un P différent, et rien n'est écrit.
    - `distinguo_expliquer_score` donne le détail par facteur et par décision.
  - Vérif : `uv run python -m back.serveur_mcp` puis `npx @modelcontextprotocol/inspector`.
  - Fichiers : `back/serveur_mcp.py`

- [ ] **T9. Le MCP depuis le client de démo** · S · dépend de : T8 · **bloqué par la question ouverte 2**
  - Faire : brancher le client choisi (Le Chat : tunnel `cloudflared`, puis déclarer le connecteur ; Claude Desktop : configuration locale), et noter la procédure dans le README de démo ou dans le spec.
  - Accepté si :
    - Depuis le client, une question en langage naturel sur le cas Uber déclenche `distinguo_analyser`, et l'agent cite P et le pivot.
    - Une relance (« et si la plateforme sanctionnait les refus ? ») déclenche `distinguo_simuler`.
  - Vérif : à la main, depuis le client ; capture d'écran en secours.
  - Fichiers : la procédure de démo uniquement

### Checkpoint : MCP
- [ ] Les trois outils marchent depuis le client de démo.
- [ ] Le tunnel est fermé après le test.

## Phase 4 : J2/J3, vrai calculateur, vrai corpus, démo

- [ ] **T10. Brancher le vrai calculateur** · S · dépend de : T3 · **passe devant dès que Mathis livre**
  - Faire : ajouter les dépendances du calculateur au `pyproject.toml`, `uv sync`, et vérifier que l'avertissement « faux calculateur » a disparu.
  - Accepté si :
    - `/analyse` renvoie un dossier complété par le vrai `completer()`, accepté par `valider.py`.
    - La réponse arrive en moins d'1 s avec ~20 décisions.
  - Vérif : `uv run pytest` ; `time curl -X POST localhost:8000/cas/<id>/analyse`.
  - Fichiers : `pyproject.toml`, `uv.lock`

- [ ] **T11. Corpus réel, équilibré à la main** · S · dépend de : T2, T5, T6
  - Faire : `ingerer` sur les 6 arrêts français du dataset Legora ; ajouter à la main des arrêts de cour d'appel, en priorité ceux qui retiennent l'indépendance (fichiers déposés dans le dataset ou via `POST /documents`) ; relecture et validation par le juriste. L'arrêt Transopco 2025 (chambre commerciale, concurrence déloyale) reste à arbitrer par le juriste : son issue sur la requalification n'est qu'incidente.
  - Accepté si :
    - Environ 15 décisions validées, dont au moins 5 pour l'indépendance, avec des cours d'appel en plus des arrêts de cassation.
    - Aucune fiche `[FICTIF]` dans `data/fiches/`.
  - Vérif : `ls data/fiches | wc -l` ; `grep -L '"validee": true' data/fiches/*.json` liste les fiches restant à relire.
  - Fichiers : `back/ingerer.py`, `data/fiches/`, `data/decisions/`

- [ ] **T12. Répétition de la démo** · XS · dépend de : tout
  - Faire : jouer le scénario deux fois, une fois par le front et une fois par le MCP, puis enregistrer la vidéo de secours **avant le gel de 17h**.
  - Accepté si :
    - Dépôt du cas Uber → `sanction_deconnexion` à confirmer → analyse → case cochée → bascule, sans erreur et avec `/analyse` en moins d'1 s.
  - Vérif : à la main ; vidéo enregistrée.
  - Fichiers : aucun

### Checkpoint final
- [ ] Les critères de réussite du spec (J1, J2, MCP, J3) sont tous cochés.
- [ ] `uv run pytest` est vert ; aucun secret ni aucune donnée client dans git.
- [ ] Merge sur `main` et push.
