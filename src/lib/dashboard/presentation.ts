import type { DecisionAnalysis, FactorDefinition, FactValue } from "@/types/dashboard";

export const factValueChoices: { value: FactValue; inputValue: string; label: string }[] = [
  { value: true, inputValue: "yes", label: "Yes" },
  { value: false, inputValue: "no", label: "No" },
  { value: null, inputValue: "unknown", label: "Unknown" },
];

// English presentation of the shared French grid. IDs and ordering stay intact.
const factorCopy: Record<string, { label: string; question: string }> = {
  service_organise: { label: "Platform-organised service", question: "Does the platform set all the conditions for the service?" },
  geolocalisation_suivi: { label: "Real-time location tracking", question: "Does the platform track the worker’s location in real time?" },
  sanction_deconnexion: { label: "Account suspension or deactivation", question: "Can the platform suspend an account for refusals, cancellations, or low ratings?" },
  penalites_bonus: { label: "Penalties or performance bonuses", question: "Are penalties or bonuses linked to the worker’s behaviour?" },
  tarif_impose: { label: "Prices set by the platform", question: "Does the platform set the price of each job?" },
  clientele_attribuee: { label: "No independent customer base", question: "Is the worker prevented from building their own customer base?" },
  execution_dirigee: { label: "Work instructions imposed", question: "Does the platform impose routes, processes, or deadlines?" },
  multi_plateformes: { label: "Freedom to work for competitors", question: "Can the worker take jobs from other platforms?" },
  remplacement_possible: { label: "Freedom to use a substitute", question: "Can another worker perform the job in their place?" },
  info_masquee: { label: "Job details hidden before acceptance", question: "Are the destination or job details hidden until acceptance?" },
  evaluation_performance: { label: "Performance ratings", question: "Does the platform use worker ratings or performance statistics?" },
  equipement_marque: { label: "Branded equipment required", question: "Does the platform require branded clothing or equipment?" },
  liberte_horaires: { label: "Freedom to choose working hours", question: "Can the worker choose when to connect and work?" },
  moyens_propres: { label: "Worker’s own equipment", question: "Does the worker supply equipment and cover their own expenses?" },
  immatriculation: { label: "Registered as self-employed", question: "Is the worker registered as a self-employed business?" },
  charte_sociale: { label: "Platform social charter", question: "Does the platform have a social responsibility charter?" },
  qualification_contractuelle: { label: "Independent contractor agreement", question: "Does the contract describe the relationship as independent?" },
  dependance_economique: { label: "Economic dependence", question: "Does most of the worker’s income come from the platform?" },
};

export function factCopy(factor: FactorDefinition) {
  return factorCopy[factor.id] ?? { label: factor.libelle, question: factor.question };
}

export function factLabel(id: string) {
  return factorCopy[id]?.label ?? id;
}

export function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

// Describe changes in returned results; no analysis is calculated in the browser.
export function decisionStatusChange(current: DecisionAnalysis | undefined, original: DecisionAnalysis | undefined) {
  if (!current || !original || current.retenue === original.retenue) return null;
  return current.retenue ? "Newly retained" : "Newly excluded";
}

export function factValueLabel(value: FactValue) {
  return value === null ? "Unknown" : value ? "Yes" : "No";
}

export function outcomeLabel(value: boolean, labels: { si_vrai: string; si_faux: string }) {
  const label = value ? labels.si_vrai : labels.si_faux;
  return ({ Salariat: "Employment", Indépendance: "Independence" } as Record<string, string>)[label] ?? label;
}

// French citations rendered in English: court, month and number sign. The case-law reference itself is unchanged.
const courtCopy: [RegExp, string][] = [
  [/^Cass\. soc\./, "Supreme Court"],
  [/^Cass\. com\./, "Supreme Court (Commercial)"],
  [/^CA ([A-ZÀ-Ý][\w-]+)/, "$1 Appeal"],
];
const monthCopy: Record<string, string> = {
  "janv.": "Jan.", "févr.": "Feb.", "mars": "Mar.", "avr.": "Apr.", "avril": "Apr.", "mai": "May", "juin": "Jun.",
  "juil.": "Jul.", "juillet": "Jul.", "août": "Aug.", "sept.": "Sep.", "oct.": "Oct.", "nov.": "Nov.", "déc.": "Dec.",
};

export function decisionLabel(title: string) {
  let label = title.replace("[FICTIF] ", "");
  for (const [pattern, english] of courtCopy) label = label.replace(pattern, english);
  label = label.replace(/(\d{1,2}) (janv\.|févr\.|mars|avr\.|avril|mai|juin|juil\.|juillet|août|sept\.|oct\.|nov\.|déc\.) (\d{4})/, (_, day, month, year) => `${day} ${monthCopy[month]} ${year}`);
  return label.replace(/n° /g, "No. ");
}
