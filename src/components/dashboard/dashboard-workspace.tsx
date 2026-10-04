"use client";

import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { AppBrand } from "@/components/ui/app-brand";
import { decisionStatusChange, factLabel, factValueLabel, percent } from "@/lib/dashboard/presentation";
import { exampleDossier, getDashboardPreview } from "@/mocks/dashboard";
import type { DashboardDetail, FactOverride, FactValue } from "@/types/dashboard";
import { BalancePanel } from "./balance-panel";
import { CaseFactsTable } from "./comparison-matrix";
import { DashboardPanel } from "./dashboard-panel";
import { EvidencePanel } from "./evidence-panel";
import { FloatingAnalysisSummary } from "./floating-analysis-summary";
import styles from "./dashboard.module.css";

export function DashboardWorkspace() {
  const [override, setOverride] = useState<FactOverride | null>(null);
  const [selectedFactor, setSelectedFactor] = useState("sanction_deconnexion");
  const [detail, setDetail] = useState<DashboardDetail | null>(null);
  const [detailClosing, setDetailClosing] = useState(false);
  const [floatingHeight, setFloatingHeight] = useState(0);
  const scoreRef = useRef<HTMLDivElement>(null);
  const detailTriggerRef = useRef<HTMLButtonElement | null>(null);
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

  function selectCaseFact(factorId: string) {
    setSelectedFactor(factorId);
    if (detail) {
      // Keep focus on the case selector when switching away from evidence.
      detailTriggerRef.current = null;
      setDetailClosing(true);
    }
  }

  function inspectDetail(nextDetail: DashboardDetail, trigger: HTMLButtonElement) {
    detailTriggerRef.current = trigger;
    setDetailClosing(false);
    setDetail(nextDetail);
    if (nextDetail.factorId) setSelectedFactor(nextDetail.factorId);
  }

  function closeDetail() {
    setDetailClosing(true);
  }

  function finishClosingDetail() {
    setDetail(null);
    setDetailClosing(false);
    requestAnimationFrame(() => detailTriggerRef.current?.focus({ preventScroll: true }));
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}><AppBrand /></header>
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
          <div className={styles.factsSection}>
            <DashboardPanel id="facts-title" title="Facts & precedents">
              <CaseFactsTable dossier={dossier} original={original} factors={facts} selectedFactor={selectedFactor} detail={detailClosing ? null : detail} onInspect={inspectDetail} onFactChange={changeFact} onFactSelect={selectCaseFact} />
            </DashboardPanel>
          </div>
          <p className={styles.srOnly} role="status">{override ? `Simulation: ${factLabel(override.factorId)}, ${factValueLabel(override.value)}` : "Original analysis"}. Employment estimate {percent(dossier.resultat.prediction.probabilite)}. {dossier.resultat.decisions.filter((decision) => decision.retenue).length} decisions retained. {changedDecisions.length} precedent statuses changed from the original case.</p>
        </div>
        <FloatingAnalysisSummary dossier={dossier} original={original} selectedFactor={selectedFactor} onFactChange={changeFact} scoreRef={scoreRef} onHeightChange={setFloatingHeight} />
        {detail && <EvidencePanel detail={detail} dossier={dossier} original={original} closing={detailClosing} onClose={closeDetail} onExited={finishClosingDetail} />}
      </main>
    </div>
  );
}
