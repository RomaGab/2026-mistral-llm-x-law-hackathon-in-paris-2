"""Serveur MCP « pivot » pour l'agent Mistral (Le Chat). Cf. SPEC-back.md, « Outils MCP », et prompt_agent.md.

    uv run --env-file .env python -m back.serveur_mcp          # → http://127.0.0.1:8001/mcp

Les outils appellent service.py directement et renvoient un RÉSUMÉ (libellés, pourcentages entiers),
pas le dossier complet : le LLM extrait, le code décide. Tout chiffre vient de `resultat`.
"""
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from back import service
from back.service import Erreur

mcp = MCPServer(
    "pivot",
    instructions="Moteur d'arbitrage jurisprudentiel Pivot : structurer un cas, consulter l'état du droit, arbitrer.",
)


def _pct(x: float) -> int:
    return round(100 * x)


def _oui_non(v: bool | None) -> str:
    return "Inconnu" if v is None else ("Oui" if v else "Non")


def _sur_erreur(fonction, *args, **kwargs):
    """Une erreur métier devient un message lisible par l'agent. ToolError : mcp 2.x masque les autres exceptions."""
    try:
        return fonction(*args, **kwargs)
    except Erreur as e:
        raise ToolError(f"{e.code} : {e.message}") from e


def resumer(dossier: dict) -> dict:
    """Résumé de pivot_arbitrer : rien que des valeurs lues dans le dossier complété."""
    g = dossier["grille"]
    r = dossier["resultat"]
    libelle = {f["id"]: f["libelle"] for f in g["facteurs"]}
    question = {f["id"]: f["question"] for f in g["facteurs"]}
    issue_libelle = {True: g["issue"]["si_vrai"], False: g["issue"]["si_faux"]}
    intitule = {d["id"]: d["intitule"] for d in dossier["decisions"]}
    cas = dossier["cas"]["facteurs"]
    p = r["prediction"]["probabilite"]
    lo, hi = r["prediction"]["intervalle"]
    maj = r["majeure"]
    analyse = r["facteurs"]

    def fait(f: str) -> dict:
        return {"id": f, "libelle": libelle[f],
                "probabilite_salariat_si_oui": _pct(analyse[f]["probabilite_si_vrai"]),
                "probabilite_salariat_si_non": _pct(analyse[f]["probabilite_si_faux"])}

    manquants = [f for f in r["pivots"] if analyse[f]["type"] == "a_documenter"]
    leviers = []
    for f, a in analyse.items():
        if a["type"] != "levier" or a["niveau"] == "neutralise":
            continue
        nouveau = a["probabilite_si_faux"] if cas[f] else a["probabilite_si_vrai"]
        leviers.append((abs(nouveau - p), f, nouveau))
    leviers.sort(key=lambda x: -x[0])

    exception = r["exception"]
    return {
        "cas_id": dossier["cas"]["id"],
        "hypothese": dossier["meta"]["simulation"],
        "position_majeure": {
            "libelle": issue_libelle[maj["issue"]],
            "probabilite": _pct(maj["probabilite"]),
            "intervalle": [_pct(lo), _pct(hi)] if maj["issue"] else [_pct(1 - hi), _pct(1 - lo)],
            "incertain": r["prediction"]["incertain"],
        },
        "probabilite_salariat": _pct(p),
        "indice_liceite": _pct(1 - p),
        "definitif": not manquants,
        "faits_manquants": [{**fait(f), "question": question[f]} for f in manquants],
        "decisions_retenues": {
            "nombre": sum(1 for x in r["decisions"] if x["retenue"]),
            "majeure": [intitule[i] for i in maj["decisions"]],
        },
        "decisions_ecartees": [{"intitule": intitule[x["id"]], "motif": x["motif_exclusion"]}
                               for x in r["decisions"] if not x["retenue"]],
        "pivots": [fait(f) for f in r["pivots"]],
        "pivots_combines": [
            {"faits": [{"id": f, "libelle": libelle[f], "valeur": _oui_non(v)} for f, v in zip(c["facteurs"], c["valeurs"])],
             "probabilite_salariat": _pct(c["probabilite_si"])}
            for c in r["pivots_combines"]
        ],
        "exception": None if exception is None else {
            "libelle": issue_libelle[exception["issue"]],
            "probabilite": _pct(exception["probabilite"]),
            "conditions": [{"id": c["facteur"], "libelle": libelle[c["facteur"]], "valeur": _oui_non(c["valeur"]),
                            "probabilite_salariat": _pct(c["probabilite_si"])} for c in exception["conditions"]],
            "decision_reference": intitule.get(exception["decision_reference"]),
        },
        "leviers": [{"id": f, "libelle": libelle[f], "valeur_actuelle": _oui_non(cas[f]),
                     "valeur_testee": _oui_non(not cas[f]),
                     "probabilite_salariat": _pct(nouveau), "indice_liceite": _pct(1 - nouveau)}
                    for _, f, nouveau in leviers[:3]],
        "avertissements": r["avertissements"],
    }


@mcp.tool()
def pivot_structurer_cas(description: str, pieces: list[str] | None = None, ressort: str | None = None) -> dict:
    """Crée le cas : extrait les faits (Oui / Non / Inconnu, avec l'extrait qui les justifie) de la description
    et des pièces. `pieces` : un texte par pièce, passages recopiés MOT POUR MOT (le moteur ne voit pas les fichiers).
    `ressort` : cour d'appel du client, ex. « CA Paris ». Renvoie cas_id, les faits et ceux à confirmer."""
    cas = _sur_erreur(service.creer_cas, description, ressort, None, None, pieces)
    g = service.grille()["facteurs"]
    preuves = cas.get("preuves", {})
    return {
        "cas_id": cas["id"],
        "faits": [{"id": f["id"], "libelle": f["libelle"], "valeur": _oui_non(cas["facteurs"][f["id"]]),
                   "extrait": (preuves.get(f["id"]) or {}).get("extrait")} for f in g],
        "a_confirmer": [{"id": f["id"], "libelle": f["libelle"], "question": f["question"]}
                        for f in g if f["id"] in cas["a_confirmer"]],
    }


@mcp.tool()
def pivot_etat_du_droit() -> dict:
    """La grille d'analyse (facteurs du faisceau d'indices, avec leur question) et les décisions validées du corpus."""
    g = service.grille()
    sens = {True: g["issue"]["si_vrai"], False: g["issue"]["si_faux"], None: "neutre"}
    return {
        "question": g["question"],
        "grille": [{"id": f["id"], "libelle": f["libelle"], "question": f["question"],
                    "sens": sens[f["oriente"]], "importance": f["importance"]} for f in g["facteurs"]],
        "corpus": [{"intitule": d["intitule"], "formation": d["formation"],
                    "issue": g["issue"]["si_vrai"] if d["issue"] else g["issue"]["si_faux"]}
                   for d in service.lister("fiches") if d.get("validee") is True],
    }


@mcp.tool()
def pivot_arbitrer(cas_id: str, faits: dict[str, bool | None] | None = None, hypothese: bool = False) -> dict:
    """Calcule le score du cas. `faits` = {identifiant_facteur: true | false} confirmés par l'avocat : ils sont
    ENREGISTRÉS. Avec `hypothese: true`, simulation : rien n'est enregistré. Probabilités en pourcentage entier."""
    if faits and not hypothese:
        _sur_erreur(service.modifier_cas, cas_id, faits)
        dossier = _sur_erreur(service.analyser, cas_id)
    else:
        dossier = _sur_erreur(service.analyser, cas_id, faits if faits else None)
    return resumer(dossier)


if __name__ == "__main__":
    mcp.run("streamable-http", host="127.0.0.1", port=8001)
