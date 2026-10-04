"""API REST pour le front (§7 du contrat). Lancer : uv run uvicorn back.api:app --reload --port 8000"""
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictBool
from starlette.exceptions import HTTPException

from back import service
from back.service import Erreur


class CorpsFacteurs(BaseModel):
    # StrictBool : "oui", 1 ou "true" sont refusés (400), seuls true / false / null passent.
    facteurs: dict[str, StrictBool | None]

app = FastAPI(title="Pivot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # démo locale


def _erreur(statut: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"erreur": {"code": code, "message": message}}, status_code=statut)


@app.exception_handler(Erreur)
def _erreur_metier(_, e: Erreur):
    return _erreur(e.statut, e.code, e.message)


@app.exception_handler(HTTPException)
def _erreur_http(_, e: HTTPException):
    return _erreur(e.status_code, "introuvable" if e.status_code == 404 else "http", str(e.detail))


@app.exception_handler(RequestValidationError)
def _requete_invalide(_, e: RequestValidationError):
    # Dans le contrat, 422 est réservé au validateur du dossier : un corps mal formé est un 400.
    details = "; ".join(f"{'/'.join(map(str, x['loc']))} : {x['msg']}" for x in e.errors())
    return _erreur(400, "requete_invalide", details)


@app.get("/sante")
def sante():
    return {"ok": True}


@app.get("/grille")
def grille():
    return service.grille()


@app.get("/cas/{cas_id}")
def lire_cas(cas_id: str):
    return service.lire("cas", cas_id)


@app.patch("/cas/{cas_id}")
def modifier_cas(cas_id: str, corps: CorpsFacteurs):
    return service.modifier_cas(cas_id, corps.facteurs)


@app.post("/cas/{cas_id}/analyse")
def analyser(cas_id: str, corps: CorpsFacteurs | None = None):
    """Dossier complété. Avec {"facteurs": {...}} : simulation, rien n'est enregistré."""
    return service.analyser(cas_id, corps.facteurs if corps else None)


@app.get("/decisions")
def lister_decisions():
    return service.lister("fiches")


@app.get("/decisions/{decision_id}")
def lire_decision(decision_id: str):
    return service.lire("fiches", decision_id)


@app.patch("/decisions/{decision_id}")
def modifier_decision(decision_id: str, champs: dict[str, Any]):
    """Relecture du juriste, ex. {"validee": true} : la fiche entre dans les prochaines analyses."""
    return service.modifier_decision(decision_id, champs)
