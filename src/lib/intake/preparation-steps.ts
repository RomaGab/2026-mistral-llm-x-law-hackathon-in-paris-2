import type { CasePreparationStep } from "@/types/case-intake";

// Steps shown while a case is prepared; the intake advances them as each backend call completes
// (documents uploaded → facts extracted → analysis returned).
export function preparationSteps(hasDocuments: boolean): CasePreparationStep[] {
  return [
    { id: "question", kind: "question", label: "Reading your question…" },
    hasDocuments
      ? { id: "source", kind: "document", label: "Reading your documents…" }
      : { id: "source", kind: "context", label: "Understanding the situation…" },
    { id: "facts", kind: "facts", label: "Identifying the relevant facts…" },
    { id: "missing", kind: "missing", label: "Checking for missing information…" },
    { id: "review", kind: "review", label: "Preparing facts for your review…" },
  ];
}
