# pivot — contexte du projet

*Projet du LLM x Law Hackathon Paris #2 (Mistral AI × Stanford Law School).*
*Ancien nom : Distinguo. On le retrouve encore dans `docs/pitch.md`, `docs/spec-back.md` et `docs/architecture-contrats.md`.*

## Le but

**pivot départage une jurisprudence contradictoire.** Les outils de recherche trouvent les précédents. pivot dit à l'avocat de quel côté penche son dossier, avec quelle certitude, et **quel fait manquant changerait la réponse**.

> **Le LLM extrait, le code décide.** Mistral lit les documents et les décisions. Un moteur déterministe et testé fait la pesée. Chaque chiffre affiché renvoie à un fait, une décision et un extrait cité.

## Le problème

Certains domaines du droit se jugent sur un **faisceau d'indices**. Exemple : la requalification des travailleurs de plateformes. Sur des faits très proches, un avocat trouve des arrêts qui concluent au salariat et d'autres à l'indépendance.

- **Aujourd'hui**, un collaborateur senior passe des jours à lire ces décisions, à annoter les faits et à repérer le *fait pivot* qui a fait basculer chaque solution. C'est lent, coûteux et non reproductible.
- **Un LLM seul** résume les décisions en liste plate. Il ne pèse pas leur autorité, ne dit pas lesquelles s'appliquent au cas et ne chiffre pas le risque.

## Ce que voit l'avocat

1. **Une tendance** : par exemple *Indépendance 65 %*, avec son intervalle à 95 %, marquée *Incertaine* et *Provisoire*.
2. **Les questions à poser à la data room** : les faits inconnus qui feraient basculer l'issue, classés par impact (« La plateforme peut-elle suspendre un compte pour refus ? Si oui 63 % salariat · si non 15 % »).
3. **La bascule** : répondre *Oui* fait bouger la balance en direct. Les précédents qui ne s'appliquent plus sont écartés, avec le motif.
4. **Les preuves** : pour chaque fait et chaque décision, l'extrait verbatim sur lequel il repose.

## Le cas de démo

Une seule question de droit, volontairement étroite : **un travailleur de plateforme est-il salarié en droit français ?**

| | |
|---|---|
| **Corpus** | 12 arrêts de la Cour de cassation (2018–2025), textes officiels : 9 pour le salariat, 3 pour l'indépendance |
| **Grille** | 18 facteurs (15 actifs, 3 neutralisés) : géolocalisation, désactivation de compte, tarif imposé, liberté de travailler pour des concurrents… |
| **Scénario** | Due diligence M&A sur *UrbanShift*, plateforme de livraison à vélo (5 000 coursiers micro-entrepreneurs). Prompt et pièces jointes dans [`docs/demo/demo.md`](demo/demo.md) |

La question de démo est un exemple. Ce qui lui est propre tient en deux endroits : `contracts/grille.json` (les facteurs) et `data/fiches/` (les décisions validées). Pour une nouvelle question (rupture brutale, clause de non-concurrence, amendes RGPD…), un juriste écrit la grille, `back.ingerer` extrait les décisions, un relecteur les valide. Le code ne change pas.

## Ce qu'on vend

Le dashboard est la vitrine de la démo. **Le produit est le moteur d'arbitrage**, exposé via un serveur MCP (`pivot_structurer_cas`, `pivot_etat_du_droit`, `pivot_arbitrer`). Un cabinet ne s'équipe pas d'une nouvelle application : Le Chat, Harvey ou l'outil interne du cabinet appellent pivot dès qu'une question porte sur un risque jurisprudentiel.

| Valeur | Concrètement |
|---|---|
| Temps | Des jours de lecture comparée ramenés à quelques minutes |
| Rigueur | Résultat reproductible, auditable facteur par facteur, sans hallucination dans la pesée |
| Conseil | « Modifiez cette clause et le risque s'effondre » : le fait pivot devient un levier de structuration |
| Intégration | MCP : on améliore les outils existants au lieu d'en imposer un |

## Comment ça marche

```
 front (Next.js)  ──REST──►  back (FastAPI)  ──────────►  calculateur (Python)
 prompt + pièces             lit TXT/PDF/DOCX             écarte les précédents dont un fait
 dashboard                   Mistral extrait les faits     déterminant est contraire au cas
 simulation « et si »        stocke cas et décisions      régression logistique bayésienne,
                             serveur MCP                   a priori = grille du juriste
                                                          pivots, exception, lecture a fortiori
          un seul format JSON de bout en bout : le « dossier » (contracts/)
```

| Brique | Rôle | Ne fait pas |
|---|---|---|
| **Front** | Saisie du cas, dépôt de documents, confirmation des faits, affichage du dossier complété | Aucun calcul, aucun appel à Mistral |
| **Back** | API, extraction des faits, stockage, construction du dossier, serveur MCP | Aucune pondération |
| **Calculateur** | Fonction pure `completer(dossier) → dossier` qui remplit le bloc `resultat` | Aucun réseau, aucun LLM, aucun stockage |

Règles qui tiennent l'ensemble :

- **`contracts/` fait foi.** Schéma, grille, validateur et exemples. Tout changement de format est annoncé à l'équipe.
- **Un fait vaut `true`, `false` ou `null`.** `null` veut dire « on ne sait pas », ce qui est différent de `false`. La démo part justement d'un fait inconnu.
- **La sortie du LLM n'est jamais crue telle quelle.** Chaque extrait cité est vérifié dans le texte source. Un fait sans extrait vérifié retourne à l'avocat pour confirmation.
- **Déterministe et rapide.** Même dossier, même résultat. Une analyse prend environ 30 ms, donc les simulations sont instantanées.
- **Deux relectures humaines.** L'avocat confirme les faits du cas. Un juriste valide chaque décision avant qu'elle n'entre dans le corpus.

## Hors périmètre du hackathon

- **Source de jurisprudence en direct.** Le corpus est fermé : l'export de recherche Legora (`dataset-legora/`) et les textes officiels. Brancher pivot sur Legora (export remplacé par un flux, ou échange via MCP) est la première chose à construire ensuite. *Legora cherche, pivot arbitre.*
- **Autres questions de droit.** L'architecture les permet, la démo n'en montre qu'une.

## Limites assumées

- Les 12 décisions ont été relues par des relecteurs IA indépendants face aux textes officiels (trace dans `data/revues/`), pas encore par un avocat en exercice.
- Petit corpus : les intervalles restent larges. Les scores sont des estimations pondérées par les preuves, pas des probabilités calibrées.
- L'extraction lit ce que disent les documents. Le juge regarde comment la relation fonctionne en pratique.

## Vocabulaire

| Terme | Sens |
|---|---|
| **Dossier** | Le format JSON unique : `meta`, `grille`, `cas`, `decisions`, `parametres`, `resultat` |
| **Grille** | Les facteurs d'une question de droit, avec leur orientation et leur importance |
| **Fait pivot** | Fait inconnu ou modifiable dont la valeur fait basculer l'issue |
| **Écarter** (distinguer) | Exclure un précédent dont un fait déterminant est contraire au cas |
| **A fortiori** | Une décision s'applique a fortiori si le cas a tous ses arguments, et aucun argument contraire de plus |
| **À confirmer** | Faits inconnus ou de confiance < 0,6, mis en avant pour l'avocat |

## Pour aller plus loin

- [README](../README.md) : lancement en local, vérifications, organisation du dépôt
- [Architecture et contrats](architecture-contrats.md) : format du dossier, API, modèle du calculateur
- [Spec back](spec-back.md) · [Notes de pitch](pitch.md)
- [AGENTS.md](../AGENTS.md) : conventions du front
