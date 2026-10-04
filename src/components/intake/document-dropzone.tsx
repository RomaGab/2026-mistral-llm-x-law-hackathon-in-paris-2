"use client";

import { useId, useRef, useState, type DragEvent, type ReactNode, type RefObject } from "react";
import { FiPlus, FiUpload, FiX } from "react-icons/fi";

import { DOCUMENT_ACCEPT, MAX_DOCUMENT_BYTES, formatDocumentSize, getDocumentType, mergeSelectedDocuments } from "@/lib/intake/files";
import type { SelectedDocument } from "@/types/intake";

import styles from "./document-dropzone.module.css";

const documentGuidance = `PDF, TXT, or DOCX · Up to ${formatDocumentSize(MAX_DOCUMENT_BYTES)} per file`;

type DocumentDropzoneProps = {
  fileInputRef: RefObject<HTMLInputElement | null>;
  documents: SelectedDocument[];
  onDocumentsChange: (documents: SelectedDocument[]) => void;
  children: ReactNode;
  actions?: ReactNode;
};

export function DocumentDropzone({ fileInputRef, documents, onDocumentsChange, children, actions }: DocumentDropzoneProps) {
  const guidanceId = useId();
  const attachRef = useRef<HTMLButtonElement>(null);
  const dragDepth = useRef(0);
  const [isDragging, setIsDragging] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [announcement, setAnnouncement] = useState("");

  function addDocuments(files: Iterable<File>) {
    const result = mergeSelectedDocuments(documents, files);
    setErrors(result.errors);
    if (result.addedCount > 0) onDocumentsChange(result.documents);
    const messages = [];
    if (result.addedCount > 0) messages.push(`${result.addedCount} ${result.addedCount === 1 ? "document" : "documents"} added.`);
    if (result.duplicateCount > 0) messages.push(`${result.duplicateCount} ${result.duplicateCount === 1 ? "duplicate" : "duplicates"} skipped.`);
    setAnnouncement(messages.join(" "));
  }

  function onDragEnter(event: DragEvent<HTMLDivElement>) {
    if (!event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    dragDepth.current += 1;
    setIsDragging(true);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    if (!event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    dragDepth.current = 0;
    setIsDragging(false);
    addDocuments(Array.from(event.dataTransfer.files));
  }

  function removeDocument(document: SelectedDocument) {
    attachRef.current?.focus();
    onDocumentsChange(documents.filter(({ id }) => id !== document.id));
    setAnnouncement(`“${document.file.name}” removed.`);
  }

  return (
    <div
      className={`${styles.field} ${isDragging ? styles.dragging : ""}`}
      onDragEnter={onDragEnter}
      onDragLeave={(event) => {
        event.preventDefault();
        dragDepth.current = Math.max(0, dragDepth.current - 1);
        if (dragDepth.current === 0) setIsDragging(false);
      }}
      onDragOver={(event) => {
        if (!event.dataTransfer.types.includes("Files")) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
      }}
      onDrop={onDrop}
    >
      {children}

      {documents.length > 0 && (
        <ul className={styles.fileList} aria-label="Selected documents">
          {documents.map((document) => (
            <li key={document.id} className={styles.fileRow}>
              <span className={styles.fileType}>{getDocumentType(document.file.name)?.toUpperCase()}</span>
              <div className={styles.fileDetails}>
                <span className={styles.fileName} title={document.file.name}>{document.file.name}</span>
                <span className={styles.fileSize}>{formatDocumentSize(document.file.size)}</span>
              </div>
              <button
                type="button"
                className={styles.removeButton}
                aria-label={`Remove ${document.file.name}`}
                onClick={() => removeDocument(document)}
              >
                <FiX size={16} strokeWidth={1.5} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className={styles.toolbar}>
        <button
          ref={attachRef}
          type="button"
          className={styles.attachButton}
          aria-label="Attach documents"
          aria-describedby={guidanceId}
          title={`Attach documents — ${documentGuidance}`}
          onClick={() => fileInputRef.current?.click()}
        >
          <FiPlus size={20} strokeWidth={1.6} aria-hidden="true" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={DOCUMENT_ACCEPT}
          multiple
          hidden
          aria-label="Attach documents"
          aria-describedby={guidanceId}
          onChange={(event) => {
            addDocuments(Array.from(event.currentTarget.files ?? []));
            event.currentTarget.value = "";
          }}
        />
        <span id={guidanceId} className={styles.srOnly}>{documentGuidance}</span>
        {actions}
      </div>

      {isDragging && (
        <div className={styles.dropOverlay} aria-hidden="true">
          <FiUpload size={28} strokeWidth={1.5} aria-hidden="true" />
          <strong>Drop documents to attach</strong>
          <span>{documentGuidance}</span>
        </div>
      )}
      <div role="alert" className={styles.errors}>
        {errors.length > 0 && <ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul>}
      </div>
      <span className={styles.srOnly} role="status" aria-live="polite" aria-atomic="true">{announcement}</span>
    </div>
  );
}
