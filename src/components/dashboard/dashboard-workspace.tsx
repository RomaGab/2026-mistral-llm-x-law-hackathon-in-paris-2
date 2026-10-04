"use client";

import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { analyseCase, ApiError } from "@/lib/api/client";
import { AppBrand } from "@/components/ui/app-brand";
import { decisionStatusChange, factLabel, factValueLabel, percent } from "@/lib/dashboard/presentation";
import { getDashboardPreview } from "@/mocks/dashboard";
import type { DashboardDetail, DashboardDossier, FactOverride, FactValue } from "@/types/dashboard";
import { BalancePanel } from "./balance-panel";
import { CaseBrief } from "./case-brief";
import { CaseFactsTable } from "./comparison-matrix";
import { DashboardPanel } from "./dashboard-panel";
import { EvidencePanel } from "./evidence-panel";
import { FloatingAnalysisSummary } from "./floating-analysis-summary";
import styles from "./dashboard.module.css";

function overrideKey(override: FactOverride) {
  return `${override.factorId}:${override.value === null ? "unknown" : override.value}`;
}

function firstQuestion(dossier: DashboardDossier) {
  return dossier.resultat.pivots[0] ?? dossier.grille.facteurs.find((factor) => dossier.cas.facteurs[factor.id] === null)?.id ?? dossier.grille.facteurs[0].id;
}

// With `initialDossier` (a real analysis from the backend), each fact change asks the backend for a
// simulation. Without it (the /dashboard route), the frozen fixtures are shown as before.
export function DashboardWorkspace({ initialDossier }: { initialDossier?: DashboardDossier }) {
  const [original] = useState<DashboardDossier>(() => initialDossier ?? getDashboardPreview(null));
  const live = initialDossier !== undefined;
  const [override, setOverride] = useState<FactOverride | null>(null);
  const [simulations, setSimulations] = useState<Record<string, DashboardDossier>>({});
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const latestKey = useRef<string | null>(null);
  const [selectedFactor, setSelectedFactor] = useState(() => firstQuestion(original));
  const [detail, setDetail] = useState<DashboardDetail | null>(null);
  const [detailClosing, setDetailClosing] = useState(false);
  const [floatingHeight, setFloatingHeight] = useState(0);
  const scoreRef = useRef<HTMLDivElement>(null);
  const detailTriggerRef = useRef<HTMLButtonElement | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const simulated = override ? (live ? simulations[overrideKey(override)] : getDashboardPreview(override)) : original;
  const pending = override !== null && !simulated;
  // While a simulation is pending, keep the last analysis and show only the edited fact.
  const dossier = simulated ?? (override
    ? { ...original, cas: { ...original.cas, facteurs: { ...original.cas.facteurs, [override.factorId]: override.value } } }
    : original);
  const floatingStyle: CSSProperties & { "--floating-summary-height": string } = {
    "--floating-summary-height": `${floatingHeight}px`,
  };
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
    const next = value === original.cas.facteurs[factorId] ? null : { factorId, value };
    setOverride(next);
    setSimulationError(null);
    latestKey.current = next ? overrideKey(next) : null;
    if (!live || !next || simulations[overrideKey(next)]) return;
    const key = overrideKey(next);
    analyseCase(original.cas.id, { [factorId]: value })
      .then((result) => setSimulations((previous) => ({ ...previous, [key]: result })))
      .catch((error: unknown) => {
        if (latestKey.current !== key) return;
        setSimulationError(error instanceof ApiError ? error.message : "The simulation failed.");
      });
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
          <CaseBrief dossier={dossier} pending={pending} error={simulationError} onFactSelect={selectCaseFact} />
          <div className={styles.analysisSummary} aria-busy={pending}>
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
