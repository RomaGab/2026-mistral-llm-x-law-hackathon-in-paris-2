"""Lecture des décisions : exclusion, poids, proximité, alignement, a fortiori.

Tout est déterministe et ne dépend que du dossier (pas d'horloge, pas de réseau).
"""
import math
from datetime import date

AUTORITE = {"ass_pleniere": 1.0, "ch_mixte": 1.0, "cass": 0.85, "ca": 0.5, "premiere_instance": 0.25}
PORTEE = {"R": 1.0, "B": 0.8, "inedit": 0.4, "na": 0.3}

# ---- système juridique (v1.4) : coefficient MULTIPLICATIF sur le poids d'une décision
PAYS_DEFAUT = "France"
TRADITIONS = {
    **dict.fromkeys(["Royaume-Uni", "États-Unis", "Australie", "Canada", "Irlande", "Nouvelle-Zélande", "Inde"], "common_law"),
    **dict.fromkeys(["France", "Espagne", "Italie", "Pays-Bas", "Suisse", "Belgique", "Allemagne", "Portugal",
                     "Luxembourg", "Autriche", "Brésil", "Chili", "Colombie", "Argentine", "Québec"], "civil_law"),
    "Union européenne": "union_europeenne",
}
MEMBRES_UE = {"France", "Espagne", "Italie", "Pays-Bas", "Belgique", "Allemagne", "Portugal", "Luxembourg", "Autriche", "Irlande"}
ALIAS = {"USA": "États-Unis", "Etats-Unis": "États-Unis", "UK": "Royaume-Uni", "CJUE": "Union européenne", "UE": "Union européenne"}
SYSTEME = {"meme_pays": 1.0, "droit_ue": 0.6, "meme_tradition": 0.35, "autre_tradition": 0.08}


def pays(obj: dict) -> str:
    """Pays d'un cas ou d'une décision, normalisé (« France » si absent)."""
    p = (obj.get("pays") or PAYS_DEFAUT).strip()
    return ALIAS.get(p, p)


def systeme_juridique(cas: dict, decision: dict) -> float:
    """Même pays : ×1. CJUE pour un pays membre : ×0,6. Même tradition : ×0,35. Tradition opposée
    (common law contre civil law, ou pays inconnu) : ×0,08."""
    pc, pd = pays(cas), pays(decision)
    if pc == pd:
        return SYSTEME["meme_pays"]
    if pd == "Union européenne" and pc in MEMBRES_UE:
        return SYSTEME["droit_ue"]
    tc, td = TRADITIONS.get(pc), TRADITIONS.get(pd)
    if tc is not None and tc == td:
        return SYSTEME["meme_tradition"]
    return SYSTEME["autre_tradition"]


class Grille:
    """Vue pratique sur dossier["grille"]."""

    def __init__(self, grille: dict):
        self.ids = [f["id"] for f in grille["facteurs"]]
        self.rang = {i: k for k, i in enumerate(self.ids)}
        self.importance = {f["id"]: f["importance"] for f in grille["facteurs"]}
        self.oriente = {f["id"]: f["oriente"] for f in grille["facteurs"]}
        self.libelle = {f["id"]: f["libelle"] for f in grille["facteurs"]}
        self.actifs = [i for i in self.ids if self.importance[i] > 0]


def exclusion(faits: dict, decision: dict, g: Grille) -> str | None:
    """Motif d'exclusion de la décision pour ce jeu de faits, ou None si elle est retenue."""
    if decision.get("remise_en_cause"):
        return f"Solution remise en cause : {decision['remise_en_cause']}"
    for k in decision["determinants"]:
        v = faits[k]
        if g.importance[k] > 0 and v is not None and v != decision["facteurs"][k]:
            return f"Fait déterminant divergent : {g.libelle[k]}"
    return None


def detail_poids(cas: dict, decision: dict, date_reference: str) -> dict:
    age = (date.fromisoformat(date_reference) - date.fromisoformat(decision["date"])).days / 365.25
    geo = 1.0 if decision["ressort"] is None or decision["ressort"] == cas["ressort"] else 0.5
    return {
        "autorite": AUTORITE[decision["formation"]],
        "portee": PORTEE[decision["publication"]],
        "actualite": round(math.exp(-max(age, 0.0) / 10), 2),
        "geographie": geo,
        "systeme_juridique": systeme_juridique(cas, decision),
    }


def poids(dp: dict) -> float:
    base = 0.5 * dp["autorite"] + 0.2 * dp["portee"] + 0.15 * dp["actualite"] + 0.15 * dp["geographie"]
    return round(base * dp.get("systeme_juridique", 1.0), 2)


def proximite(faits: dict, decision: dict, g: Grille) -> float:
    """Part des faits (pondérés par importance) identiques ; un fait inconnu d'un côté compte pour moitié."""
    num = den = 0.0
    for i in g.actifs:
        a, b = faits[i], decision["facteurs"][i]
        num += g.importance[i] * (0.5 if a is None or b is None else float(a == b))
        den += g.importance[i]
    return round(num / den, 2) if den else 0.0


def alignement(faits: dict, decision: dict, g: Grille) -> dict:
    out = {}
    for i in g.ids:
        a, b = faits[i], decision["facteurs"][i]
        out[i] = "inconnu" if a is None or b is None else ("identique" if a == b else "oppose")
    return out


def litteraux(faits: dict, g: Grille) -> dict:
    """Faits connus et non neutralisés, rangés par camp : True = favorise l'issue vraie."""
    camps = {True: [], False: []}
    for f in g.actifs:
        v = faits[f]
        if v is not None:
            camps[g.oriente[f] if v else not g.oriente[f]].append({"facteur": f, "valeur": v})
    return camps


def a_fortiori(faits: dict, decision: dict, g: Grille) -> dict:
    """Lecture précédent par précédent (result model ; cf. Morello et al., JURIX 2025)."""
    X, P, s = litteraux(faits, g), litteraux(decision["facteurs"], g), decision["issue"]
    manquants = [l for l in P[s] if l not in X[s]]
    contraires = [l for l in X[not s] if l not in P[not s]]
    return {
        "s_applique_a_fortiori": not manquants and not contraires,
        "arguments_manquants": manquants,
        "arguments_contraires": contraires,
    }
