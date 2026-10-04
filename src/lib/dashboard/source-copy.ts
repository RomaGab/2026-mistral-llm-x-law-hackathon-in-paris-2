import type { FactorDefinition } from "@/types/dashboard";
import { factCopy } from "./presentation";

// Display translations for the current source excerpts. Shared contract fixtures
// remain in their original language; backend integration must supply English copy.
const excerptTranslations: Record<string, string> = {
  "l'application les géolocalise pendant les courses": "the app tracks their location during deliveries",
  "le prix de chaque course est fixé par la plateforme": "the platform sets the price of each delivery",
  "ils peuvent travailler pour d'autres applications": "they can work for other apps",
  "peuvent confier une course à un autre livreur inscrit": "can assign a delivery to another registered rider",
  "Les livreurs choisissent leurs créneaux": "Riders choose their working hours",
  "sont micro-entrepreneurs": "are self-employed under the microbusiness regime",
  "[FICTIF] extrait de la motivation": "[FICTIONAL] excerpt from the court’s reasoning",
};

export function englishExcerpt(excerpt: string) {
  return excerptTranslations[excerpt] ?? null;
}

export function englishExclusionReason(reason: string, factors: FactorDefinition[]) {
  const prefix = "Fait déterminant divergent : ";
  if (reason.startsWith(prefix)) {
    const sourceLabel = reason.slice(prefix.length);
    const factor = factors.find((item) => item.libelle === sourceLabel);
    if (factor) return `Decisive fact differs: ${factCopy(factor).label}.`;
  }
  return "This precedent is excluded. An English explanation is not available yet.";
}
