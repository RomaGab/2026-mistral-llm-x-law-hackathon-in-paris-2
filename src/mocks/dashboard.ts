import example from "../../contracts/exemples/dossier_complet.json";
import scenarioData from "./dashboard-scenarios.json";
import type { AnalysisResult, DashboardDossier, FactOverride } from "@/types/dashboard";

export const exampleDossier: DashboardDossier = example;
const scenarios: Record<string, AnalysisResult> = scenarioData;

// These responses are frozen by scripts/generate-dashboard-fixtures.py.
// Replace this adapter with POST /cas/{id}/analyse at backend integration.
// A preview changes one fact relative to the original case; it never saves facts.
export function getDashboardPreview(override: FactOverride | null): DashboardDossier {
  const originalValue = override ? exampleDossier.cas.facteurs[override.factorId] : null;
  const changed = override !== null && override.value !== originalValue;
  const key = changed ? `${override.factorId}:${override.value === null ? "unknown" : override.value}` : "baseline";
  const result = scenarios[key];
  if (!result) throw new Error(`Missing dashboard preview: ${key}`);

  return {
    ...exampleDossier,
    cas: {
      ...exampleDossier.cas,
      facteurs: changed ? { ...exampleDossier.cas.facteurs, [override.factorId]: override.value } : exampleDossier.cas.facteurs,
    },
    resultat: result,
  };
}
