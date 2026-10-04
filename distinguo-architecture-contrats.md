# Distinguo — Architecture et contrats d'équipe

*But : que le front, le back et le calculateur avancent en parallèle sans s'attendre.*
*Règle d'or : **le dossier `contracts/` fait foi**. Toute modification d'un format est annoncée à toute l'équipe avant d'être codée.*

> **Version 1.1 — ce qui change :** un **format unique, le « dossier »**, remplace la requête et le résultat séparés. Le back envoie un dossier au calculateur, qui le renvoie complété. L'issue à prédire devient un booléen (`true` = requalification). Ajout de la grille complète, du schéma JSON, d'un validateur et d'exemples prêts à l'emploi dans `contracts/`.

---

## 1. Les trois briques

```
┌──────────────┐   REST/JSON   ┌───────────────────────────────┐   dossier     ┌──────────────┐
│    FRONT     │ ────────────► │             BACK              │ ────────────► │ CALCULATEUR  │
│              │               │                               │  (resultat    │              │
│ question     │               │ API                           │   = null)     │ exclusions   │
│ dépôt docs   │               │ ETL : texte → faits (Mistral) │               │ modèle       │
│ faits à      │ ◄──────────── │ base : décisions, cas         │ ◄──────────── │ fait pivot   │
│ confirmer    │   dossier     │ construit le dossier          │   dossier     │ alignements  │
│ résultat     │   complété    │ (option) serveur MCP          │   complété    │              │
└──────────────┘               └───────────────────────────────┘               └──────────────┘
```

| Brique | Responsable | Rôle | Ne fait **pas** |
|---|---|---|---|
| **Front** | [dev front] | Saisie du cas, dépôt de documents, confirmation des faits, affichage du dossier complété (balance, matrice, cases à cocher) | Aucun calcul, aucun appel à Mistral |
| **Back** | [dev back] | API, extraction des faits (ETL), stockage des décisions et des cas, construction du dossier, appel du calculateur, serveur MCP en option | Aucune logique de pondération |
| **Calculateur** | Mathis | Fonction pure : reçoit un dossier, remplit son bloc `resultat`. Évaluation statistique du modèle. | Aucun appel réseau, aucun LLM, aucun stockage |
| **Grille et corpus** | [juriste / ops, sinon partagé] | `contracts/grille.json`, choix des décisions, relecture des fiches extraites | — |

**Le calculateur est une librairie Python appelée directement par le back**, pas un service séparé. Comme il prend et renvoie un dossier JSON, il pourra devenir un service plus tard sans rien changer.

---

## 2. Principes

1. **Un seul format : le dossier.** Le back le construit, le calculateur le complète, le front l'affiche.
2. **Une seule grille de facteurs**, dans `contracts/grille.json`. Le back s'en sert pour extraire, le calculateur pour pondérer, le front pour afficher les libellés.
3. **Trois valeurs pour un fait : `true` / `false` / `null`.** `null` veut dire « on ne sait pas », ce qui est différent de `false`. Le scénario de démo commence justement avec une sanction inconnue.
4. **L'issue est un booléen :** `true` = requalification (salariat), `false` = indépendance. Le front affiche les libellés de la grille (`si_vrai` / `si_faux`), jamais `true` ou `false`.
5. **Deux relectures humaines :** l'avocat confirme les faits du cas ; le juriste relit chaque décision extraite avant qu'elle ne serve (`validee: true`).
6. **Traçabilité :** chaque fait extrait garde l'extrait du texte qui le justifie et un niveau de confiance.
7. **Recalcul instantané :** cocher un fait relance seulement le calculateur, sans LLM. Moins d'une seconde.
8. **Contrôle automatique :** tout dossier peut être vérifié par `contracts/valider.py`, qui contrôle le format **et** la cohérence.

---

## 3. Parcours complet

```
 Avocat            FRONT                     BACK                              CALCULATEUR
   │  question +     │                         │                                    │
   │  documents ───► │  POST /documents ─────► │ texte → faits (Mistral)            │
   │                 │  POST /cas ───────────► │ cas créé, faits extraits           │
   │                 │ ◄────── cas (+ preuves) │                                    │
   │ ◄── « confirmez │                         │                                    │
   │     ces faits » │                         │                                    │
   │  corrections ─► │  PATCH /cas/{id} ─────► │ faits mis à jour                   │
   │                 │  POST /cas/{id}/analyse►│ construit le dossier ────────────► │ remplit resultat
   │                 │ ◄──── dossier complété ─│ ◄────────────── dossier complété ─ │
   │ ◄── balance,    │                         │                                    │
   │     matrice     │                         │                                    │
   │  coche un fait► │  POST /cas/{id}/analyse  {"facteurs": {...}} ──────────────► │ recalcule (< 1 s)
   │ ◄── bascule     │ ◄─────────────────────────────────────────── dossier complété│
```

---

## 4. Le format unique : le dossier

Un dossier a six blocs. Le schéma exact est dans `contracts/dossier.schema.json`, et des exemples complets dans `contracts/exemples/`.

| Bloc | Contenu | Rempli par |
|---|---|---|
| `meta` | Version du format, identifiant, simulation ou non | Back |
| `grille` | Les facteurs de la question de droit, avec libellé, orientation et importance | Back (copie de `grille.json`) |
| `cas` | Les faits du client, avec leurs preuves | Back |
| `decisions` | Les décisions **validées**, avec leurs faits, leur issue et leurs métadonnées | Back |
| `parametres` | Modèle à utiliser, niveau de l'intervalle, date de référence | Back |
| `resultat` | `null` à l'envoi ; prédiction, majeure, exception, fait pivot, détail par décision au retour | **Calculateur** |

### Forme générale
```json
{
  "meta":       { "version_format": "1.0", "dossier_id": "cas_7f3a9c21", "simulation": false },
  "grille":     { "version": "1.0", "question": "…", "issue": { "libelle": "…", "si_vrai": "Salariat", "si_faux": "Indépendance" }, "facteurs": [ … ] },
  "cas":        { "id": "cas_7f3a9c21", "description": "…", "ressort": "CA Paris",
                  "facteurs": { "geolocalisation_suivi": true, "sanction_deconnexion": null, "…": "…" },
                  "preuves":  { "geolocalisation_suivi": { "extrait": "…", "confiance": 1.0, "source": "extraction" } },
                  "a_confirmer": ["sanction_deconnexion"] },
  "decisions":  [ { "id": "…", "intitule": "Cass. soc., 4 mars 2020", "formation": "cass", "date": "2020-03-04",
                    "issue": true, "validee": true,
                    "facteurs": { "…": "…" }, "determinants": ["sanction_deconnexion"], "…": "…" } ],
  "parametres": { "modele": "logistique_bayesienne", "niveau_intervalle": 0.8, "date_reference": "2026-10-04" },
  "resultat":   null
}
```

---

## 5. Le détail des blocs

### Grille (`contracts/grille.json`)
| Champ | Sens |
|---|---|
| `issue.si_vrai` / `issue.si_faux` | Libellés affichés pour `true` / `false` (« Salariat » / « Indépendance ») |
| `facteurs[].id` | Identifiant utilisé partout. **L'ordre de la liste est l'ordre d'affichage et l'ordre des colonnes du modèle.** |
| `facteurs[].question` | Question posée à Mistral lors de l'extraction |
| `facteurs[].oriente` | `true` : quand le fait est présent, il pousse vers la requalification. `false` : vers l'indépendance. `null` : facteur neutralisé |
| `facteurs[].importance` | 1,0 déterminant · 0,5 important · 0,2 faible · 0 neutralisé (ignoré par le modèle, affiché quand même) |

La grille contient 18 facteurs (15 actifs, 3 neutralisés). Le juriste doit la valider.

### Cas
| Champ | Sens |
|---|---|
| `facteurs` | **Tous** les facteurs de la grille, avec `true` / `false` / `null` |
| `preuves` | Pour les faits renseignés : extrait du document, confiance (0 à 1), source (`extraction`, `utilisateur`, `juriste`) |
| `a_confirmer` | Faits inconnus ou de confiance < 0,6. Le front les met en avant. Calculé par le back. |
| `ressort` | Cour d'appel du client, ex. `"CA Paris"`. Sert au critère géographique. |

### Décision
| Champ | Sens |
|---|---|
| `intitule` | Libellé court pour le front, ex. « Cass. soc., 4 mars 2020 » |
| `formation` | `ass_pleniere` · `ch_mixte` · `cass` · `ca` · `premiere_instance` |
| `ressort` | `null` pour la Cour de cassation, sinon `"CA Paris"`, etc. |
| `publication` | `R` · `B` · `inedit` · `na` |
| `issue` | **Issue au fond**, pas le dispositif. Une cassation peut aboutir à `true`. |
| `facteurs` | **Tous** les facteurs de la grille |
| `determinants` | Faits sur lesquels la juridiction s'appuie expressément. Ils ne peuvent pas valoir `null`. |
| `remise_en_cause` | Texte si revirement ou réforme, sinon `null`. La décision est alors écartée. |
| `validee` | `true` après relecture du juriste. **Seules les décisions validées entrent dans un dossier.** |

### Paramètres
| Champ | Sens |
|---|---|
| `modele` | `logistique_bayesienne` (principal) ou `vote_pondere` (comparaison) |
| `niveau_intervalle` | 0,8 par défaut |
| `date_reference` | Date utilisée pour l'ancienneté des décisions. Le calculateur ne lit jamais l'horloge. |
| `seuil_exception` | 0,15 par défaut |

### Résultat (rempli par le calculateur)
**Convention : toutes les probabilités désignent P(issue = `true`), sauf `majeure.probabilite` et `exception.probabilite`.**

| Champ | Sens |
|---|---|
| `prediction.probabilite` | P(requalification) |
| `prediction.intervalle` | Intervalle au niveau demandé. Il contient toujours la probabilité. |
| `prediction.issue` | `probabilite > 0,5` |
| `prediction.incertain` | `true` si l'intervalle contient 0,5. Le front affiche alors « incertain ». |
| `majeure` | L'issue prédite, sa probabilité (= max(p, 1 − p)) et les décisions **retenues** qui la soutiennent |
| `exception` | L'issue inverse, sa probabilité (= 1 − majeure), les faits qui y mènent (`conditions`) et la décision retenue la plus proche de ce camp. `null` s'il n'y a pas d'exception crédible. |
| `impacts` | Pour chaque fait non neutralisé : ce que deviendrait P si on l'inversait (un fait `null` est testé à `true` **et** à `false`). Trié par effet décroissant. |
| `fait_pivot` | Le premier élément de `impacts` |
| `impacts[].bascule` | `true` si l'issue prédite changerait |
| `decisions[]` | Une ligne par décision du dossier, **dans le même ordre** : retenue ou non, motif d'exclusion, proximité (0 à 1), poids utilisé, détail du poids, alignement fait par fait (`identique` · `oppose` · `inconnu`) |
| `avertissements` | Messages à afficher tels quels (corpus déséquilibré, réforme en cours…) |

---

## 6. Les règles du contrat

Elles sont toutes vérifiées par `contracts/valider.py`. Un dossier qui en viole une est refusé.

**À l'envoi (back → calculateur)**
- Le cas et chaque décision contiennent **exactement** les facteurs de la grille : ni manquant, ni en trop.
- Les valeurs sont `true`, `false` ou `null` : jamais `"oui"`, `1` ou `"inconnu"`.
- Les décisions ont des identifiants uniques, sont toutes `validee: true`, et leurs faits déterminants ne sont pas `null`.
- Aucun champ hors schéma.

**Au retour (calculateur → back)**
- `resultat.decisions` reprend les décisions dans le même ordre.
- Une décision est écartée si et seulement si elle a un motif d'exclusion.
- La majeure ne cite que des décisions retenues, de la bonne issue.
- Probabilité, intervalle, issue, incertitude, majeure, exception, `delta` et `bascule` sont cohérents entre eux.
- `fait_pivot` est le premier des `impacts`.

**Vérifier un dossier :**
```
uv run --with jsonschema python contracts/valider.py mon_dossier.json
```

---

## 7. API du back (pour le front)

| Méthode | Route | Entrée | Sortie |
|---|---|---|---|
| GET | `/sante` | — | `{"ok": true}` |
| GET | `/grille` | — | Grille |
| GET | `/decisions` | — | Liste des décisions, validées ou non |
| GET | `/decisions/{id}` | — | Décision |
| PATCH | `/decisions/{id}` | Champs corrigés, dont `validee` | Décision (relecture du juriste) |
| POST | `/documents` | Fichier (PDF, TXT, DOCX) + `type` : `cas` ou `decision` | `{"document_id", "type", "decision_id"}` — une décision déposée est créée avec `validee: false` |
| POST | `/cas` | `{"question", "description", "ressort", "document_ids"}` | Cas (faits extraits, preuves, à confirmer) |
| GET | `/cas/{id}` | — | Cas |
| PATCH | `/cas/{id}` | `{"facteurs": {"sanction_deconnexion": true}}` | Cas mis à jour (source `utilisateur`) |
| POST | `/cas/{id}/analyse` | Optionnel : `{"facteurs": {...}}` | **Dossier complété** |

- **Simulation :** si `facteurs` est fourni à `/analyse`, ces valeurs remplacent celles du cas **pour ce calcul seulement**, sans être enregistrées. Le dossier renvoyé a `meta.simulation = true`. C'est ce qu'utilisent les cases à cocher.
- **Délais :** `POST /cas` et `POST /documents` appellent Mistral (10 à 30 secondes) : le front affiche un chargement. `/analyse` répond en moins d'une seconde.
- **Erreurs :** `{"erreur": {"code": "...", "message": "..."}}`. Codes : 400 requête mal formée, 404 introuvable, 422 dossier refusé par le validateur (le message liste les problèmes), 502 erreur Mistral.

---

## 8. Le calculateur

### Interface
- **Une fonction :** `completer(dossier) → dossier`. Elle renvoie une copie avec `resultat` rempli, sans modifier l'entrée. Si le dossier est invalide, elle lève une erreur qui liste tous les problèmes.
- **Une commande** pour tester sans le back : `python -m calculateur entree.json > sortie.json`.
- **Déterministe :** même dossier, même résultat. Pas d'horloge (`date_reference`), graine aléatoire fixe.
- **Rapide :** moins d'une seconde pour une vingtaine de décisions, faits inversés compris.

### Ce qu'il fait
1. **Exclusions :** une décision est écartée si un de ses faits déterminants est contraire au cas, ou si sa solution a été remise en cause.
2. **Pondération des décisions :** autorité, publication, ancienneté et ressort donnent le poids de chaque décision retenue.
3. **Modèle principal, la régression logistique bayésienne :**
   - variable à prédire : `issue` ;
   - codage des faits : `true` = +1, `false` = −1, `null` = 0 (un fait inconnu ne pousse dans aucun sens) ; facteurs neutralisés exclus ;
   - point de départ a priori : le sens donné par `oriente` et la force donnée par `importance`. Les décisions ajustent ces valeurs ;
   - poids d'observation : le poids de chaque décision ;
   - intervalle : tiré de l'incertitude du modèle.
4. **Modèle de comparaison, le vote pondéré :** mêmes entrées, même sortie. Les deux sont comparés en retirant chaque décision tour à tour, et on garde le meilleur.
5. **Fait pivot, impacts et exception :** chaque fait est inversé un par un et on mesure l'effet sur P.
6. **Proximité et alignement :** comparaison fait par fait du cas avec chaque décision, pour la matrice et pour désigner la décision de référence de l'exception.

---

## 9. Travailler en parallèle

Tout est déjà dans `contracts/` :

| Fichier | Sert à |
|---|---|
| `grille.json` | Les 18 facteurs. Tout le monde. |
| `dossier.schema.json` | Le format exact du dossier |
| `valider.py` | Vérifier n'importe quel dossier |
| `exemples/dossier_entree.json` | Ce que le back envoie au calculateur (5 décisions **fictives**) |
| `exemples/dossier_complet.json` | Ce que le calculateur renvoie : statut incertain, majeure « indépendance », exception « salariat si sanction » |
| `exemples/dossier_apres_bascule.json` | La même chose après avoir coché « sanction » : la majeure bascule vers le salariat |

Les décisions et les probabilités des exemples sont **fictives et illustratives**. Elles servent à développer, pas à la démo.

- **Front :** branché sur les fichiers d'exemple, sans back. Les deux fichiers complets suffisent pour coder la balance, la matrice et la bascule.
- **Back :** un faux calculateur qui renvoie `dossier_complet.json`, remplacé par le vrai à l'intégration. Il valide chaque dossier qu'il construit.
- **Calculateur :** part de `dossier_entree.json`, et vérifie chaque sortie avec le validateur.

---

## 10. Organisation du dépôt

```
├── contracts/          ← formats, grille, exemples (modifiés uniquement après accord)
├── front/
├── back/
├── calculateur/        ← package Python importé par le back
├── data/
│   ├── decisions/      ← textes bruts
│   └── fiches/         ← décisions extraites puis validées
└── distinguo-architecture-contrats.md
```
- Une branche par personne, fusion sur `main` à chaque jalon.
- Personne ne modifie le dossier d'un autre sans le prévenir.
- **Changer un format :** proposer la modification de `contracts/` à toute l'équipe, mettre à jour schéma, exemples et validateur ensemble, puis augmenter la version (ajout d'un champ optionnel : 1.1 ; changement incompatible : 2.0).

---

## 11. Jalons communs

| Jalon | Quand | Ce qui doit être prêt |
|---|---|---|
| **J0 — Contrats figés** | ✅ fait | `contracts/` en ligne, à relire par chacun |
| **J1 — Chacun tourne seul** | J0 + 1h30 | Front sur les exemples ; back qui extrait une vraie décision en dossier valide ; calculateur qui complète `dossier_entree.json` et passe le validateur |
| **J2 — Back ↔ calculateur** | J0 + 2h30 | `POST /cas/{id}/analyse` renvoie un vrai dossier complété |
| **J3 — Bout en bout** | J0 + 3h30 | Front branché sur le back, vraies décisions validées, scénario de démo qui tourne |
| **Gel** | 17h00 | Plus de nouvelle fonctionnalité. Captures et vidéo de secours. |
| **Soumission** | 18h00 | — |

Un point de 5 minutes à chaque jalon : ce qui marche, ce qui bloque, ce qui change.

---

## 12. Points à trancher maintenant

- [ ] Qui joue le rôle de juriste (grille, choix du corpus, relecture des décisions) ?
- [ ] Le back est-il en Python ? Si non, le calculateur devient un petit service HTTP qui prend et renvoie le même dossier.
- [ ] Fichiers JSON ou SQLite pour le stockage côté back ?
- [ ] Le serveur MCP est-il dans la démo, ou seulement mentionné dans le pitch ?
- [ ] Le juriste valide-t-il la grille telle quelle (facteurs, orientations, importances) ?
