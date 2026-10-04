"""Les deux modèles du calculateur, avec la même interface.

    modele = creer_modele(dossier, grille)
    modele.predire(faits) -> {"p", "lo", "hi", "exclues"}   (valeurs non arrondies)

`faits` est un dictionnaire {facteur: True | False | None} couvrant toute la grille.
Les exclusions sont recalculées pour chaque jeu de faits : changer un fait peut écarter
ou réintégrer des décisions. Aucun aléa : même entrée, même sortie.
"""

import math
from collections import defaultdict

import numpy as np
from scipy.stats import beta, norm

from .precedents import Grille, detail_poids, exclusion, poids, proximite

SIGMA_DEFAUT = (
    0.3  # écart-type de l'a priori : confiance dans la grille du juriste (choisi par validation croisée sur le corpus)
)
KAPPA_DEFAUT = 2.0  # force probante d'une décision dans le vote pondéré
ECHELLE_A_PRIORI = 1.0
PLAFOND_JURIDICTION = 1.5


def code(v: bool | None) -> float:
    return 0.0 if v is None else (1.0 if v else -1.0)


class _Base:
    def __init__(self, dossier: dict, g: Grille):
        self.g = g
        self.decisions = dossier["decisions"]
        self.cas = dossier["cas"]
        p = dossier["parametres"]
        self.niveau = p["niveau_intervalle"]
        self.poids = [poids(detail_poids(self.cas, d, p["date_reference"])) for d in self.decisions]
        self._cache: dict[tuple, dict] = {}

    def exclues(self, faits: dict) -> list[str]:
        return [d["id"] for d in self.decisions if exclusion(faits, d, self.g)]

    def predire(self, faits: dict) -> dict:
        cle = tuple(faits[i] for i in self.g.ids)
        if cle not in self._cache:
            self._cache[cle] = self._predire(faits)
        return self._cache[cle]


class LogistiqueBayesienne(_Base):
    """Régression logistique bayésienne : a priori = sens × importance de chaque facteur.

    MAP par Newton, intervalle par approximation de Laplace sur le score (logit).
    """

    def __init__(self, dossier: dict, g: Grille):
        super().__init__(dossier, g)
        sigma = float(dossier["parametres"].get("sigma_a_priori", SIGMA_DEFAUT))
        self.mu = np.array(
            [0.0] + [(1.0 if g.oriente[f] else -1.0) * g.importance[f] * ECHELLE_A_PRIORI for f in g.actifs]
        )
        self.prec = np.full(len(self.mu), 1.0 / sigma**2)
        self.X = np.array([[1.0] + [code(d["facteurs"][f]) for f in g.actifs] for d in self.decisions]).reshape(
            -1, len(self.mu)
        )
        self.y = np.array([1.0 if d["issue"] else 0.0 for d in self.decisions])
        self.w = np.array(self.poids)
        self._ajustements: dict[tuple, tuple] = {}

    def _ajuster(self, retenues: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
        if retenues not in self._ajustements:
            idx = list(retenues)
            X, y, w = self.X[idx], self.y[idx], self.w[idx]
            b = self.mu.copy()
            for _ in range(100):
                p = 1.0 / (1.0 + np.exp(-(X @ b)))
                g = X.T @ (w * (y - p)) - self.prec * (b - self.mu)
                H = X.T @ (X * (w * p * (1 - p))[:, None]) + np.diag(self.prec)
                pas = np.linalg.solve(H, g)
                b = b + pas
                if np.max(np.abs(pas)) < 1e-10:
                    break
            p = 1.0 / (1.0 + np.exp(-(X @ b)))
            H = X.T @ (X * (w * p * (1 - p))[:, None]) + np.diag(self.prec)
            self._ajustements[retenues] = (b, np.linalg.inv(H))
        return self._ajustements[retenues]

    def _predire(self, faits: dict) -> dict:
        exclues = self.exclues(faits)
        retenues = tuple(k for k, d in enumerate(self.decisions) if d["id"] not in exclues)
        b, cov = self._ajuster(retenues)
        x = np.array([1.0] + [code(faits[f]) for f in self.g.actifs])
        z = float(x @ b)
        s = math.sqrt(max(float(x @ cov @ x), 0.0))
        q = norm.ppf(0.5 + self.niveau / 2)
        sig = lambda t: 1.0 / (1.0 + math.exp(-t))
        return {"p": sig(z), "lo": sig(z - q * s), "hi": sig(z + q * s), "exclues": exclues}


class VotePondere(_Base):
    """Vote des décisions retenues, pondéré par proximité × poids, lissé par une loi Beta."""

    A0 = 0.5  # a priori de Jeffreys

    def __init__(self, dossier: dict, g: Grille):
        super().__init__(dossier, g)
        self.kappa = float(dossier["parametres"].get("kappa", KAPPA_DEFAUT))

    def _predire(self, faits: dict) -> dict:
        exclues = self.exclues(faits)
        scores = [
            (d, proximite(faits, d, self.g) * w) for d, w in zip(self.decisions, self.poids) if d["id"] not in exclues
        ]
        par_jur = defaultdict(float)
        for d, s in scores:
            par_jur[d["juridiction"]] += s
        A = B = self.A0
        for d, s in scores:
            s *= min(1.0, PLAFOND_JURIDICTION / par_jur[d["juridiction"]]) if par_jur[d["juridiction"]] else 1.0
            if d["issue"]:
                A += self.kappa * s
            else:
                B += self.kappa * s
        q = (1 - self.niveau) / 2
        lo, hi = beta.ppf([q, 1 - q], A, B)
        return {"p": A / (A + B), "lo": float(lo), "hi": float(hi), "exclues": exclues}


MODELES = {"logistique_bayesienne": LogistiqueBayesienne, "vote_pondere": VotePondere}


def creer_modele(dossier: dict, g: Grille) -> _Base:
    return MODELES[dossier["parametres"]["modele"]](dossier, g)
