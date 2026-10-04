import { FiChevronDown, FiZap } from "react-icons/fi";
import { factCopy, factLabel, percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier, FactValue } from "@/types/dashboard";
import { FactValueControl } from "./fact-value-control";
import styles from "./dashboard.module.css";

export function PivotInsight({ dossier, original, selectedFactor, onFactChange }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  selectedFactor: string;
  onFactChange: (id: string, value: FactValue) => void;
}) {
  const factor = dossier.grille.facteurs.find((item) => item.id === selectedFactor);
  if (!factor) return null;
  const copy = factCopy(factor);
  const analysis = original.resultat.facteurs[selectedFactor];
  return (
    <section className={styles.pivotInsight} aria-labelledby="pivot-title">
      <div className={styles.pivotEyebrow}><FiZap size={15} aria-hidden="true" />{analysis.est_pivot ? "A pivotal question" : "Explore a fact"}</div>
      <div className={styles.pivotQuestion}>
        <h2 id="pivot-title">{copy.question}</h2>
        <div className={styles.pivotControls}>
          <FactValueControl label={copy.question} value={dossier.cas.facteurs[selectedFactor]} onChange={(value) => onFactChange(selectedFactor, value)} />
        </div>
      </div>
      <p className={styles.pivotHint}>Explore one fact at a time.</p>
      <details className={styles.factDetails}>
        <summary><FiChevronDown size={12} aria-hidden="true" />Why this fact?</summary>
        <p>Starting from the original case, the employment estimate is {percent(analysis.probabilite_si_vrai)} if Yes and {percent(analysis.probabilite_si_faux)} if No.</p>
        {original.cas.preuves[selectedFactor]?.extrait && <blockquote lang="fr">“{original.cas.preuves[selectedFactor].extrait}”</blockquote>}
        {dossier.resultat.pivots_combines.length > 0 && <p>Combined pivots: {dossier.resultat.pivots_combines.map((pair) => pair.facteurs.map(factLabel).join(" + ")).join("; ")}. These require a combined simulation.</p>}
      </details>
    </section>
  );
}
