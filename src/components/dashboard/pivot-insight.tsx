import { useId, type Ref } from "react";
import { FiZap } from "react-icons/fi";
import { factCopy } from "@/lib/dashboard/presentation";
import type { DashboardDossier, FactValue } from "@/types/dashboard";
import { FactValueControl } from "./fact-value-control";
import styles from "./dashboard.module.css";

export function PivotInsight({ dossier, original, selectedFactor, onFactChange, compact = false, ref }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  selectedFactor: string;
  onFactChange: (id: string, value: FactValue) => void;
  compact?: boolean;
  ref?: Ref<HTMLElement>;
}) {
  const headingId = useId();
  const factor = dossier.grille.facteurs.find((item) => item.id === selectedFactor);
  if (!factor) return null;
  const copy = factCopy(factor);
  const analysis = original.resultat.facteurs[selectedFactor];
  return (
    <section ref={ref} className={styles.pivotInsight} data-compact={compact} aria-labelledby={headingId}>
      <div className={styles.pivotEyebrow}><FiZap size={15} aria-hidden="true" />{analysis.est_pivot ? "A pivotal question" : "Explore a fact"}</div>
      <div className={styles.pivotQuestion}>
        <h2 key={selectedFactor} className={styles.questionUpdate} id={headingId}>{copy.question}</h2>
        <div className={styles.pivotControls}>
          <FactValueControl label={copy.question} value={dossier.cas.facteurs[selectedFactor]} onChange={(value) => onFactChange(selectedFactor, value)} />
        </div>
      </div>
    </section>
  );
}
