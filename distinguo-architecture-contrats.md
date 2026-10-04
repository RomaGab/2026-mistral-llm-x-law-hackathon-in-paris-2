# Distinguo — Architecture et contrats d'équipe

*But : que le front, le back et le calculateur avancent en parallèle sans s'attendre.*
*Règle d'or : **le dossier `contracts/` fait foi**. Toute modification d'un format est annoncée à toute l'équipe avant d'être codée.*

> **Version 1.4 — compatible :** champ facultatif `pays` pour le cas et pour chaque décision (« France » par défaut). Le calculateur pondère chaque décision par son **système juridique** : même pays ×1, CJUE pour un pays membre de l'UE ×0,6, même tradition juridique (civil law / common law) ×0,35, tradition opposée ×0,08. Coefficient visible dans `detail_poids.systeme_juridique`.
>
> *Version 1.3 :* chaque ligne de `resultat.decisions` peut indiquer si la décision **s'applique a fortiori** au cas, quels arguments **manquent** au cas pour qu'elle s'applique, et quels arguments **contraires** le cas a en plus. Ces trois champs sont facultatifs : un dossier 1.2 reste valide. Le choix du modèle est fixé (§8).
>
> *Version 1.2 :* le résultat donne maintenant **l'analyse de chaque facteur** (`resultat.facteurs`) : est-il pivot (`est_pivot`), son niveau, s'il est à documenter ou un levier, ce que deviendrait P s'il valait vrai ou faux, et quelles décisions seraient alors écartées. **Plusieurs facteurs peuvent être pivots** (`resultat.pivots`), et si aucun ne l'est seul, on cherche les paires (`resultat.pivots_combines`). Les champs `impacts` et `fait_pivot` de la v1.1 sont supprimés. Personne ne les avait encore codés, donc ce n'est pas une v2.0, mais c'est un changement incompatible.
>
> *Version 1.1 :* format unique, le « dossier ». Issue booléenne. Grille, schéma, validateur et exemples dans `contracts/`.

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
7. **Recalcul instantané :** changer un fait relance seulement le calculateur, sans LLM. Moins d'une seconde.
8. **Des cases à trois états dans le front :** oui / non / inconnu. Une case à deux états ne peut pas représenter un fait inconnu, qui est le point de départ de la démo.
9. **Arrondis :** le calculateur arrondit toutes les probabilités à 2 décimales **d'abord**, puis calcule les drapeaux (issue, incertain, pivot, niveau) sur les valeurs arrondies. Sinon, le front et le validateur verraient des incohérences à 0,50 près.
10. **Contrôle automatique :** tout dossier peut être vérifié par `contracts/valider.py`, qui contrôle le format **et** la cohérence.

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
  "meta":       { "version_format": "1.4", "dossier_id": "cas_7f3a9c21", "simulation": false },
  "grille":     { "version": "1.0", "question": "…", "issue": { "libelle": "…", "si_vrai": "Salariat", "si_faux": "Indépendance" }, "facteurs": [ … ] },
  "cas":        { "id": "cas_7f3a9c21", "description": "…", "ressort": "CA Paris",
                  "facteurs": { "geolocalisation_suivi": true, "sanction_deconnexion": null, "…": "…" },
                  "preuves":  { "geolocalisation_suivi": { "extrait": "…", "confiance": 1.0, "source": "extraction" } },
                  "a_confirmer": ["sanction_deconnexion"] },
  "decisions":  [ { "id": "…", "intitule": "Cass. soc., 4 mars 2020", "formation": "cass", "date": "2020-03-04",
                    "issue": true, "validee": true,
                    "facteurs": { "…": "…" }, "determinants": ["sanction_deconnexion"], "…": "…" } ],
  "parametres": { "modele": "logistique_bayesienne", "niveau_intervalle": 0.95, "date_reference": "2026-10-04" },
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
| `pays` | v1.4, facultatif, « France » par défaut. Système juridique du client : les décisions d'un autre système pèsent beaucoup moins. |

### Décision
| Champ | Sens |
|---|---|
| `intitule` | Libellé court pour le front, ex. « Cass. soc., 4 mars 2020 » |
| `formation` | `ass_pleniere` · `ch_mixte` · `cass` · `ca` · `premiere_instance` |
| `ressort` | `null` pour la Cour de cassation, sinon `"CA Paris"`, etc. |
| `pays` | v1.4, facultatif, « France » par défaut. Ex. « Royaume-Uni », « États-Unis », « Union européenne » (CJUE). Pour un pays étranger, `formation: "cass"` désigne sa cour suprême. |
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
| `niveau_intervalle` | 0,95 par défaut (intervalle à 95 %) |
| `date_reference` | Date utilisée pour l'ancienneté des décisions. Le calculateur ne lit jamais l'horloge. |
| `seuil_exception` | 0,15 par défaut. Probabilité minimale de l'issue minoritaire pour afficher une exception même sans pivot. |
| `seuil_sensibilite` | 0,10 par défaut. Écart de P à partir duquel un facteur est « sensible ». |
| `marge_pivot` | 0,15 par défaut (le back envoie 0,10, adapté à σ = 0,3). Pour être pivot, un fait inversé doit faire passer P de l'autre côté de 0,5 **et** à au moins cette distance de 0,5. |
| `sigma_a_priori` | Facultatif, 0,3 par défaut (régression logistique), choisi par validation croisée sur les 12 arrêts : même justesse (12/12) et même calibration qu'à 0,5, mais 11 résultats nets sur 12 au lieu de 8. Confiance dans la grille du juriste : plus petit = le modèle suit davantage la grille. À choisir avec `python -m calculateur.evaluation`. |
| `kappa` | Facultatif, 2,0 par défaut (vote pondéré). Force probante d'une décision. |

### Résultat (rempli par le calculateur)
**Convention : toutes les probabilités désignent P(issue = `true`), sauf `majeure.probabilite` et `exception.probabilite`.**

| Champ | Sens |
|---|---|
| `prediction.probabilite` | P(requalification) |
| `prediction.intervalle` | Intervalle au niveau demandé. Il contient toujours la probabilité. |
| `prediction.issue` | `probabilite > 0,5` |
| `prediction.incertain` | `true` si l'intervalle contient 0,5. Le front affiche alors « incertain ». |
| `majeure` | L'issue prédite, sa probabilité (= max(p, 1 − p)) et les décisions **retenues** qui la soutiennent, de la plus forte à la plus faible |
| `exception` | L'issue inverse, sa probabilité (= 1 − majeure), jusqu'à 3 faits qui en rapprochent le plus (`conditions`), et la décision retenue la plus proche de ce camp. Présente si et seulement s'il y a des pivots, des pivots combinés, ou si l'issue minoritaire atteint `seuil_exception`. |
| `pivots` | Identifiants des facteurs pivots, du plus influent au moins influent. Peut être vide. |
| `pivots_combines` | Si `pivots` est vide : jusqu'à 5 **paires** de faits qui font basculer ensemble (ex. géolocalisation **et** sanction). Vide sinon. |
| `facteurs` | **L'analyse de chaque facteur de la grille**, détaillée ci-dessous |
| `decisions[]` | Une ligne par décision du dossier, **dans le même ordre** : retenue ou non, motif d'exclusion, proximité (0 à 1), poids utilisé, détail du poids, alignement fait par fait (`identique` · `oppose` · `inconnu`), et en v1.3 la lecture a fortiori (ci-dessous) |
| `avertissements` | Messages à afficher tels quels (corpus déséquilibré, réforme en cours…) |

#### `resultat.decisions[]` : la lecture a fortiori (v1.3, facultative)
Chaque fait connu du cas ou d'une décision est un **argument** pour l'un des deux camps : « sanction = oui » est un argument pour le salariat, « peut travailler pour des concurrents = oui » un argument pour l'indépendance. Une décision s'applique **a fortiori** au cas si le cas a tous ses arguments en faveur de son issue, et aucun argument contraire de plus.

| Champ | Sens | Usage dans le front |
|---|---|---|
| `s_applique_a_fortiori` | `true` si rien ne manque et rien ne s'oppose | « Cet arrêt s'applique pleinement à votre cas » |
| `arguments_manquants` | Arguments de la décision, en faveur de son issue, que le cas n'a pas. Liste de `{"facteur", "valeur"}` | Si le fait vaut `null` dans le cas : « à documenter » ; s'il a la valeur opposée : déjà couvert par les contraires, ne pas afficher deux fois |
| `arguments_contraires` | Arguments du cas, contre l'issue de la décision, que la décision n'avait pas | « Votre cas s'en distingue par… » |

Exemple tiré de `dossier_complet.json` : pour CA Paris 2023 (indépendance), il manque `tarif_impose = non`, et le cas a en contraire `tarif_impose = oui`. Lecture : *« cet arrêt s'appliquerait si le prix n'était pas fixé par la plateforme »*.

Avec un petit corpus et un faisceau d'indices, il est rare qu'une décision s'applique pleinement : dans les exemples, aucune ne le fait. Ces champs servent à **expliquer** (ce qui rapproche ou distingue le cas de chaque arrêt), pas à décider.

#### `resultat.facteurs` : une entrée par facteur, pour l'affichage ligne par ligne
```json
"sanction_deconnexion": {
  "est_pivot": true,
  "niveau": "pivot",
  "type": "a_documenter",
  "probabilite_si_vrai": 0.72,
  "probabilite_si_faux": 0.24,
  "contribution": 0.0,
  "ecartees_si_vrai": ["exemple-ca-paris-1", "exemple-ca-lyon-1"],
  "ecartees_si_faux": ["exemple-cass-1", "exemple-cass-2", "exemple-ca-lyon-1"]
}
```

| Champ | Sens | Usage dans le front |
|---|---|---|
| `est_pivot` | Changer ce fait fait basculer l'issue **franchement** (au-delà de `marge_pivot`) | Badge « PIVOT » |
| `niveau` | `pivot` · `sensible` (fait bouger P d'au moins `seuil_sensibilite`) · `faible` · `neutralise` (importance 0) | Couleur de la ligne |
| `type` | `a_documenter` si le fait du cas est inconnu ; `levier` s'il est connu | « À demander au client » / « Si le client changeait ce point… » |
| `probabilite_si_vrai` / `_si_faux` | P(issue vraie) si ce fait valait vrai / faux. Pour un fait connu, la valeur actuelle redonne P. | Au survol : « avec : 72 % · sans : 24 % » |
| `contribution` | Ce que le fait apporte au score par rapport à « inconnu » : logit(P) − logit(P si le fait était inconnu). > 0 : vers la requalification. 0 si inconnu ou neutralisé. | Barre d'explication |
| `ecartees_si_vrai` / `_si_faux` | **Liste complète** des décisions écartées si ce fait valait vrai / faux | Comparée à la liste actuelle : « si oui, CA Paris 2021 ne s'applique plus » |

**Un fait connu ne se teste que dans un sens** (on l'inverse). Un fait inconnu se teste dans les deux. Un facteur est pivot si l'un des tests franchit 0,5 avec la marge.

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
- Probabilité, intervalle, issue, incertitude, majeure et exception sont cohérents entre eux.
- `resultat.facteurs` couvre exactement la grille. Pour chaque facteur, `est_pivot`, `niveau` et `type` correspondent aux probabilités et à la valeur du cas.
- Un facteur neutralisé n'est jamais pivot et n'a aucun effet.
- `pivots` liste exactement les facteurs pivots, triés. `pivots_combines` est vide s'il existe des pivots simples.
- Les conditions de l'exception reprennent les probabilités de `resultat.facteurs`.
- (v1.3) Si une ligne de `resultat.decisions` donne la lecture a fortiori, ses trois champs sont présents ensemble et correspondent aux faits du cas et de la décision.
- `version_format` vaut `"1.2"` ou `"1.3"`.

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
- **En Python :** `from calculateur import completer, ErreurDossier`. `ErreurDossier.problemes` liste les erreurs du dossier d'entrée (à renvoyer en 422).
- **En ligne de commande**, depuis la racine du dépôt :
  - `uv run python -m calculateur entree.json -o sortie.json` complète un dossier ;
  - `uv run python -m calculateur.evaluation dossier.json` retire chaque décision tour à tour et compare les modèles (justesse, cas nets, Brier) ;
  - `uv run pytest` lance les tests du calculateur.
- **Installation :** `uv sync` (le `pyproject.toml` racine est commun au back et au calculateur).
- **Déterministe :** même dossier, même résultat. Pas d'horloge (`date_reference`), graine aléatoire fixe.
- **Rapide :** moins d'une seconde pour une vingtaine de décisions, faits inversés compris.

### Ce qu'il fait
1. **Exclusions :** une décision est écartée si un de ses faits déterminants est contraire au cas, ou si sa solution a été remise en cause.
2. **Pondération des décisions :** autorité, publication, ancienneté et ressort donnent un poids de base, **multiplié** par le coefficient de système juridique (v1.4) :

   | Décision par rapport au cas | Coefficient |
   |---|---|
   | Même pays | ×1 |
   | CJUE, pour un cas d'un pays membre de l'UE | ×0,6 |
   | Même tradition juridique, autre pays (ex. Espagne pour la France) | ×0,35 |
   | Tradition opposée (common law contre civil law), ou pays inconnu de la table | ×0,08 |

   Un coefficient multiplicatif, et non un critère de plus dans la somme, pour qu'une décision d'un autre système pèse **beaucoup** moins, quelle que soit son autorité chez elle. La table des traditions est dans `calculateur/precedents.py`.
3. **Modèle principal, la régression logistique bayésienne :**
   - variable à prédire : `issue` ;
   - codage des faits : `true` = +1, `false` = −1, `null` = 0 (un fait inconnu ne pousse dans aucun sens) ; facteurs neutralisés exclus ;
   - point de départ a priori : le sens donné par `oriente` et la force donnée par `importance`. Les décisions ajustent ces valeurs ;
   - poids d'observation : le poids de chaque décision ;
   - intervalle : tiré de l'incertitude du modèle.
4. **Modèle de comparaison, le vote pondéré :** mêmes entrées, même sortie. Les deux sont comparés en retirant chaque décision tour à tour, et on garde le meilleur.
5. **Analyse des facteurs :** chaque fait est testé à vrai et à faux. On recalcule les exclusions puis P, et on en déduit pivot, niveau, contribution et décisions écartées. Si aucun fait seul n'est pivot, on teste les paires (environ 100 calculs, instantané). L'exception reprend les faits qui rapprochent le plus de l'issue minoritaire.
6. **Proximité et alignement :** comparaison fait par fait du cas avec chaque décision, pour la matrice et pour désigner la décision de référence de l'exception.
7. **Lecture a fortiori (v1.3) :** pour chaque décision, les arguments qui manquent au cas et les arguments contraires en trop.

### Pourquoi ce modèle (décision d'équipe)
**Choix : régression logistique bayésienne, avec la grille du juriste comme a priori, et une lecture a fortiori pour l'explication.**

| Option | Décision | Raison |
|---|---|---|
| Régression logistique bayésienne | **Moteur** | Marche avec une quinzaine de décisions grâce à l'a priori. Traduction directe du faisceau d'indices : le juge pèse les indices globalement, le modèle additionne leurs poids. Pivots et explications testés sur le contrat. |
| LOPA (Morello et al., JURIX 2025) : agrégation des précédents qui s'appliquent a fortiori | **Explication + vision** | Testé sur nos exemples : aucune décision ne s'applique a fortiori, donc il s'abstiendrait sur tout. Il faut des centaines de décisions. On reprend sa lecture précédent par précédent pour expliquer (point 7). |
| Vote pondéré | Comparaison | Défaut connu : beaucoup de précédents faibles peuvent écraser un précédent fort. |
| Forêt aléatoire | Écartée | Surapprendrait sur 15 décisions, et n'explique rien. |

**Ce que dit la littérature :**
- **Morello, Ciabattoni, Gray (JURIX 2025)** : sur 201 affaires décrites par des facteurs, les modèles transparents fondés sur les précédents font jeu égal avec une forêt aléatoire optimisée (F1 0,754 contre 0,740), tout en expliquant chaque décision et en donnant une confiance utile.
- **Gray, Savelka, Oliver, Ashley (2024)** : des facteurs proposés par un LLM puis affinés par un humain prédisent aussi bien que ceux des experts. Ce sont eux qui valident notre chaîne « le LLM extrait, l'humain valide ». En revanche, chez eux, la régression logistique régularisée fait moins bien que la forêt aléatoire (MCC 0,56 contre 0,66) : ne pas les citer pour la parité.

**Réglage :** σ (la confiance dans la grille) est choisi en retirant chaque décision tour à tour, parmi 0,2, 0,3 et 0,5. On compare au vote pondéré, à Mistral seul et à la classe majoritaire.

**Phrase pour le pitch :** *« Un raisonnement transparent sur les facteurs, une approche qui fait jeu égal avec les modèles boîte noire selon la littérature récente (Morello et al., JURIX 2025), et qui dit quand il ne sait pas. »*

---

## 9. Travailler en parallèle

Tout est déjà dans `contracts/` :

| Fichier | Sert à |
|---|---|
| `grille.json` | Les 18 facteurs. Tout le monde. |
| `dossier.schema.json` | Le format exact du dossier |
| `valider.py` | Vérifier n'importe quel dossier |
| `exemples/dossier_entree.json` | Ce que le back envoie au calculateur (5 décisions **fictives**) |
| `exemples/dossier_complet.json` | Ce que le calculateur renvoie : P = 0,47, indépendance, incertain, 5 pivots (dont la sanction), 1 décision écartée |
| `exemples/dossier_apres_bascule.json` | La même chose avec « sanction » à oui : P = 0,72, bascule vers le salariat, 2 pivots (sanction, géolocalisation), une 2e décision écartée |
| `generer_exemples.py` | Régénère les exemples avec le **vrai calculateur**, puis les valide : `uv run python contracts/generer_exemples.py` |

Les décisions sont **fictives** : les chiffres sont ceux du vrai calculateur, mais sur des données inventées, donc sans valeur juridique. Ils servent à développer, pas à la démo.

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
- **Changer un format :** proposer la modification de `contracts/` à toute l'équipe, mettre à jour schéma, exemples et validateur ensemble, puis augmenter la version (ajout d'un champ optionnel : version mineure suivante, 1.4 ; changement incompatible : 2.0). Régénérer les exemples avec `generer_exemples.py`.

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
- [x] Le back est en Python (SPEC-back) : il importe `calculateur` directement. `pyproject.toml` racine créé avec les dépendances du calculateur ; le back y ajoute les siennes.
- [ ] Fichiers JSON ou SQLite pour le stockage côté back ?
- [ ] Le serveur MCP est-il dans la démo, ou seulement mentionné dans le pitch ?
- [ ] Le juriste valide-t-il la grille telle quelle (facteurs, orientations, importances) ?
- [ ] **Calculateur — largeur des intervalles.** L'intervalle est à 95 %. Avec une quinzaine de décisions, il est très large : dans les exemples, même après la bascule (P = 0,72), il va de 0,16 à 0,97 et le résultat reste « incertain ». Pour qu'un statut « net » apparaisse, il faudra un a priori plus fort ou plus de décisions ; sinon, assumer « salariat probable mais incertain » dans la démo.
