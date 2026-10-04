"""API REST pour le front (§7 du contrat). Lancer : uv run uvicorn back.api:app --reload --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from back import service
from back.service import Erreur

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


@app.get("/sante")
def sante():
    return {"ok": True}


@app.get("/grille")
def grille():
    return service.grille()
