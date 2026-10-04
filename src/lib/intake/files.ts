import type { SelectedDocument } from "@/types/intake";

export const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024;

export const DOCUMENT_ACCEPT =
  ".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

const documentTypes = ["pdf", "txt", "docx"] as const;
type DocumentType = (typeof documentTypes)[number];

export function getDocumentType(filename: string): DocumentType | null {
  const dotIndex = filename.lastIndexOf(".");
  if (dotIndex === -1) return null;
  const extension = filename.slice(dotIndex + 1).toLowerCase();
  return documentTypes.find((type) => type === extension) ?? null;
}

function documentIdentity(file: File): string {
  return JSON.stringify([file.name, file.size, file.lastModified]);
}

export function mergeSelectedDocuments(
  current: SelectedDocument[],
  incoming: Iterable<File>,
): {
  documents: SelectedDocument[];
  errors: string[];
  addedCount: number;
  duplicateCount: number;
} {
  const documents = [...current];
  const identities = new Set(current.map(({ file }) => documentIdentity(file)));
  const errors: string[] = [];
  let addedCount = 0;
  let duplicateCount = 0;

  for (const file of incoming) {
    if (!getDocumentType(file.name)) {
      errors.push(`“${file.name}”: unsupported format. Use a PDF, TXT, or DOCX file.`);
      continue;
    }

    if (file.size === 0) {
      errors.push(`“${file.name}”: this file is empty.`);
      continue;
    }

    if (file.size > MAX_DOCUMENT_BYTES) {
      errors.push(`“${file.name}”: this file exceeds the 20 MB limit.`);
      continue;
    }

    const id = documentIdentity(file);
    if (identities.has(id)) {
      duplicateCount += 1;
      continue;
    }

    identities.add(id);
    documents.push({ id, file });
    addedCount += 1;
  }

  return { documents, errors: [...new Set(errors)], addedCount, duplicateCount };
}

export function formatDocumentSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const megabytes = bytes / (1024 * 1024);
  const size = megabytes >= 1 ? megabytes : bytes / 1024;
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(size)} ${megabytes >= 1 ? "MB" : "KB"}`;
}
