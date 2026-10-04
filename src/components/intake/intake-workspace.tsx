"use client";

import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { FiArrowUp, FiFileText, FiX } from "react-icons/fi";

import type { CaseIntakeDraft } from "@/types/case-intake";

import { DocumentDropzone } from "./document-dropzone";
import styles from "./intake-workspace.module.css";

type CaseIntakeFormProps = {
  draft: CaseIntakeDraft;
  onDraftChange: (draft: CaseIntakeDraft) => void;
  onSubmit: (draft: CaseIntakeDraft) => void;
};

export function CaseIntakeForm({ draft, onDraftChange, onSubmit }: CaseIntakeFormProps) {
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const confirmationRef = useRef<HTMLDialogElement>(null);
  const addDocumentsRef = useRef<HTMLButtonElement>(null);
  const canSubmit = draft.question.trim().length > 0;

  useLayoutEffect(() => {
    const textarea = promptRef.current;
    if (!textarea) return;

    function resizePrompt() {
      if (!textarea) return;
      const scrollTop = textarea.scrollTop;
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
      textarea.scrollTop = scrollTop;
    }

    resizePrompt();
    window.addEventListener("resize", resizePrompt);
    return () => window.removeEventListener("resize", resizePrompt);
  }, [draft.question]);

  function submitDraft() {
    if (!canSubmit) return;
    onSubmit({ ...draft, question: draft.question.trim() });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      promptRef.current?.focus();
      return;
    }
    if (confirmationRef.current?.open) return;
    if (draft.documents.length === 0) {
      confirmationRef.current?.showModal();
      addDocumentsRef.current?.focus();
      return;
    }
    submitDraft();
  }

  return (
    <form
      className={styles.form}
      aria-label="Your legal question"
      onSubmit={handleSubmit}
      onKeyDown={(event) => {
        if (confirmationRef.current?.open) return;
        if (!event.nativeEvent.isComposing && event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
          event.preventDefault();
          event.currentTarget.requestSubmit();
        }
      }}
    >
      <DocumentDropzone
        fileInputRef={fileInputRef}
        documents={draft.documents}
        onDocumentsChange={(documents) => onDraftChange({ ...draft, documents })}
        actions={
          <button
            type="submit"
            className={styles.submitButton}
            disabled={!canSubmit}
            aria-label="Send question"
            title="Send question"
          >
            <FiArrowUp size={20} strokeWidth={1.75} aria-hidden="true" />
          </button>
        }
      >
        <textarea
          ref={promptRef}
          name="question"
          className={styles.textarea}
          rows={4}
          required
          aria-label="Your legal question"
          placeholder="Ask your legal question…"
          value={draft.question}
          onChange={(event) => onDraftChange({ ...draft, question: event.target.value })}
        />
      </DocumentDropzone>

      <dialog
        ref={confirmationRef}
        className={styles.confirmation}
        aria-labelledby="no-documents-title"
        aria-describedby="no-documents-description"
      >
        <div className={styles.dialogHeader}>
          <span className={styles.dialogIcon}><FiFileText size={20} aria-hidden="true" /></span>
          <button
            type="button"
            className={styles.closeButton}
            aria-label="Close confirmation"
            onClick={() => confirmationRef.current?.close()}
          >
            <FiX size={20} aria-hidden="true" />
          </button>
        </div>
        <h2 id="no-documents-title">Continue without documents?</h2>
        <p id="no-documents-description">
          No files are attached to your question. Would you like to continue without documents?
        </p>
        <div className={styles.dialogActions}>
          <button
            ref={addDocumentsRef}
            type="button"
            className={styles.secondaryButton}
            onClick={() => {
              confirmationRef.current?.close();
              fileInputRef.current?.click();
            }}
          >
            Add documents
          </button>
          <button
            type="button"
            className={styles.continueButton}
            onClick={() => {
              confirmationRef.current?.close();
              submitDraft();
            }}
          >
            Continue without documents
          </button>
        </div>
      </dialog>
    </form>
  );
}

export function IntakeWorkspace() {
  const [draft, setDraft] = useState<CaseIntakeDraft>({
    question: "", description: "", ressort: null, documents: [],
  });
  const [submitted, setSubmitted] = useState(false);

  return (
    <div
      className={styles.shell}
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes("Files")) event.preventDefault();
      }}
      onDrop={(event) => {
        if (event.dataTransfer.types.includes("Files")) event.preventDefault();
      }}
    >
      <header className={styles.header}>
        <div className={styles.brand} aria-label="Distinguo">
          <svg className={styles.brandMark} width="28" height="28" viewBox="0 0 28 28" fill="currentColor" aria-hidden="true">
            <path d="M4 4h12v4H8v12h8v4H4V4Zm12 4h4v4h-4V8Zm4 4h4v8h-4v-8Zm-4 8h4v4h-4v-4Z" />
          </svg>
          <span className={styles.brandName}>distinguo<span>.</span></span>
        </div>
      </header>

      <main className={styles.content} id="main-content">
        <div className={styles.composer}>
          <div className={styles.intro}>
            <h1>Analyze your case.</h1>
            <p>Ask your question and add your documents to identify the decisive facts.</p>
          </div>
          <CaseIntakeForm
            draft={draft}
            onDraftChange={(next) => {
              setDraft(next);
              setSubmitted(false);
            }}
            onSubmit={(next) => {
              setDraft(next);
              setSubmitted(true);
            }}
          />
          <div className={styles.feedback} role="status" aria-live="polite">
            {submitted && "Preview saved for this session. Analysis will be available once connected."}
          </div>
        </div>
      </main>
    </div>
  );
}
