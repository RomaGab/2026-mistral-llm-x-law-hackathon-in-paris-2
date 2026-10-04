# Plan : Back Distinguo

Spec validé : [SPEC-back.md](../SPEC-back.md). Tâches détaillées (critères, vérifs, fichiers) : [todo.md](todo.md).

## Vue d'ensemble

On livre un chemin de bout en bout à chaque phase, pas une couche à la fois. On attaque d'abord ce qui peut faire échouer la démo : l'extraction d'une **vraie** décision par Mistral (J1), puis le MCP, qui est obligatoire en démo. Le vrai calculateur arrive quand Mathis le livre. D'ici là, le faux calculateur garde toutes les routes fonctionnelles, sans aucune attente.

## Décisions d'architecture

- **`service.py` est le seul cœur.** `api.py` et `serveur_mcp.py` ne sont que des adaptateurs : un outil MCP n'appelle jamais l'API en HTTP.
- **`extraction.appeler_mistral` est le seul point réseau.** Les tests le remplacent par `monkeypatch`, donc tous tournent sans clé.
- **Le juge de paix est `contracts.valider.erreurs_dossier`.** Le back n'a pas sa propre validation du dossier.
- **Le faux calculateur s'active de lui-même** quand le package `calculateur` est absent. Brancher le vrai ne demande aucune modification du back.
- **Les données de test** sont le cas et les 5 décisions fictives de `contracts/exemples/dossier_entree.json`, chargées dans un `DISTINGUO_DATA` temporaire.

## Graphe de dépendances

```
T1 socle
 ├── T2 vraie décision → fiche ─┬── T5 OCR PDF/DOCX ─────────────┐
 │                              ├── T6 relecture juriste ────────┤
 │                              └── T7 créer un cas ──┐          ├── T11 corpus réel
 └── T3 analyse ── T4 PATCH cas ──────────────────────┤          │
        │                                             └── T8 MCP local ── T9 MCP depuis Le Chat
        └── T10 vrai calculateur (dès que Mathis livre)
                                         tout ──► T12 répétition de la démo
```

## Phases

| Phase | Tâches | Sortie |
|---|---|---|
| 1. J1 : socle, vraie décision, analyse | T1 → T2 → T3 → T4 | Une vraie décision extraite donne un dossier valide ; l'analyse et la simulation marchent avec le faux calculateur |
| 2. Parcours du front | T5, T6, T7 | Toutes les routes du §7 répondent |
| 3. MCP | T8 → T9 | Les 3 outils `pivot_*` marchent depuis l'agent Mistral dans Le Chat |
| 4. J2/J3 : vrai calculateur, vrai corpus, démo | T10, T11, T12 | Scénario de démo de bout en bout sur de vraies décisions |

Un checkpoint en fin de phase : `uv run pytest` vert, commit, push, 5 minutes avec l'équipe.

**T10 n'a pas de place fixe :** dès que Mathis livre `calculateur/`, il passe devant la tâche en cours. Tant qu'il n'a pas livré, rien n'est bloqué.

## Risques

| Risque | Impact | Parade |
|---|---|---|
| Corpus déséquilibré : 6 arrêts de cassation français, dont 5 pour le salariat et 1 pour l'indépendance (Voxtur 2022), aucune cour d'appel | Haut | Sans contrepoids, presque tous les cas sortent « salariat », et la démo de jurisprudence contradictoire tombe à plat. T11 : ajouter à la main des arrêts de cour d'appel qui retiennent l'indépendance (objectif : environ 15 décisions, dont au moins 5 côté indépendance). Le calculateur signale aussi le déséquilibre dans `avertissements`. |
| Mistral renvoie un JSON non conforme ou invente des extraits | Moyen | JSON mode, `temperature=0`, normalisation stricte (testée) ; la fiche n'entre dans un dossier qu'après relecture du juriste. |
| Latence ou quota Mistral pendant l'ingestion | Moyen | L'ingestion saute les fiches déjà extraites et ne coûte qu'une fois ; `--limite` pour les essais. |
| Le Chat n'arrive pas à se connecter au MCP (URL publique, auth) | Haut | T8 est d'abord validé avec l'Inspector en local ; T9 est fait tôt. En repli, Claude Desktop ou l'Inspector en démo, plus la vidéo enregistrée avant le gel. |
| Le calculateur est en retard ou ses dépendances entrent en conflit | Moyen | Le faux calculateur garde la démo fonctionnelle ; T10 est isolé. |
| Mistral OCR ne lit pas les DOCX | Faible | Vérifié au début de T5 ; sinon, DOCX → 400. |

## Questions ouvertes (reprises du spec)

1. ~~Format du dataset Legora~~ Réglé (TXT + tableau de synthèse JSON ; les juridictions étrangères sont exclues). Corpus constitué à la main.
2. ~~Client MCP de la démo~~ Réglé : agent Mistral dans Le Chat (prompt « Agent Stratégique Pivot »). Reste à vérifier l'authentification du connecteur (T9).
3. `pyproject.toml` racine partagé : à annoncer à Mathis avant de pousser T1.
4. Lecture des DOCX par Mistral OCR. Réglé dans T5.
