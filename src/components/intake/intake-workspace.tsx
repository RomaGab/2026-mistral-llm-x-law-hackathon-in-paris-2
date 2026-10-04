"use client";

import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { FiArrowUp, FiFileText, FiX } from "react-icons/fi";

import type { CaseIntakeDraft } from "@/types/case-intake";
import { AppHeader } from "@/components/ui/app-header";
import { DashboardWorkspace } from "@/components/dashboard/dashboard-workspace";
import { PREPARATION_PREVIEW_MS } from "@/mocks/case-preparation";

import { CasePreparationPreview } from "./case-preparation";
import { DocumentDropzone } from "./document-dropzone";
import styles from "./intake-workspace.module.css";

type CaseIntakeFormProps = {
  draft: CaseIntakeDraft;
  onDraftChange: (draft: CaseIntakeDraft) => void;
  onSubmit: (draft: CaseIntakeDraft) => void;
};

type IntakePhase = "intake" | "leaving" | "preparing" | "returning" | "dashboard";

export function CaseIntakeForm({ draft, onDraftChange, onSubmit }: CaseIntakeFormProps) {
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const confirmationRef = useRef<HTMLDialogElement>(null);
  const confirmationTitleRef = useRef<HTMLHeadingElement>(null);
  const [confirmationAction, setConfirmationAction] = useState<"dismiss" | "submit" | null>(null);
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

  function closeConfirmation(action: "dismiss" | "submit" = "dismiss") {
    if (!confirmationRef.current?.open || confirmationAction !== null) return;
    setConfirmationAction(action);
  }

  function finishClosingConfirmation() {
    confirmationRef.current?.close();
    setConfirmationAction(null);
    if (confirmationAction === "submit") submitDraft();
    else promptRef.current?.focus({ preventScroll: true });
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
      confirmationTitleRef.current?.focus({ preventScroll: true });
      return;
    }
    submitDraft();
  }

  return (
    <form
      className={styles.form}
      aria-label="Your case and legal question"
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
          autoFocus={draft.question.length > 0}
          name="question"
          className={styles.textarea}
          rows={4}
          required
          aria-label="Your case and legal question"
          placeholder="Describe the situation and the legal question you want to explore…"
          value={draft.question}
          onChange={(event) => onDraftChange({ ...draft, question: event.target.value })}
        />
      </DocumentDropzone>

      <dialog
        ref={confirmationRef}
        className={styles.confirmation}
        aria-labelledby="no-documents-title"
        aria-describedby="no-documents-description"
        data-closing={confirmationAction !== null}
        onCancel={(event) => {
          event.preventDefault();
          closeConfirmation();
        }}
        onAnimationEnd={(event) => {
          if (event.target === event.currentTarget && !event.nativeEvent.pseudoElement && confirmationAction !== null) {
            finishClosingConfirmation();
          }
        }}
      >
        <div className={styles.dialogHeader}>
          <span className={styles.dialogIcon}><FiFileText size={20} aria-hidden="true" /></span>
          <button
            type="button"
            className={styles.closeButton}
            aria-label="Close confirmation"
            onClick={() => closeConfirmation()}
          >
            <FiX size={20} aria-hidden="true" />
          </button>
        </div>
        <h2 ref={confirmationTitleRef} id="no-documents-title" tabIndex={-1}>Continue without documents?</h2>
        <p id="no-documents-description">
          No files are attached to your question. Would you like to continue without documents?
        </p>
        <div className={styles.dialogActions}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => {
              if (confirmationAction !== null) return;
              // Keep the picker inside the click gesture for Safari.
              fileInputRef.current?.click();
              closeConfirmation();
            }}
          >
            Add documents
          </button>
          <button
            type="button"
            className={styles.continueButton}
            onClick={() => closeConfirmation("submit")}
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
  const [phase, setPhase] = useState<IntakePhase>("intake");
  const showIntake = phase === "intake" || phase === "leaving";

  useEffect(() => {
    if (phase !== "preparing") return;
    const timeout = window.setTimeout(() => setPhase("returning"), PREPARATION_PREVIEW_MS);
    return () => window.clearTimeout(timeout);
  }, [phase]);

  if (phase === "dashboard") {
    return <DashboardWorkspace />;
  }

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
      <AppHeader />

      <main className={styles.content} id="main-content">
        <div className={styles.composer}>
          {showIntake ? (
            <div
              key="intake"
              className={styles.intakeStage}
              data-leaving={phase === "leaving"}
              inert={phase === "leaving"}
              onAnimationEnd={(event) => {
                if (event.target === event.currentTarget && phase === "leaving") setPhase("preparing");
              }}
            >
              <div className={styles.intro}>
                <h1>Find the facts that could change your case.</h1>
                <p>Add your documents, confirm the facts, and explore what could shift the outcome.</p>
              </div>
              <CaseIntakeForm
                draft={draft}
                onDraftChange={setDraft}
                onSubmit={(next) => {
                  if (phase !== "intake") return;
                  setDraft(next);
                  setPhase("leaving");
                }}
              />
            </div>
          ) : (
            <div
              key="preparation"
              className={styles.preparationStage}
              data-leaving={phase === "returning"}
              onAnimationEnd={(event) => {
                if (event.target === event.currentTarget && phase === "returning") setPhase("dashboard");
              }}
            >
              <CasePreparationPreview hasDocuments={draft.documents.length > 0} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
