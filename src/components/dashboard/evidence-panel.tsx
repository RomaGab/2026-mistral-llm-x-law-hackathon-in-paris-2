import { useEffect, useLayoutEffect, useRef } from "react";
import { FiArrowUpRight, FiX } from "react-icons/fi";
import { decisionLabel, decisionStatusChange, factCopy, factLabel, factValueLabel, percent } from "@/lib/dashboard/presentation";
import { englishExcerpt, englishExclusionReason } from "@/lib/dashboard/source-copy";
import type { DashboardDetail, DashboardDossier, FactorDefinition } from "@/types/dashboard";
import styles from "./dashboard.module.css";

export function EvidencePanel({ detail, dossier, original, closing, preserveFocus, onClose, onExited }: {
  detail: DashboardDetail;
  dossier: DashboardDossier;
  original: DashboardDossier;
  closing: boolean;
  preserveFocus: boolean;
  onClose: () => void;
  onExited: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const factor = original.grille.facteurs.find((item) => item.id === detail.factorId);
  const title = detail.kind === "fact" ? "Your case evidence" : detail.factorId ? "Precedent evidence" : "Precedent details";

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    // Dropdown evidence stays nonmodal so the native select remains usable.
    const compact = window.matchMedia("(max-width: 767px)");
    const previousOverflow = document.body.style.overflow;
    function syncMode() {
      if (!dialog) return;
      const modal = compact.matches && !preserveFocus;
      if (dialog.open && dialog.matches(":modal") !== modal) dialog.close();
      if (!dialog.open) {
        if (preserveFocus) {
          // show() runs native autofocus; opening directly leaves the select alone.
          dialog.open = true;
        } else if (modal) {
          dialog.showModal();
        } else {
          dialog.show();
        }
      }
      document.body.style.overflow = modal ? "hidden" : previousOverflow;
      if (!preserveFocus) headingRef.current?.focus({ preventScroll: true });
    }
    syncMode();
    compact.addEventListener("change", syncMode);
    return () => {
      compact.removeEventListener("change", syncMode);
      document.body.style.overflow = previousOverflow;
    };
  }, [preserveFocus]);

  useEffect(() => {
    const dialog = dialogRef.current;
    return () => dialog?.close();
  }, []);

  useLayoutEffect(() => {
    if (!preserveFocus) headingRef.current?.focus({ preventScroll: true });
    bodyRef.current?.scrollTo({ top: 0 });
  }, [detail, preserveFocus]);

  return (
    <dialog ref={dialogRef} id="case-details" className={styles.evidencePanel} data-closing={closing} data-preserve-focus={preserveFocus} aria-labelledby="evidence-title" onAnimationEnd={(event) => {
      if (event.target === event.currentTarget && !event.nativeEvent.pseudoElement && closing) onExited();
    }} onCancel={(event) => {
      event.preventDefault();
      onClose();
    }}>
      <header className={styles.evidenceHeader}>
        <h2 id="evidence-title" ref={headingRef} tabIndex={-1}>{title}</h2>
        <button type="button" className={styles.closePanel} aria-label="Close details" disabled={closing} onClick={onClose}><FiX size={20} aria-hidden="true" /></button>
      </header>
      <div className={styles.evidenceBody} ref={bodyRef}>
        <div key={`${detail.kind}:${detail.factorId ?? ""}:${detail.kind === "decision" ? detail.decisionId : ""}`} className={styles.evidenceContent}>{detail.kind === "fact"
          ? factor && <FactEvidence dossier={original} factor={factor} />
          : <DecisionDetail dossier={dossier} original={original} decisionId={detail.decisionId} factorId={detail.factorId} />}</div>
      </div>
    </dialog>
  );
}

function EvidenceExcerpt({ excerpt }: { excerpt: string | null | undefined }) {
  if (!excerpt) return <p>No supporting excerpt was found in the sources.</p>;
  const translation = englishExcerpt(excerpt);
  // Legal sources are quoted verbatim: without a reviewed translation, show the original French.
  if (!translation) return <figure className={styles.evidenceExcerpt}>
    <blockquote lang="fr">“{excerpt}”</blockquote>
    <figcaption>Original excerpt (French)</figcaption>
  </figure>;
  return <figure className={styles.evidenceExcerpt}>
    <blockquote lang="en">“{translation}”</blockquote>
    <figcaption>English translation</figcaption>
  </figure>;
}

function FactEvidence({ dossier, factor }: { dossier: DashboardDossier; factor: FactorDefinition }) {
  const copy = factCopy(factor);
  const evidence = dossier.cas.preuves?.[factor.id]?.extrait;
  const analysis = dossier.resultat.facteurs[factor.id];
  return <div className={styles.factEvidence}>
    <h3>{copy.question}</h3>
    <EvidenceExcerpt excerpt={evidence} />
    {analysis && <p>From the original case: Yes {percent(analysis.probabilite_si_vrai)} · No {percent(analysis.probabilite_si_faux)} employment estimate.</p>}
  </div>;
}

function DecisionDetail({ dossier, original, decisionId, factorId }: { dossier: DashboardDossier; original: DashboardDossier; decisionId: string; factorId?: string }) {
  const decision = dossier.decisions.find((item) => item.id === decisionId);
  const result = dossier.resultat.decisions.find((item) => item.id === decisionId);
  if (!decision || !result) return null;
  const change = decisionStatusChange(result, original.resultat.decisions.find((item) => item.id === decisionId));
  const missing = result.arguments_manquants?.filter((argument) => dossier.cas.facteurs[argument.facteur] === null) ?? [];
  const alignment = factorId ? result.alignement[factorId] : null;
  const evidence = factorId ? decision.preuves?.[factorId]?.extrait : null;
  return (
    <div className={styles.decisionDetail}>
      <div className={styles.decisionHeading}><h3>{decisionLabel(decision.intitule)}</h3><span className={styles.status}>{result.retenue ? "Retained" : "Excluded"}</span></div>
      {change && <p className={styles.decisionChangeNote}>{change} compared with the original case.</p>}
      {factorId ? <>
        <h4>{factLabel(factorId)}</h4>
        <p>Precedent: {factValueLabel(decision.facteurs[factorId])} · Your case: {factValueLabel(dossier.cas.facteurs[factorId])}</p>
        <p>{alignment === "identique" ? "This fact matches your case." : alignment === "oppose" ? "This fact differs from your case." : "The comparison is unknown because a fact has not been established."}</p>
        <EvidenceExcerpt excerpt={evidence} />
      </> : <p className={styles.decisionMeta}>{decision.intitule.includes("[FICTIF]") ? "Fictional precedent" : "Precedent"} · {new Date(`${decision.date}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })} · Similarity {percent(result.proximite)}</p>}
      {result.motif_exclusion && <p className={styles.sourceNote}>{englishExclusionReason(result.motif_exclusion, dossier.grille.facteurs)}</p>}
      {!factorId && <>
        {result.s_applique_a_fortiori === true && <p>This precedent applies even more strongly to your case.</p>}
        {missing.length > 0 && <><h4>Evidence to establish</h4><ul>{missing.map((argument) => <li key={argument.facteur}>{factLabel(argument.facteur)}</li>)}</ul></>}
        {!!result.arguments_contraires?.length && <><h4>What distinguishes your case</h4><ul>{result.arguments_contraires.map((argument) => <li key={argument.facteur}>{factLabel(argument.facteur)}</li>)}</ul></>}
      </>}
      {decision.url && <a href={decision.url} target="_blank" rel="noreferrer">Read the decision <FiArrowUpRight size={12} aria-hidden="true" /></a>}
    </div>
  );
}
