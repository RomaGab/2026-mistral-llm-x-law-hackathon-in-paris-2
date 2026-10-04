import type { SelectedDocument } from "./intake";

// Local intake state. document_ids are assigned by POST /documents at integration.
export type CaseIntakeDraft = {
  question: string;
  description: string;
  ressort: string | null;
  documents: SelectedDocument[];
};
