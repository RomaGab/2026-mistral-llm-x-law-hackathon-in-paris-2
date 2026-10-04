import { FiChevronDown, FiZap } from "react-icons/fi";
import { factCopy, factValueLabel, percent } from "@/lib/dashboard/presentation";
import type { FactorAnalysis, FactorDefinition, FactValue } from "@/types/dashboard";
import { FactValueControl } from "./fact-value-control";
import styles from "./dashboard.module.css";

export function FactToggle({ factor, analysis, originalAnalysis, value, originalValue, selected, evidence, onChange, onInspect }: {
  factor: FactorDefinition;
  analysis: FactorAnalysis;
  originalAnalysis: FactorAnalysis;
  value: FactValue;
  originalValue: FactValue;
  selected: boolean;
  evidence?: string | null;
  onChange: (factorId: string, value: FactValue) => void;
  onInspect: (factorId: string) => void;
}) {
  const copy = factCopy(factor);
  const changed = value !== originalValue;
  return (
    <div className={styles.factRow} data-selected={selected} data-changed={changed}>
      <div className={styles.factTopline}>
        <button type="button" className={styles.factLabel} onClick={() => onInspect(factor.id)} aria-pressed={selected}>{copy.label}</button>
        {analysis.est_pivot && <span className={styles.pivotBadge}><FiZap size={11} aria-hidden="true" />Pivot</span>}
      </div>
      <div className={styles.factControls}>
        <FactValueControl label={copy.label} value={value} onChange={(next) => onChange(factor.id, next)} />
        <span className={styles.factMeta}>{changed ? `Was ${factValueLabel(originalValue)}` : value === null ? "To verify" : "From case"}</span>
      </div>
      <details className={styles.factDetails}>
        <summary><FiChevronDown size={12} aria-hidden="true" />Evidence & impact</summary>
        <p>{copy.question}</p>
        {evidence ? <blockquote lang="fr">“{evidence}”</blockquote> : <p>No supporting excerpt in this example.</p>}
        <p>From the original case: Yes {percent(originalAnalysis.probabilite_si_vrai)} · No {percent(originalAnalysis.probabilite_si_faux)} employment estimate.</p>
        {analysis.niveau === "neutralise" && <p>This factor does not affect the model’s score.</p>}
      </details>
    </div>
  );
}
