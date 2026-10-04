"""python -m calculateur entree.json [-o sortie.json] : complète un dossier sans passer par le back."""
import argparse
import json
import sys
from pathlib import Path

from . import ErreurDossier, completer


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m calculateur", description=__doc__)
    parser.add_argument("entree", type=Path, help="dossier JSON (resultat = null)")
    parser.add_argument("-o", "--sortie", type=Path, help="fichier de sortie (sinon : sortie standard)")
    args = parser.parse_args()

    try:
        complet = completer(json.loads(args.entree.read_text(encoding="utf-8")))
    except ErreurDossier as e:
        print(e, file=sys.stderr)
        return 1
    texte = json.dumps(complet, ensure_ascii=False, indent=2) + "\n"
    if args.sortie:
        args.sortie.write_text(texte, encoding="utf-8")
    else:
        sys.stdout.write(texte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
