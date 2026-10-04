"""Freeze single-fact UI scenarios using the existing calculator, never browser math.

Run from the project root: uv run python scripts/generate-dashboard-fixtures.py
The fictional contract examples are for frontend development only.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calculateur import completer
from contracts.valider import erreurs_dossier


def main():
    original = json.loads((ROOT / "contracts/exemples/dossier_entree.json").read_text())
    scenarios = {}
    for factor in [None, *original["grille"]["facteurs"]]:
        for value in [None] if factor is None else [True, False, None]:
            dossier = copy.deepcopy(original)
            key = "baseline"
            if factor is not None:
                factor_id = factor["id"]
                if original["cas"]["facteurs"][factor_id] is value:
                    continue
                dossier["cas"]["facteurs"][factor_id] = value
                dossier["meta"]["simulation"] = True
                key = f"{factor_id}:{str(value).lower() if value is not None else 'unknown'}"
            completed = completer(dossier)
            errors = erreurs_dossier(completed)
            if errors:
                raise ValueError(f"Invalid scenario {key}: {errors}")
            scenarios[key] = completed["resultat"]
    target = ROOT / "src/mocks/dashboard-scenarios.json"
    target.write_text(json.dumps(scenarios, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(scenarios)} validated scenarios to {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
