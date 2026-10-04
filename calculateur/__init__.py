"""Calculateur Distinguo : remplit le bloc `resultat` d'un dossier (contrat dans contracts/).

from calculateur import completer, ErreurDossier
dossier_complet = completer(dossier)   # lève ErreurDossier si le dossier est invalide
"""

from .moteur import VERSION as __version__
from .moteur import ErreurDossier, completer

__all__ = ["ErreurDossier", "__version__", "completer"]
