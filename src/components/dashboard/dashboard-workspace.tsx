"use client";

import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { AppHeader } from "@/components/ui/app-header";
import { decisionStatusChange, factLabel, factValueLabel, percent } from "@/lib/dashboard/presentation";
import { exampleDossier, getDashboardPreview } from "@/mocks/dashboard";
import type { DashboardDetail, FactOverride, FactValue } from "@/types/dashboard";
import { BalancePanel } from "./balance-panel";
import { CaseFactsTable } from "./comparison-matrix";
import { EvidencePanel } from "./evidence-panel";
import { FloatingAnalysisSummary } from "./floating-analysis-summary";
import styles from "./dashboard.module.css";

export function DashboardWorkspace() {
  const [override, setOverride] = useState<FactOverride | null>(null);
  const [selectedFactor, setSelectedFactor] = useState("sanction_deconnexion");
  const [detail, setDetail] = useState<DashboardDetail | null>(null);
  const [detailClosing, setDetailClosing] = useState(false);
  const [detailKeepsFocus, setDetailKeepsFocus] = useState(false);
  const [floatingHeight, setFloatingHeight] = useState(0);
  const headerRef = useRef<HTMLElement>(null);
  const scoreRef = useRef<HTMLDivElement>(null);
  const detailTriggerRef = useRef<HTMLButtonElement | HTMLSelectElement | null>(null);
  const restoringDetailFocusRef = useRef(false);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const dossier = getDashboardPreview(override);
  const floatingStyle: CSSProperties & { "--floating-summary-height": string } = {
    "--floating-summary-height": `${floatingHeight}px`,
  };
  const original = getDashboardPreview(null);
  const changedDecisions = dossier.resultat.decisions.filter((decision) => decisionStatusChange(decision, original.resultat.decisions.find((item) => item.id === decision.id)));
  // Keep unknown facts first without moving a focused row after a simulation.
  // Preserve shared grid order within the two groups.
  const facts = [
    ...dossier.grille.facteurs.filter((factor) => original.cas.facteurs[factor.id] === null),
    ...dossier.grille.facteurs.filter((factor) => original.cas.facteurs[factor.id] !== null),
  ];

  useLayoutEffect(() => { titleRef.current?.focus({ preventScroll: true }); }, []);

  function changeFact(factorId: string, value: FactValue) {
    setSelectedFactor(factorId);
    setOverride(value === exampleDossier.cas.facteurs[factorId] ? null : { factorId, value });
  }

  function selectCaseFact(factorId: string, trigger: HTMLSelectElement) {
    // Closing evidence returns focus without immediately reopening it.
    if (restoringDetailFocusRef.current) return;
    inspectDetail({ kind: "fact", factorId }, trigger);
  }

  function inspectDetail(nextDetail: DashboardDetail, trigger: HTMLButtonElement | HTMLSelectElement) {
    detailTriggerRef.current = trigger;
    setDetailClosing(false);
    setDetailKeepsFocus(trigger instanceof HTMLSelectElement);
    setDetail((current) => current?.kind === "fact" && nextDetail.kind === "fact" && current.factorId === nextDetail.factorId ? current : nextDetail);
    if (nextDetail.factorId) setSelectedFactor(nextDetail.factorId);
  }

  function closeDetail() {
    setDetailClosing(true);
  }

  function finishClosingDetail() {
    setDetail(null);
    setDetailClosing(false);
    requestAnimationFrame(() => {
      restoringDetailFocusRef.current = true;
      detailTriggerRef.current?.focus({ preventScroll: true });
      restoringDetailFocusRef.current = false;
    });
  }

  return (
    <div className={styles.shell}>
      <AppHeader ref={headerRef} />
      <main className={styles.main} style={floatingStyle} id="main-content" onKeyDown={(event) => {
        if (event.key === "Escape" && !event.defaultPrevented && detail && !(event.target instanceof HTMLSelectElement)) {
          event.preventDefault();
          closeDetail();
        }
      }}>
        <div className={styles.mainContent}>
          <div className={styles.pageHeading}>
            <h1 ref={titleRef} tabIndex={-1}>Case analysis</h1>
          </div>
          <div className={styles.analysisSummary}>
            <BalancePanel scoreRef={scoreRef} dossier={dossier} originalProbability={original.resultat.prediction.probabilite} override={override} />
          </div>
          <section className={styles.factsSection} aria-labelledby="facts-title">
            <h2 id="facts-title" className={styles.factsHeading}>Facts & precedents</h2>
            <div className={styles.panel}>
              <CaseFactsTable dossier={dossier} original={original} factors={facts} selectedFactor={selectedFactor} detail={detailClosing ? null : detail} onInspect={inspectDetail} onFactChange={changeFact} onFactSelect={selectCaseFact} />
            </div>
          </section>
          <p className={styles.srOnly} role="status">{override ? `Simulation: ${factLabel(override.factorId)}, ${factValueLabel(override.value)}` : "Original analysis"}. Employment estimate {percent(dossier.resultat.prediction.probabilite)}. {dossier.resultat.decisions.filter((decision) => decision.retenue).length} decisions retained. {changedDecisions.length} precedent statuses changed from the original case.</p>
        </div>
        <FloatingAnalysisSummary dossier={dossier} original={original} selectedFactor={selectedFactor} onFactChange={changeFact} scoreRef={scoreRef} headerRef={headerRef} onHeightChange={setFloatingHeight} />
        {detail && <EvidencePanel detail={detail} dossier={dossier} original={original} closing={detailClosing} preserveFocus={detailKeepsFocus} onClose={closeDetail} onExited={finishClosingDetail} />}
      </main>
    </div>
  );
}
