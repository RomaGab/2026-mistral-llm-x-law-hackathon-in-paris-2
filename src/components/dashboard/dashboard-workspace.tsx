"use client";

import Link from "next/link";
import { useLayoutEffect, useRef, useState } from "react";
import { FiArrowLeft, FiChevronDown, FiColumns, FiList, FiRotateCcw } from "react-icons/fi";
import { AppBrand } from "@/components/ui/app-brand";
import { factLabel, factValueLabel, percent } from "@/lib/dashboard/presentation";
import { exampleDossier, getDashboardPreview } from "@/mocks/dashboard";
import type { FactOverride, FactValue } from "@/types/dashboard";
import { BalancePanel } from "./balance-panel";
import { ComparisonMatrix, DecisionDetail } from "./comparison-matrix";
import { FactToggle } from "./fact-toggle";
import { PivotInsight } from "./pivot-insight";
import styles from "./dashboard.module.css";

export function DashboardWorkspace({ onBack, submittedQuestion }: { onBack?: () => void; submittedQuestion?: string }) {
  const [override, setOverride] = useState<FactOverride | null>(null);
  const [selectedFactor, setSelectedFactor] = useState("sanction_deconnexion");
  const [selectedDecision, setSelectedDecision] = useState<string | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const dossier = getDashboardPreview(override);
  const original = getDashboardPreview(null);
  const isSimulation = override !== null;
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

  return (
    <div className={styles.shell}>
      <header className={styles.header}><AppBrand /><span className={styles.demoBadge}>Demo · Fictional data</span></header>
      <main className={styles.main} id="main-content">
        <div className={styles.toolbar}>
          {onBack ? <button type="button" className={styles.backLink} onClick={onBack}><FiArrowLeft size={15} aria-hidden="true" />Back to your case</button> : <Link className={styles.backLink} href="/"><FiArrowLeft size={15} aria-hidden="true" />New case</Link>}
        </div>
        <div className={styles.pageHeading}>
          <h1 ref={titleRef} tabIndex={-1}>Case analysis</h1>
          {override && <div className={styles.scenarioToolbar}>
            <span className={styles.simulationLabel} title={factLabel(override.factorId) + ": " + factValueLabel(override.value)}>Simulation</span>
            <button type="button" className={styles.resetButton} onClick={() => setOverride(null)}><FiRotateCcw size={14} aria-hidden="true" />Reset</button>
          </div>}
        </div>
        <BalancePanel dossier={dossier} originalProbability={original.resultat.prediction.probabilite} isSimulation={isSimulation} submittedQuestion={submittedQuestion} />
        <PivotInsight dossier={dossier} original={original} selectedFactor={selectedFactor} onFactChange={changeFact} />
        <div className={styles.disclosures}>
          <details className={styles.disclosure}>
            <summary><FiList size={17} aria-hidden="true" /><h2>Review all {dossier.grille.facteurs.length} facts</h2><FiChevronDown className={styles.disclosureChevron} size={16} aria-hidden="true" /></summary>
            <div className={styles.factList}>{facts.map((factor) => <FactToggle
              key={factor.id}
              factor={factor}
              analysis={dossier.resultat.facteurs[factor.id]}
              originalAnalysis={original.resultat.facteurs[factor.id]}
              value={dossier.cas.facteurs[factor.id]}
              originalValue={original.cas.facteurs[factor.id]}
              selected={factor.id === selectedFactor}
              evidence={original.cas.preuves[factor.id]?.extrait}
              onChange={changeFact}
              onInspect={setSelectedFactor}
            />)}</div>
          </details>
          <details className={styles.disclosure}>
            <summary><FiColumns size={17} aria-hidden="true" /><h2>Compare {dossier.decisions.length} decisions</h2><FiChevronDown className={styles.disclosureChevron} size={16} aria-hidden="true" /></summary>
            <ComparisonMatrix dossier={dossier} selectedFactor={selectedFactor} onSelectFactor={setSelectedFactor} selectedDecision={selectedDecision} onSelectDecision={(id) => setSelectedDecision(id === selectedDecision ? null : id)} />
            {selectedDecision && <DecisionDetail dossier={dossier} decisionId={selectedDecision} />}
          </details>
        </div>
        <p className={styles.srOnly} role="status">{override ? `Simulation: ${factLabel(override.factorId)}, ${factValueLabel(override.value)}` : "Original analysis"}. Employment estimate {percent(dossier.resultat.prediction.probabilite)}. {dossier.resultat.decisions.filter((decision) => decision.retenue).length} decisions retained.</p>
      </main>
    </div>
  );
}
