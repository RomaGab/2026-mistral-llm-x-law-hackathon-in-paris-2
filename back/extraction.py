"""Mistral : texte → faits. Seul module qui parle au réseau. On ne croit jamais la sortie du LLM :
tout passe par normaliser_faits / normaliser_decision avant d'être stocké (cf. docs/spec-back.md)."""

import base64
import io
import json
import math
import os
import re
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from mistralai.client import Mistral
from mistralai.client.utils import BackoffStrategy, RetryConfig
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from back import service
from back.service import Erreur

FORMATIONS = {"ass_pleniere", "ch_mixte", "cass", "ca", "premiere_instance"}
NATIONALES = {"ass_pleniere", "ch_mixte", "cass"}  # Cour de cassation : pas de ressort
PUBLICATIONS = {"R", "B", "inedit", "na"}
MENTION_COUR = re.compile(r"(?:FP|FS|F)(?:[-+][A-Z])+")  # mention brute de la Cour, ex. "F-D", "FS-B", "FP-P+B+R+I"
DISPOSITIFS = {"cassation", "rejet", "confirmation", "infirmation", "autre"}
GUILLEMETS = {'"': '"', "«": "»", "“": "”"}  # ouvrant → fermant
TYPO = str.maketrans({q: "'" for q in '"’‘«»“”'} | {"…": "..."})  # tous les guillemets se valent
ELLIPSE = re.compile(r"\[\s*\.\.\.\s*\]|\.\.\.")
PUCE = re.compile(r"(?m)^\s*[-•*]\s+")  # une citation peut enjamber deux lignes à puces


# Notre abonnement a une limite de débit serrée : le SDK réessaie sur 429 et 5xx (2 s, 4 s, 8 s…).
ATTENTE_LOT_MS = 120_000  # ingestion en lot : on peut attendre 2 min
ATTENTE_INTERACTIVE_MS = 25_000  # un utilisateur attend devant l'écran : on abandonne vite, avec un message clair


def _client(attente_max_ms: int = ATTENTE_LOT_MS) -> Mistral:
    cle = os.environ.get("MISTRAL_API_KEY")
    if not cle:
        raise Erreur(502, "mistral", "MISTRAL_API_KEY absente (lancer avec uv run --env-file .env)")
    reessai = RetryConfig("backoff", BackoffStrategy(2_000, 30_000, 2.0, attente_max_ms), retry_connection_errors=True)
    return Mistral(api_key=cle, timeout_ms=120_000, retry_config=reessai)


def _message_panne(quoi: str, e: Exception) -> str:
    if "429" in str(e):
        return (
            f"{quoi} : limite de débit Mistral atteinte (429). Réessayez dans une minute, ou déposez un fichier .txt."
        )
    return f"{quoi} : {e}"


def appeler_mistral(messages: list[dict], attente_max_ms: int = ATTENTE_LOT_MS) -> dict:
    """Un appel en JSON mode, température 0. Toute panne (réseau, quota, JSON illisible) donne un 502."""
    try:
        reponse = _client(attente_max_ms).chat.complete(
            model=os.environ.get("MISTRAL_MODELE", "ministral-14b-latest"),
            messages=messages,
            temperature=0,
            random_seed=0,
            response_format={"type": "json_object"},
        )
        return json.loads(reponse.choices[0].message.content)
    except Erreur:
        raise
    except Exception as e:  # frontière réseau : on ne laisse rien remonter d'autre
        raise Erreur(502, "mistral", _message_panne("Échec de l'appel à Mistral", e)) from e


TYPES_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
EXTENSIONS_DOCUMENT = {".txt", *TYPES_MIME}


def ocr(octets: bytes, mime: str) -> str:
    """PDF ou DOCX → texte (markdown) via Mistral OCR. Toute panne donne un 502."""
    url = f"data:{mime};base64,{base64.b64encode(octets).decode()}"
    try:
        r = _client(ATTENTE_INTERACTIVE_MS).ocr.process(
            model=os.environ.get("MISTRAL_OCR", "mistral-ocr-latest"),
            document={"type": "document_url", "document_url": url},
        )
        return "\n\n".join(page.markdown for page in r.pages)
    except Erreur:
        raise
    except Exception as e:  # frontière réseau
        raise Erreur(502, "mistral", _message_panne("Échec de l'OCR Mistral", e)) from e


SEUIL_TEXTE_PDF = 200  # caractères : en dessous, le PDF est probablement scanné (images) → OCR
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def lire_pdf(octets: bytes) -> str:
    """Texte d'un PDF « texte », lu localement (sans réseau ni quota). Chaîne vide si illisible."""
    try:
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(octets)).pages)
    except (PyPdfError, ValueError, KeyError, OSError):  # PDF corrompu ou chiffré : l'OCR essaiera
        return ""


def lire_docx(octets: bytes) -> str:
    """Texte d'un DOCX (du XML zippé), paragraphe par paragraphe, sans dépendance ni réseau."""
    try:
        with zipfile.ZipFile(io.BytesIO(octets)) as archive:
            racine = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
        raise Erreur(400, "docx_illisible", "Ce fichier DOCX est illisible") from None
    paragraphes = []
    for p in racine.iter(f"{W}p"):
        morceaux = []
        for e in p.iter():
            if e.tag == f"{W}t":
                morceaux.append(e.text or "")
            elif e.tag == f"{W}tab":
                morceaux.append("\t")
            elif e.tag in (f"{W}br", f"{W}cr"):
                morceaux.append("\n")
        paragraphes.append("".join(morceaux))
    return "\n".join(paragraphes)


def lire_document(nom: str, octets: bytes) -> str:
    """TXT en UTF-8 et DOCX lus localement ; PDF lu localement, et passé à l'OCR Mistral
    seulement s'il ne contient presque pas de texte (PDF scanné). Autre extension : 400."""
    extension = Path(nom).suffix.lower()
    if extension not in EXTENSIONS_DOCUMENT:
        raise Erreur(400, "format_refuse", f"Format non pris en charge : {nom!r} (TXT, PDF ou DOCX)")
    if extension == ".txt":
        try:
            texte = octets.decode("utf-8")
        except UnicodeDecodeError:
            raise Erreur(400, "encodage", f"{nom!r} n'est pas un texte UTF-8") from None
    elif extension == ".docx":
        texte = lire_docx(octets)
    else:
        texte = lire_pdf(octets)
        if len(texte.strip()) < SEUIL_TEXTE_PDF:
            texte = ocr(octets, TYPES_MIME[extension])
    if not texte.strip():
        raise Erreur(400, "document_vide", f"Aucun texte lisible dans {nom!r}")
    return texte


def _comparable(s: str) -> str:
    return " ".join(PUCE.sub("", s.translate(TYPO)).split()).lower()


def _citation(extrait: str) -> str:
    """Le passage cité, sans les guillemets qui l'entourent ni le commentaire qui suit."""
    e = extrait.strip()
    fin = GUILLEMETS.get(e[:1])
    if fin and fin in e[1:]:
        e = e[1 : e.rindex(fin)].strip()
    return e


def _retrouve(extrait: str, source: str) -> bool:
    """Chaque fragment de la citation (séparés par [...]) figure tel quel dans le texte, casse et guillemets mis à part."""
    fragments = [_comparable(m).strip(" '") for m in ELLIPSE.split(extrait.translate(TYPO))]
    fragments = [m for m in fragments if m]
    return bool(fragments) and all(m in source for m in fragments)


def normaliser_faits(brut, texte: str, grille: list[dict]) -> tuple[dict, dict]:
    """Sortie Mistral → facteurs stricts (true / false / null) + preuves vérifiées contre le texte."""
    brut = brut if isinstance(brut, dict) else {}
    source = _comparable(texte)
    facteurs, preuves = {}, {}
    for f in grille:
        r = brut.get(f["id"]) if isinstance(brut.get(f["id"]), dict) else {}
        v = r.get("valeur")
        facteurs[f["id"]] = v if isinstance(v, bool) else None
        extrait = _citation(r["extrait"]) if isinstance(r.get("extrait"), str) else None
        if extrait and not _retrouve(extrait, source):
            extrait = None  # citation introuvable dans le texte : hallucination probable
        extrait = extrait or None
        c = r.get("confiance")
        nombre = isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c)
        confiance = min(max(float(c), 0.0), 1.0) if nombre else 0.0
        if extrait is None:
            confiance = min(confiance, 0.5)  # pas de preuve → à confirmer
        if facteurs[f["id"]] is not None or extrait:
            preuves[f["id"]] = {"extrait": extrait, "confiance": confiance, "source": "extraction"}
    return facteurs, preuves


def _publication(valeur) -> str:
    """Catégorie du schéma. Le modèle renvoie parfois la mention brute de la Cour (« F-D ») :
    elle se convertit sans ambiguïté (R s'il y a un R, sinon B s'il y a un B, sinon inédit)."""
    if valeur in PUBLICATIONS:
        return valeur
    if isinstance(valeur, str) and MENTION_COUR.fullmatch(valeur.strip().upper()):
        lettres = set(valeur.strip().upper().split("-", 1)[1].replace("+", "-").split("-"))
        return "R" if "R" in lettres else "B" if "B" in lettres else "inedit"
    raise _invalide("publication", valeur)


def _invalide(champ: str, valeur) -> Erreur:
    return Erreur(502, "extraction_invalide", f"Mistral a renvoyé un champ {champ} invalide : {valeur!r}")


def normaliser_decision(brut, texte: str, grille: list[dict], id_: str, pays: str | None = None) -> dict:
    """Sortie Mistral → fiche au format `decision` du schéma, toujours validee: false.
    Une métadonnée obligatoire invalide fait échouer la fiche plutôt que d'inventer une valeur."""
    if not isinstance(brut, dict):
        raise Erreur(502, "extraction_invalide", "La réponse de Mistral n'est pas un objet JSON")

    def texte_requis(champ):
        v = brut.get(champ)
        if not isinstance(v, str) or not v.strip():
            raise _invalide(champ, v)
        return v.strip()

    def dans(champ, valeurs):
        if brut.get(champ) not in valeurs:
            raise _invalide(champ, brut.get(champ))
        return brut[champ]

    if not isinstance(brut.get("issue"), bool):
        raise _invalide("issue", brut.get("issue"))
    jour = texte_requis("date")
    try:
        date.fromisoformat(jour)
    except ValueError:
        raise _invalide("date", jour) from None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", jour):
        raise _invalide("date", jour)
    formation = dans("formation", FORMATIONS)
    facteurs, preuves = normaliser_faits(brut.get("faits"), texte, grille)
    cites = brut.get("determinants") if isinstance(brut.get("determinants"), list) else []
    # le modèle renvoie parfois [{"identifiant": ..., "extrait": ...}] au lieu d'une liste d'ids
    cites = [c.get("identifiant", c.get("id")) if isinstance(c, dict) else c for c in cites]
    ressort = brut.get("ressort") if isinstance(brut.get("ressort"), str) else None
    return {
        "id": id_,
        "pays": pays
        or (brut["pays"].strip() if isinstance(brut.get("pays"), str) and brut["pays"].strip() else "France"),
        "intitule": texte_requis("intitule"),
        "juridiction": texte_requis("juridiction"),
        "formation": formation,
        "ressort": None if formation in NATIONALES else ressort,
        "date": jour,
        "numero": brut.get("numero") if isinstance(brut.get("numero"), str) else None,
        "publication": _publication(brut.get("publication")),
        "dispositif": brut.get("dispositif") if brut.get("dispositif") in DISPOSITIFS else None,
        "issue": brut["issue"],
        "textes": [t for t in brut.get("textes") or [] if isinstance(t, str)]
        if isinstance(brut.get("textes"), list)
        else [],
        "remise_en_cause": None,  # seul le juriste le renseigne
        "url": None,
        "validee": False,  # seul le juriste valide
        "facteurs": facteurs,
        # ordre de la grille, sans doublon ; un motif décisif est connu ET cité (extrait vérifié)
        "determinants": [
            f["id"]
            for f in grille
            if f["id"] in cites and facteurs[f["id"]] is not None and (preuves.get(f["id"]) or {}).get("extrait")
        ],
        "preuves": preuves,
    }


def _messages_decision(texte: str, grille: dict, notes: dict | None) -> list[dict]:
    questions = "\n".join(f'- "{f["id"]}" : {f["question"]}' for f in grille["facteurs"])
    consignes = f"""Fiche cette décision de justice française pour la question de droit : « {grille["question"]} »
(issue vraie = « {grille["issue"]["si_vrai"]} », issue fausse = « {grille["issue"]["si_faux"]} »).

Réponds uniquement par un objet JSON avec exactement ces clés :
- "intitule" : libellé court, ex. "Cass. soc., 4 mars 2020, n° 19-13.316" ou "CA Paris, 10 janv. 2019, n° 18/08357".
- "pays" : pays ou ordre juridique de la juridiction, ex. "France", "Royaume-Uni", "États-Unis", "Union européenne".
- "juridiction" : ex. "Cour de cassation, chambre sociale".
- "formation" : "ass_pleniere", "ch_mixte", "cass" (toute chambre de la Cour de cassation ; pour un pays étranger, sa cour suprême), "ca" (cour d'appel) ou "premiere_instance".
- "ressort" : pour une cour d'appel, "CA <ville>" ; sinon null.
- "date" : date de la décision, au format AAAA-MM-JJ.
- "numero" : numéro de pourvoi ou de RG, sinon null.
- "publication" : pour la Cour de cassation, "R" si la mention de publication contient R, sinon "B" si elle contient B, sinon "inedit" (ex. "F-D") ; pour les autres juridictions, "na".
- "dispositif" : "cassation", "rejet", "confirmation", "infirmation" ou "autre".
- "issue" : true si, AU FOND, la décision retient (ou conduit à retenir) {grille["issue"]["libelle"].lower()}, false sinon. Ce n'est pas le dispositif : une cassation peut aboutir à true comme à false.
- "textes" : liste des articles de loi visés.
- "faits" : un objet avec, pour CHAQUE identifiant ci-dessous, {{"valeur": true | false | null, "extrait": "..." | null, "confiance": 0 à 1}}.
  "valeur" : true ou false SEULEMENT si le texte l'établit expressément (faits constatés par les juges, y compris ceux de l'arrêt attaqué que la décision reprend), ou si les notes le disent expressément. Sinon null : un texte muet n'est pas un « non ». Ne déduis jamais un fait d'un autre (une sanction n'est pas une évaluation de performance, une géolocalisation n'est pas un service organisé).
  La valeur répond à la question TELLE QU'ELLE EST POSÉE, quelle que soit la solution : si la décision constate que le travailleur choisit librement ses horaires, "liberte_horaires" vaut true, même si elle juge que cela n'exclut pas le salariat. Un fait favorable à l'indépendance que la juridiction écarte comme insuffisant reste un fait vrai.
  "extrait" : UN SEUL passage continu, copié exactement dans le texte de la décision, sans guillemets autour, sans « [...] », sans commentaire (300 caractères au plus). null si la valeur vient des notes ou si aucun passage ne la justifie.
  "confiance" : 1 si le passage le dit en toutes lettres ; 0,5 au plus si la valeur vient des notes.
- "determinants" : les identifiants des faits que la motivation cite expressément comme raison de la solution (en général 1 à 3). Chacun doit avoir un extrait.

Identifiants et questions :
{questions}"""
    if notes:
        consignes += (
            "\n\nNotes d'un outil de recherche sur la décision complète (le texte ci-dessous peut n'en être qu'un extrait). "
            "Ce sont des indices, pas des vérités : un fait qui n'est que dans les notes prend la valeur des notes, "
            "avec extrait null et confiance 0,5 au plus. Ne cite que le texte.\n"
            + json.dumps(notes, ensure_ascii=False, indent=1)
        )
    return [
        {
            "role": "system",
            "content": "Tu es un juriste qui fiche des décisions de justice. Tu réponds uniquement en JSON.",
        },
        {"role": "user", "content": f"{consignes}\n\n<decision>\n{texte}\n</decision>"},
    ]


def extraire_decision(texte: str, id_: str, notes: dict | None = None, pays: str | None = None) -> dict:
    g = service.grille()
    return normaliser_decision(appeler_mistral(_messages_decision(texte, g, notes)), texte, g["facteurs"], id_, pays)


def _messages_cas(texte: str, grille: dict) -> list[dict]:
    questions = "\n".join(f'- "{f["id"]}" : {f["question"]}' for f in grille["facteurs"])
    consignes = f"""Qualifie les faits de ce dossier client pour la question de droit : « {grille["question"]} ».

Réponds uniquement par un objet JSON {{"faits": {{...}}}} avec, pour CHAQUE identifiant ci-dessous,
{{"valeur": true | false | null, "extrait": "..." | null, "confiance": 0 à 1}}.
- "valeur" : true ou false SEULEMENT si le dossier l'établit expressément. Sinon null : un dossier muet n'est pas un « non ».
  Ne déduis jamais un fait d'un autre. La valeur répond à la question TELLE QU'ELLE EST POSÉE.
- "extrait" : UN SEUL passage continu, copié exactement dans le dossier, sans guillemets autour, sans « [...] »,
  sans commentaire (300 caractères au plus). null si aucun passage ne le justifie.
- "confiance" : 1 si le passage le dit en toutes lettres, moins sinon.

Identifiants et questions :
{questions}"""
    return [
        {
            "role": "system",
            "content": "Tu es un juriste qui qualifie les faits d'un dossier client. Tu réponds uniquement en JSON.",
        },
        {"role": "user", "content": f"{consignes}\n\n<dossier>\n{texte}\n</dossier>"},
    ]


def extraire_cas(description: str, textes: list[str]) -> tuple[dict, dict]:
    """Description de l'avocat + textes des pièces → facteurs et preuves vérifiées contre ce même texte."""
    g = service.grille()
    source = "\n\n".join([description, *textes])
    brut = appeler_mistral(_messages_cas(source, g), ATTENTE_INTERACTIVE_MS)
    faits = brut.get("faits", brut) if isinstance(brut, dict) else {}
    return normaliser_faits(faits, source, g["facteurs"])
