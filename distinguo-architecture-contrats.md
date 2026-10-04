# Distinguo — Architecture et contrats d'équipe

*But : que le front, le back et le calculateur avancent en parallèle sans s'attendre.*
*Règle d'or : **les formats de ce document font foi**. Toute modification est annoncée à toute l'équipe avant d'être codée.*

---

## 1. Les trois briques

```
┌──────────────┐   REST/JSON   ┌───────────────────────────────┐  JSON in/out  ┌──────────────┐
│    FRONT     │ ────────────► │             BACK              │ ────────────► │ CALCULATEUR  │
│              │               │                               │               │              │
│ question     │               │ API                           │               │ exclusions   │
│ dépôt docs   │ ◄──────────── │ ETL : texte → faits (Mistral) │ ◄──────────── │ scores       │
│ faits à      │               │ base : fiches de décisions    │               │ probabilité  │
│ confirmer    │               │ cas clients                   │               │ fait pivot   │
│ résultat     │               │ (option) serveur MCP          │               │ explications │
└──────────────┘               └───────────────────────────────┘               └──────────────┘
                                         ▲
                                         │ lit
                                 ┌───────┴────────┐
                                 │ GRILLE DE      │  ← fichier partagé, source de vérité
                                 │ FACTEURS       │    (juriste)
                                 └────────────────┘
```

| Brique | Responsable | Rôle | Ne fait **pas** |
|---|---|---|---|
| **Front** | [dev front] | Saisie du cas, dépôt de documents, confirmation des faits, affichage du résultat (balance, matrice, cases à cocher) | Aucun calcul, aucun appel à Mistral |
| **Back** | [dev back] | API, extraction des faits (ETL), stockage des décisions et des cas, appel du calculateur, serveur MCP en option | Aucune logique de pondération |
| **Calculateur** | Mathis | Fonction pure : reçoit des faits et des décisions, renvoie la position, le pivot et les explications. Évaluation statistique. | Aucun appel réseau, aucun LLM, aucun stockage |
| **Grille et corpus** | [juriste / ops, sinon partagé] | Liste des facteurs, choix des décisions, relecture des fiches extraites | — |

**Choix d'architecture :** le calculateur est une **librairie Python appelée directement par le back**, pas un service séparé. C'est un service de moins à déployer. Comme il prend du JSON en entrée et renvoie du JSON, il peut devenir un service plus tard sans rien changer.

---

## 2. Ce qui manquait au schéma de départ

1. **La grille de facteurs est un contrat partagé.** Le back s'en sert pour extraire, le calculateur pour pondérer, le front pour afficher les libellés. Un seul fichier, une seule version.
2. **Trois valeurs, pas deux : `true` / `false` / `null`.** `null` veut dire « on ne sait pas ». C'est différent de `false` : « sanction inconnue » n'est pas « pas de sanction ». C'est même le point de départ de la démo.
3. **Le calculateur a besoin des décisions, pas seulement du cas.** Le back lui envoie les faits du cas **et** les fiches des décisions (avec leurs faits, leur solution, leur juridiction, leur date).
4. **Deux types de documents déposés :**
   - des documents **du client** (contrat, échanges, attestations), qui servent à remplir les faits du cas ;
   - des **décisions de justice**, qui enrichissent la base.
   Le front doit demander lequel des deux, ou le back le détecte.
5. **Une étape de confirmation humaine** entre l'extraction et le calcul. Le front affiche les faits extraits avec l'extrait du texte qui les justifie, et l'avocat corrige. Pour les décisions, le juriste relit les fiches avant qu'elles ne servent au calcul.
6. **Traçabilité :** chaque fait extrait garde l'extrait du document dont il vient, et un niveau de confiance.
7. **Recalcul instantané :** cocher ou décocher un fait relance seulement le calculateur, sans LLM. Ça doit prendre moins d'une seconde.
8. **Données factices dès le départ** (section 7), pour que personne n'attende personne.
9. **Le serveur MCP** reste dans l'histoire du pitch : le back expose les mêmes fonctions en outils MCP. C'est un bonus, à faire après l'intégration.

---

## 3. Parcours complet

```
 Avocat            FRONT                    BACK                         CALCULATEUR
   │  question +     │                        │                               │
   │  documents ───► │  POST /documents ────► │ texte → faits (Mistral)       │
   │                 │  POST /cas ──────────► │ cas créé, faits extraits      │
   │                 │ ◄──── faits + extraits │                               │
   │ ◄── « confirmez │                        │                               │
   │     ces faits » │                        │                               │
   │  corrections ─► │  PATCH /cas/{id} ────► │ faits mis à jour              │
   │                 │  POST /cas/{id}/analyse►│ prépare la requête ─────────► │ calcule
   │                 │                        │ ◄──────────────── résultat ── │
   │ ◄── balance,    │ ◄────────── résultat ─ │                               │
   │     matrice     │                        │                               │
   │  coche un fait► │  POST /cas/{id}/analyse (faits modifiés) ────────────► │ recalcule (< 1 s)
   │ ◄── bascule     │ ◄──────────────────────────────────────── résultat ── │
```

---

## 4. Conventions communes

| Sujet | Règle |
|---|---|
| Noms des champs | `snake_case`, en français, sans accents |
| Identifiants de facteurs | Ceux de la grille, jamais d'autres |
| Valeur d'un fait | `true` (présent), `false` (absent), `null` (inconnu) |
| Solutions | `"salariat"` ou `"independance"` |
| Dates | ISO 8601 : `"2020-03-04"` |
| Probabilités | Nombre entre 0 et 1, deux décimales |
| ID de décision | `juridiction-date-numero`, ex. `cass-soc-2020-03-04-19-13316` |
| ID de cas | `cas_` + 8 caractères |
| Erreurs API | `{"erreur": {"code": "...", "message": "..."}}` |
| Ports | Back : 8000. Front : 5173 (ou 3000). CORS ouvert au front. |
| Secrets | `MISTRAL_API_KEY` en variable d'environnement, jamais dans le code |

---

## 5. Les contrats de données

### C0 — Grille de facteurs (`contracts/grille.json`)
Propriétaire : juriste. Lue par les trois briques.

```json
{
  "version": "1.0",
  "question": "Le travailleur de plateforme est-il lié par un contrat de travail ?",
  "solutions": ["salariat", "independance"],
  "facteurs": {
    "sanction_deconnexion": {
      "libelle": "Sanction par déconnexion ou désactivation",
      "question": "La plateforme peut-elle déconnecter ou désactiver le travailleur en cas de refus, d'annulation ou de mauvaise note ?",
      "groupe": "sanction",
      "oriente": "salariat",
      "importance": 1.0
    },
    "liberte_horaires": {
      "libelle": "Liberté de choisir ses horaires",
      "question": "Le travailleur choisit-il librement quand il se connecte ?",
      "groupe": "independance",
      "oriente": "independance",
      "importance": 0.2
    }
  }
}
```
La liste complète des 18 facteurs est dans `distinguo-workflow-tech.md`. `importance` vaut 1,0 (déterminant), 0,5, 0,2 ou 0 (neutralisé).

### C1 — Fiche de décision (produite par l'ETL du back, stockée en base)

```json
{
  "id": "cass-soc-2020-03-04-19-13316",
  "juridiction": "Cass. soc.",
  "formation": "cass",
  "date": "2020-03-04",
  "numero": "19-13.316",
  "publication": "B",
  "ressort": null,
  "dispositif": "rejet",
  "solution": "salariat",
  "textes": ["L. 1221-1", "L. 8221-6"],
  "remise_en_cause": null,
  "url": "https://www.courdecassation.fr/...",
  "statut_validation": "valide",
  "facteurs": {
    "sanction_deconnexion": {
      "valeur": true,
      "determinant": true,
      "extrait": "[exemple — recopier le passage exact de l'arrêt sur la déconnexion après refus de courses]",
      "confiance": 1.0
    },
    "liberte_horaires": {
      "valeur": true,
      "determinant": false,
      "extrait": "…le fait de pouvoir choisir ses jours et heures de travail n'exclut pas en soi…",
      "confiance": 0.8
    }
  }
}
```
- `formation` : `ass_pleniere` | `ch_mixte` | `cass` | `ca` | `premiere_instance`.
- `publication` : `R` | `B` | `inedit` | `na`.
- `solution` = solution **au fond**, pas le dispositif (une cassation peut aboutir au salariat).
- `determinant` = la juridiction s'appuie expressément sur ce fait dans sa motivation.
- `statut_validation` : `brut` (sorti de l'extraction) ou `valide` (relu). **Seules les fiches `valide` sont envoyées au calculateur.**
- Tous les facteurs de la grille sont présents dans la fiche, quitte à valoir `null`.

### C2 — Cas client (stocké par le back, affiché par le front)

```json
{
  "id": "cas_7f3a9c21",
  "question": "Mon client peut-il demander la requalification ?",
  "description": "Livreur à vélo, choisit ses créneaux, géolocalisé…",
  "ressort": "CA Paris",
  "documents": ["doc_12ab", "doc_34cd"],
  "facteurs": {
    "geolocalisation_suivi": {
      "valeur": true,
      "extrait": "l'application suit ma position pendant toute la course",
      "confiance": 1.0,
      "source": "extraction"
    },
    "sanction_deconnexion": {
      "valeur": null,
      "extrait": null,
      "confiance": 0.4,
      "source": "extraction"
    }
  },
  "a_confirmer": ["sanction_deconnexion"]
}
```
- `source` : `extraction` (vient de Mistral) ou `utilisateur` (corrigé à la main).
- `a_confirmer` : faits inconnus ou à faible confiance (< 0,6), à mettre en avant dans le front.

### C3 — Requête au calculateur (le back construit, le calculateur reçoit)

```json
{
  "grille": { "…": "contenu de C0" },
  "cas": {
    "ressort": "CA Paris",
    "textes": ["L. 1221-1", "L. 8221-6"],
    "facteurs": {
      "geolocalisation_suivi": true,
      "sanction_deconnexion": null,
      "liberte_horaires": true
    }
  },
  "decisions": [ "…fiches C1 avec statut_validation = valide…" ],
  "parametres": {
    "kappa": 2.0,
    "niveau_intervalle": 0.8,
    "date_reference": "2026-10-04"
  }
}
```
Le calculateur ne lit rien d'autre que cette requête : pas de fichier, pas de base. Avec la même requête, il donne toujours le même résultat.

### C4 — Résultat du calculateur (le calculateur produit, le back transmet tel quel au front)

```json
{
  "statut": "incertain",
  "p_salariat": 0.48,
  "intervalle": [0.29, 0.67],
  "masse": 3.1,

  "majeure": {
    "solution": "independance",
    "p": 0.52,
    "decisions": ["ca-paris-2021-...", "ca-lyon-2022-..."]
  },
  "exception": {
    "solution": "salariat",
    "si": [{ "facteur": "sanction_deconnexion", "valeur": true, "delta_p": 0.31 }],
    "decision_reference": "cass-soc-2020-03-04-19-13316"
  },
  "fait_pivot": {
    "facteur": "sanction_deconnexion",
    "valeur_cible": true,
    "delta_p": 0.31,
    "bascule": true
  },
  "impacts": [
    { "facteur": "sanction_deconnexion", "valeur_cible": true, "delta_p": 0.31, "bascule": true },
    { "facteur": "geolocalisation_suivi", "valeur_cible": false, "delta_p": -0.12, "bascule": false }
  ],

  "decisions": [
    {
      "id": "cass-soc-2020-03-04-19-13316",
      "solution": "salariat",
      "retenue": true,
      "motif_exclusion": null,
      "score": 0.61,
      "proximite": 0.72,
      "poids": { "autorite": 0.85, "portee": 0.8, "dispositions": 1.0, "actualite": 0.58, "geographie": 1.0 },
      "alignement": {
        "geolocalisation_suivi": "identique",
        "sanction_deconnexion": "inconnu",
        "liberte_horaires": "identique"
      }
    },
    {
      "id": "ca-xxx-2019-...",
      "solution": "independance",
      "retenue": false,
      "motif_exclusion": "Fait déterminant divergent : Géolocalisation en temps réel",
      "score": 0.0,
      "proximite": 0.35,
      "poids": { "autorite": 0.5, "portee": 0.3, "dispositions": 1.0, "actualite": 0.5, "geographie": 0.5 },
      "alignement": { "…": "…" }
    }
  ],

  "avertissements": [
    "Directive (UE) 2024/2831 : présomption légale de salariat — vérifier la transposition"
  ]
}
```
- `statut` : `salariat` | `independance` | `incertain`.
- `alignement` : `identique` | `oppose` | `inconnu`. C'est ce qui remplit **directement la matrice du front**.
- Le détail de chaque décision est inclus dans le résultat, donc il n'y a pas d'appel séparé pour « expliquer le score » : le front l'affiche au clic.
- `impacts` alimente les cases à cocher : le front peut indiquer à côté de chaque fait l'effet qu'aurait son inversion.

---

## 6. API du back (pour le front)

| Méthode | Route | Entrée | Sortie |
|---|---|---|---|
| GET | `/sante` | — | `{"ok": true}` |
| GET | `/grille` | — | C0 |
| GET | `/decisions` | — | Liste de C1 (résumé : id, juridiction, date, solution, statut_validation) |
| GET | `/decisions/{id}` | — | C1 complet |
| POST | `/documents` | Fichier (PDF, TXT, DOCX) + `type` : `cas` ou `decision` | `{"document_id", "type", "statut"}`. Pour une décision, l'extraction lance la création d'une fiche `brut`. |
| POST | `/cas` | `{"question", "description", "ressort", "document_ids"}` | C2 (faits extraits) |
| PATCH | `/cas/{id}` | `{"facteurs": {"sanction_deconnexion": true}}` | C2 mis à jour, `source` = `utilisateur` |
| POST | `/cas/{id}/analyse` | Optionnel : `{"facteurs": {...}}` pour **simuler** sans enregistrer | C4 |

- **Délais :** `POST /cas` et `POST /documents` appellent Mistral, donc comptent 10 à 30 secondes. Le front affiche un chargement. `POST /cas/{id}/analyse` est instantané.
- Le simulateur (cases à cocher) utilise `POST /cas/{id}/analyse` avec des faits modifiés : rien n'est enregistré tant que l'avocat ne valide pas.

---

## 7. Travailler en parallèle : les données factices

Dès le début, on crée un dossier `contracts/exemples/` avec un exemple réaliste de chaque format :

| Fichier | Sert à |
|---|---|
| `grille.json` | Tout le monde |
| `fiches/*.json` (4 à 5 décisions fictives mais plausibles) | Calculateur (tests), back (base de départ) |
| `cas_exemple.json` | Front (écran des faits), back |
| `requete_calcul_exemple.json` | Calculateur (entrée de test) |
| `resultat_exemple.json` + `resultat_apres_bascule.json` | Front (écran résultat et bascule), back (faux calculateur) |

Chacun démarre sur les exemples :
- **Front :** branché sur les fichiers d'exemple, sans back. Bascule sur la vraie API à l'intégration.
- **Back :** un faux calculateur qui renvoie `resultat_exemple.json`, remplacé par le vrai à l'intégration.
- **Calculateur :** teste sur les fiches d'exemple, puis sur les vraies fiches dès que l'ETL les produit.

---

## 8. Le détail de chaque brique

### Front
1. **Saisie :** question, description libre, ressort, dépôt de documents (en précisant client ou décision).
2. **Faits du cas :** liste des facteurs avec leur valeur, l'extrait et la confiance. Les faits à confirmer sont en évidence. L'avocat corrige, puis lance l'analyse.
3. **Résultat :**
   - la **balance** (probabilité, intervalle, statut) ;
   - la **matrice** faits × décisions, regroupées par camp, écartées grisées, fait pivot surligné ;
   - les **cases à cocher** pour simuler (recalcul en direct) ;
   - au clic sur une décision : détail du score et motif d'exclusion.
4. **Corpus** (optionnel) : liste des décisions et de leur statut de validation.

### Back
1. **API** de la section 6.
2. **ETL :**
   - texte du document (PDF : extraction de texte, ou Mistral OCR pour les scans) ;
   - extraction des faits selon la grille par Mistral (plusieurs passages et vote pour mesurer la confiance), avec extrait obligatoire ;
   - pour les décisions : métadonnées, solution au fond, faits déterminants, avec les règles de lecture des arrêts en « attendu que » (avant 2019) ;
   - contrôle du format, puis stockage.
3. **Stockage :** fichiers JSON ou SQLite, au choix du back. Le format exposé reste C1 et C2.
4. **Appel du calculateur :** construit C3 à partir du cas et des fiches validées, renvoie C4 sans le modifier.
5. **(Bonus) Serveur MCP :** les mêmes fonctions exposées en outils, pour la démo dans Le Chat.

### Calculateur
1. **Exclusions :** fait déterminant contraire, solution remise en cause.
2. **Score** de chaque décision : proximité des faits × poids (autorité, publication, textes, ancienneté, ressort).
3. **Probabilité** par vote pondéré, avec intervalle et statut « incertain ».
4. **Fait pivot** et impacts : chaque fait inversé un par un.
5. **Alignement** fait par fait, pour la matrice.
6. **Évaluation** (script à part) : retirer chaque décision tour à tour, comparer à Mistral seul et à la solution majoritaire, choisir `kappa`.

---

## 9. Organisation du dépôt

```
distinguo/
├── contracts/          ← formats + exemples (modifiés uniquement après accord)
│   ├── grille.json
│   └── exemples/
├── front/
├── back/
├── calculateur/        ← package Python importé par le back
├── data/
│   ├── decisions/      ← textes bruts
│   └── fiches/         ← fiches extraites puis validées
└── README.md
```
- Une branche par personne, fusion sur `main` à chaque point d'intégration.
- Personne ne modifie le dossier d'un autre sans le prévenir.

---

## 10. Jalons communs

| Jalon | Quand | Ce qui doit être prêt |
|---|---|---|
| **J0 — Contrats figés** | dans 30 min | Ce document validé, `contracts/` et les exemples créés |
| **J1 — Chacun tourne seul** | J0 + 1h30 | Front sur les exemples ; back qui extrait une vraie décision ; calculateur qui produit C4 sur les fiches d'exemple |
| **J2 — Intégration back ↔ calculateur** | J0 + 2h30 | `POST /cas/{id}/analyse` renvoie un vrai résultat |
| **J3 — Bout en bout** | J0 + 3h30 | Front branché sur le back, vraies fiches validées, scénario de démo qui tourne |
| **Gel** | 17h00 | Plus de nouvelle fonctionnalité. Captures et vidéo de secours. |
| **Soumission** | 18h00 | — |

Un point de 5 minutes à chaque jalon : ce qui marche, ce qui bloque, ce qui change.

---

## 11. Points à trancher maintenant

- [ ] Qui joue le rôle de juriste (grille, choix du corpus, relecture des fiches) ?
- [ ] Le back est-il en Python ? Si non, le calculateur devient un petit service HTTP, avec le même JSON.
- [ ] Le front détecte-t-il le type de document, ou l'utilisateur le choisit-il ? (Recommandé : l'utilisateur choisit.)
- [ ] Fichiers JSON ou SQLite pour le stockage ?
- [ ] Le serveur MCP est-il dans la démo, ou seulement mentionné dans le pitch ?
