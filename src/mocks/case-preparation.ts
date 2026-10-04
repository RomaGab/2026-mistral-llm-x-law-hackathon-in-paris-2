import type { CasePreparationStep } from "@/types/case-intake";

// Illustrative progress until backend events drive the preparation screen.
export const PREPARATION_PREVIEW_MS = 3000;

export function getPreparationPreviewSteps(hasDocuments: boolean): CasePreparationStep[] {
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
