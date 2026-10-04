# Spec : Back Distinguo

*Brique « Back » de [distinguo-architecture-contrats.md](distinguo-architecture-contrats.md) (§1). Ce spec ne répète pas le contrat : il fixe ce que le contrat laisse ouvert.*
*Le dossier `contracts/` fait foi en cas de désaccord avec ce document.*

## Objectif

Le back transforme des textes juridiques en **dossiers valides** et les fait compléter par le calculateur. Il a deux clients :

- **le front**, via l'API REST du contrat (§7) ;
- **un agent Mistral dans Le Chat** (prompt « Agent Stratégique Pivot »), via un serveur MCP montré **en démo**. C'est le produit vendu (cf. [idee.md](idee.md), partie 2).

Il fait quatre choses, et rien d'autre :

1. **Lire** un document (TXT tel quel ; PDF/DOCX via Mistral OCR).
2. **Extraire** les faits d'un texte (cas ou décision) avec Mistral, en gardant pour chaque fait l'extrait qui le justifie et un niveau de confiance.
3. **Stocker** décisions, cas et documents en fichiers JSON.
4. **Construire** le dossier, le valider, appeler `completer()`, valider le retour, le renvoyer.

Le back ne pondère rien et ne calcule aucune probabilité : c'est le travail du calculateur.

## Stack

| Élément | Choix |
|---|---|
| Langage | Python ≥ 3.12, géré par `uv` |
| API | FastAPI + uvicorn (`python-multipart` pour les dépôts de fichiers) |
| LLM | SDK `mistralai` : `mistral-large-latest` pour l'extraction (JSON mode, `temperature=0`), `mistral-ocr-latest` pour PDF/DOCX |
| MCP | SDK `mcp` (`FastMCP`), transport streamable HTTP |
| Validation | `jsonschema` via `contracts/valider.py` (déjà écrit) |
| Tests | `pytest` (+ `httpx` pour le `TestClient`) |

Ces dépendances suffisent. Pas d'ORM, pas de base de données, pas de Pydantic pour recopier le schéma du dossier : le schéma et `valider.py` font foi. Pydantic ne sert qu'aux corps de requête.

Configuration dans `.env` (déjà ignoré par git) :

| Variable | Défaut | Rôle |
|---|---|---|
| `MISTRAL_API_KEY` | — (obligatoire) | Clé API |
| `MISTRAL_MODELE` | `mistral-large-latest` | Modèle d'extraction |
| `DISTINGUO_DATA` | `data` | Racine du stockage. Les tests la pointent vers un dossier temporaire. |

## Commandes

Toutes les commandes se lancent **depuis la racine du dépôt**, pour que `back`, `contracts` et `calculateur` soient importables.

```bash
uv sync                                              # installe les dépendances (pyproject.toml racine)
uv run uvicorn back.api:app --reload --port 8000     # API pour le front
uv run python -m back.serveur_mcp                    # serveur MCP → http://localhost:8001/mcp
uv run python -m back.ingerer dataset-legora/sources_jurisprudence_plateformes/sources_brutes             # → data/fiches/ (validee: false)
uv run python -m back.ingerer dataset-legora/sources_jurisprudence_plateformes/sources_brutes --limite 1  # une seule, pour tester
uv run pytest                                        # tests (sans réseau)
uv run python contracts/valider.py dossier.json      # valide un dossier sauvegardé
uvx ruff check back/ && uvx ruff format back/        # lint + format, sans dépendance ajoutée
npx @modelcontextprotocol/inspector                  # tester le MCP à la main
cloudflared tunnel --url http://localhost:8001       # URL publique pour Le Chat, pendant la démo uniquement
```

## Structure

```
pyproject.toml          ← racine, partagé avec le calculateur (à confirmer avec Mathis)
back/
├── api.py              ← FastAPI : routes du §7, CORS, format d'erreur unique
├── serveur_mcp.py      ← outils MCP, appellent service.py directement (pas d'appel HTTP)
├── prompt_agent.md     ← instructions de l'agent Mistral, alignées sur les noms d'outils et de champs
├── service.py          ← stockage JSON + cas d'usage partagés par l'API et le MCP
│                          (deposer_document, creer_cas, modifier_cas, analyser, lister/modifier décisions)
├── extraction.py       ← Mistral : OCR, texte → faits (cas / décision), normalisation des sorties
├── ingerer.py          ← CLI d'ingestion en lot (dataset Legora)
└── tests/
data/
├── decisions/<id>.txt  ← textes bruts des décisions (après OCR)        → versionné
├── fiches/<id>.json    ← décisions extraites, au format `decision`     → versionné (relu par le juriste)
├── cas/<id>.json       ← cas clients                                   → ignoré par git
└── documents/<id>.txt  ← textes des documents d'un cas                 → ignoré par git
```

### Comportements que le contrat ne précise pas

**Lecture des documents.** Un TXT est lu en UTF-8. Un PDF ou un DOCX passe par `mistral-ocr-latest` (en data URL base64), et on garde le markdown produit. Toute autre extension est refusée (400).

**Extraction (cas et décision).** Un seul appel Mistral pour toute la grille, avec les 18 `question` de `grille.json`, et en réponse un JSON `{facteur_id: {valeur, extrait, confiance}}`. Pour une décision, l'appel extrait aussi les métadonnées du schéma `decision` (intitule, juridiction, formation, ressort, date, numero, publication, dispositif, issue **au fond**, textes, determinants).

**Normalisation (frontière de confiance : on ne croit jamais le LLM).** Elle se fait dans `extraction.py` avant tout stockage :
- toute valeur qui n'est pas exactement `true` ou `false` devient `null` ; un facteur manquant vaut `null` ; une clé hors grille est ignorée ;
- `confiance` est ramenée dans [0, 1] ; si elle n'est pas un nombre, elle vaut 0 ;
- un extrait qu'on ne retrouve pas tel quel dans le texte source (espaces normalisés) est mis à `null`. Un fait **sans extrait** a une confiance d'au plus 0,5, donc il finit dans `a_confirmer` ;
- un déterminant qui vaut `null`, ou qui est hors grille, est retiré de `determinants` ;
- une décision extraite a toujours `validee: false` et `remise_en_cause: null`. Seul le juriste change ces champs.

**`a_confirmer`** contient les facteurs qui valent `null` ou dont la confiance est < 0,6, dans l'ordre de la grille. Il est recalculé à chaque écriture du cas.

**Ingestion (`ingerer.py`).** On parcourt les fichiers `.txt`, `.pdf` et `.docx` du dossier, sous-dossiers compris. Si `00_Tableau_synthese_structure.json` est présent (format Legora), l'entrée qui pointe vers le fichier (`fichier_source_brute`) est passée **telle quelle** à Mistral, comme notes d'aide à l'extraction (date, référence, statut jugé, faits déterminants, fait pivot). Ces notes viennent elles-mêmes d'un outil de recherche : ce sont des indices, pas des vérités, et la fiche passe quand même par la relecture du juriste. Une entrée dont `juridiction_pays` ne commence pas par « France » est **sautée** (avec un message) : le schéma `decision` ne sait pas représenter une juridiction étrangère, qui n'a de toute façon pas d'autorité en droit français. Un fichier absent du tableau (ajout manuel) est extrait sans notes.

**Identifiants.** Format `^[a-z0-9_-]{1,64}$`, vérifié **avant tout accès disque** (pas de traversée de chemin). Un cas s'appelle `cas_<8 hex>`, un document `doc_<8 hex>`. Une décision déposée s'appelle `dec_<8 hex>` ; une décision ingérée reprend le nom de son fichier en slug, ce qui rend l'ingestion idempotente : une fiche qui existe déjà est sautée.

**`PATCH /cas/{id}`.** Les identifiants doivent être dans la grille et les valeurs valoir `true`, `false` ou `null` ; sinon 400. Chaque fait modifié reçoit une preuve `source: "utilisateur"`, `confiance: 1.0`, en gardant l'extrait existant.

**`PATCH /decisions/{id}`.** Fusionne les champs reçus, puis vérifie la fiche avec `valider.py` (on l'insère dans un dossier minimal). Si la fiche devient invalide, on refuse avec un 400 qui liste les problèmes, et rien n'est écrit.

**Construction du dossier** (`service.analyser(cas_id, facteurs=None)`) :
- `meta` : `version_format: "1.3"`, `dossier_id` = id du cas, `genere_le` = heure actuelle, `simulation` = `facteurs is not None` ;
- `grille` : copie de `contracts/grille.json`, relue à chaque appel ;
- `cas` : le cas stocké. En simulation, les facteurs fournis remplacent ceux du cas, et rien n'est écrit sur le disque ;
- `decisions` : toutes les fiches avec `validee: true`, triées par id ;
- `parametres` : valeurs par défaut du contrat (§5). `date_reference` = date du jour à Paris : c'est le back qui lit l'horloge, jamais le calculateur ;
- validation **avant** `completer()` et **après** ; au moindre problème, 422 avec la liste, en précisant s'il vient de l'entrée ou de la sortie ;
- aucun appel à Mistral dans ce chemin (objectif : < 1 s).

**Calculateur.** `from calculateur import completer`. Si le package `calculateur` est absent (`ModuleNotFoundError` dont `name == "calculateur"`), on utilise un faux calculateur qui renvoie `contracts/exemples/dossier_complet.json`, et on affiche un avertissement au démarrage. Toute autre erreur d'import doit planter : elle ne doit pas être masquée.

**Erreurs.** Une seule forme : `{"erreur": {"code", "message"}}`. Les erreurs de validation de requête de FastAPI (422 par défaut) sont **converties en 400** : dans le contrat, 422 est réservé au validateur. Une erreur ou un timeout Mistral donne 502.

**CORS** ouvert à toutes les origines (démo locale).

### Outils MCP

Le client est un **agent Mistral** (Le Chat, connecteur MCP distant), qui suit le prompt « Agent Stratégique Pivot ». Les noms et le découpage des outils suivent ce prompt. Les trois outils appellent `service.py`. Ils renvoient un **résumé** avec les libellés de la grille, et non le dossier complet de ~35 Ko, pour ne pas saturer le contexte de l'agent. Les règles que le prompt aurait laissées au LLM (score définitif ou non, leviers) sont **calculées ici** : le LLM extrait, le code décide.

| Outil | Entrée | Sortie |
|---|---|---|
| `pivot_structurer_cas` | `description`, `pieces?` (liste de textes), `ressort?` | Crée le cas par extraction Mistral, **sans l'analyser**. Le serveur ne voit pas les fichiers joints dans Le Chat : l'agent recopie mot pour mot dans `pieces` les passages utiles de chaque pièce. Chaque pièce est stockée comme un document du cas, et les extraits sont vérifiés contre `description` + `pieces`. Renvoie `cas_id`, chaque fait (libellé → Oui / Non / Inconnu, avec son extrait) et `a_confirmer` (libellé + question). |
| `pivot_etat_du_droit` | — | La grille (id, libellé, question, sens, importance) et le corpus validé (intitulé, formation, issue en libellé). Aucun appel à Mistral. |
| `pivot_arbitrer` | `cas_id`, `faits?` (`{facteur_id: true/false/null}`), `hypothese?` (défaut `false`) | Les `faits` sont **enregistrés** (source `utilisateur`, comme `PATCH /cas`) ; avec `hypothese: true`, c'est une simulation et rien n'est écrit. Lance ensuite l'analyse. Un id hors grille donne une erreur qui liste les ids valides. |

Résumé renvoyé par `pivot_arbitrer`, rien que des valeurs lues dans `resultat`. Les probabilités y sont en **pourcentage entier** (72, pas 0,72), pour que l'agent n'ait aucune conversion à faire :
- `position_majeure` : libellé de l'issue, `majeure.probabilite`, intervalle, `incertain` ; `probabilite_salariat` = P ; `indice_liceite` = 1 − P (probabilité d'indépendance), pour que l'agent ne calcule rien ;
- `definitif` : `false` dès qu'un facteur pivot vaut `null` dans le cas (`est_pivot` et `type: a_documenter`). C'est la « règle de blocage » du prompt. `faits_manquants` liste ces facteurs : libellé, question, P si vrai et si faux ;
- `decisions_retenues` : nombre, et intitulés de la majeure dans l'ordre du calculateur (la première est l'arrêt de référence) ; `decisions_ecartees` : intitulé et motif d'exclusion ;
- `pivots` (libellé, P si vrai et si faux), ou les paires de `pivots_combines` s'il n'y en a pas ; `exception` : issue, probabilité, conditions, décision de référence ;
- `leviers` : les 3 faits **connus** dont l'inversion fait le plus bouger P, avec la nouvelle valeur de P et d'`indice_liceite` ; `avertissements` tels quels.

## Style de code

Identifiants en **français, identiques au contrat** (`cas`, `dossier`, `facteurs`, `preuves`, `a_confirmer`). Des fonctions et des `dict`, pas de classes pour les données. Pas d'abstraction de stockage au-delà de `lire(genre, id)` / `ecrire(genre, id, obj)` / `lister(genre)`. Une exception `Erreur(statut, code, message)`, traduite en réponse HTTP **à un seul endroit** (`api.py`). Annotations de type sur les fonctions publiques ; commentaires seulement pour le « pourquoi ».

```python
def normaliser_faits(brut: dict, texte: str, grille: list[dict]) -> tuple[dict, dict]:
    """Sortie Mistral → facteurs stricts + preuves. Ne fait jamais confiance au LLM."""
    source = " ".join(texte.split())
    facteurs, preuves = {}, {}
    for f in grille:
        r = brut.get(f["id"]) if isinstance(brut.get(f["id"]), dict) else {}
        v = r.get("valeur")
        facteurs[f["id"]] = v if isinstance(v, bool) else None
        extrait = r.get("extrait") if isinstance(r.get("extrait"), str) else None
        if extrait and " ".join(extrait.split()) not in source:
            extrait = None  # citation introuvable = hallucination probable
        c = r.get("confiance")
        confiance = min(max(float(c), 0.0), 1.0) if isinstance(c, (int, float)) else 0.0
        if extrait is None:
            confiance = min(confiance, 0.5)  # pas de preuve → à confirmer
        if facteurs[f["id"]] is not None or extrait:
            preuves[f["id"]] = {"extrait": extrait, "confiance": confiance, "source": "extraction"}
    return facteurs, preuves
```

## Tests

- **`pytest`, dans `back/tests/`, sans réseau.** Mistral est remplacé par `monkeypatch` sur la fonction d'appel de `extraction.py`, et `DISTINGUO_DATA` pointe vers `tmp_path`.
- **Juge de paix : `contracts.valider.erreurs_dossier`.** Tout dossier produit par un test doit lui renvoyer `[]`.
- Trois fichiers, rien de plus :
  - `test_extraction.py` : normalisation (`"oui"` → `null`, facteur manquant → `null`, clé hors grille ignorée, extrait introuvable → `null` + confiance ≤ 0,5, déterminant `null` retiré, `validee` forcé à `false`) ;
  - `test_service.py` : avec le cas et les décisions de `dossier_entree.json`, le dossier construit est valide ; une simulation met `meta.simulation = true` et laisse le cas inchangé sur le disque ; une décision non validée n'entre pas dans le dossier ; un id `../x` est refusé ;
  - `test_api.py` : chaque route du §7 au moins une fois ; un corps mal formé donne 400 au format `erreur` ; un id inconnu donne 404 ; Mistral en échec donne 502.
- **Vérifs manuelles (clé réelle)** : `ingerer --limite 1` sur une vraie décision Legora ; le scénario de démo complet par l'API ; les trois outils `pivot_*` via l'Inspector.
- Pas d'objectif de couverture chiffré : on est en hackathon. Le critère est « chaque route et chaque règle de normalisation a son test ».

## Limites

**Toujours**
- Valider chaque dossier avec `valider.py` avant `completer()` et avant de le renvoyer.
- Normaliser toute sortie Mistral (règles ci-dessus) avant de l'écrire.
- Garder `extrait` + `confiance` pour chaque fait extrait.
- Vérifier le format des ids avant tout accès au disque.
- Lancer `uv run pytest` avant chaque commit.

**Demander d'abord**
- Toute modification de `contracts/` (annonce à l'équipe, montée de version, `generer_exemples.py`).
- Tout changement de forme de l'API du §7 : le front en dépend.
- Toute dépendance hors de la liste de la stack.
- Le `pyproject.toml` racine (partagé avec le calculateur) et les entrées de `.gitignore`.

**Jamais**
- De logique de pondération, de probabilité ou de pivot dans le back.
- D'appel à Mistral dans `/analyse`, `pivot_arbitrer` ni `pivot_etat_du_droit`.
- De passage automatique d'une décision à `validee: true` : seul le juriste le fait.
- De commit de `.env`, de clé API, de `data/cas/` ou de `data/documents/`.
- De modification de `calculateur/` ou de `front/`.
- De décisions `[FICTIF]` dans la démo.
- De tunnel public ouvert en dehors de la démo : il expose notre clé Mistral.

## Critères de réussite

| Jalon | Vérifiable par |
|---|---|
| **J1** | Les routes du §7 répondent, avec le faux calculateur. `ingerer --limite 1` transforme une vraie décision Legora en fiche ; une fois passée à `validee: true`, elle produit un dossier que `valider.py` accepte. `uv run pytest` passe. |
| **J2** | `POST /cas/{id}/analyse` renvoie un dossier complété par le **vrai** `completer()`, validé, en < 1 s avec ~20 décisions. |
| **MCP** | Dans Le Chat, avec le prompt « Agent Stratégique Pivot » : la description du cas de livreurs déclenche `pivot_structurer_cas` et `pivot_etat_du_droit` ; `pivot_arbitrer` renvoie `definitif: false` avec la sanction dans `faits_manquants`, et l'agent pose la question ; la réponse de l'avocat (« shadow-banning ») déclenche `pivot_arbitrer` avec `sanction_deconnexion: true` et la bascule. Tous les chiffres de la restitution sont ceux de l'outil. |
| **J3** | Le front est branché. Scénario de démo de bout en bout sur de vraies décisions validées : dépôt → faits à confirmer (dont la sanction) → analyse → case cochée → bascule. |

## Questions ouvertes

1. ~~Format du dataset Legora~~ **Réglé** : un TXT par décision et un tableau de synthèse JSON (voir « Ingestion »). Le corpus est constitué **à la main**, sans Judilibre. Il reste à l'équilibrer : 6 arrêts français, dont 1 seul pour l'indépendance, et aucune cour d'appel (T11).
2. ~~Client MCP de la démo~~ **Réglé** : un agent Mistral dans Le Chat, donc une URL publique via le tunnel. Il reste à vérifier quelle authentification le connecteur accepte (aucune, ou un jeton) : à tester en premier en T9.
3. **`pyproject.toml` racine partagé avec le calculateur** : à confirmer avec Mathis, et récupérer la liste de ses dépendances.
4. **Mistral OCR et DOCX** : à vérifier en premier. S'il ne les lit pas, on refuse les DOCX (400) : TXT et PDF suffisent pour la démo.
