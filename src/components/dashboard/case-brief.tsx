import { FiHelpCircle } from "react-icons/fi";
import { factCopy, factLabel, factValueLabel, outcomeLabel, percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier } from "@/types/dashboard";
import styles from "./dashboard.module.css";

// Answer first: the leading position, then what to ask next. Read from the returned analysis only.
export function CaseBrief({ dossier, pending, error, onFactSelect }: {
  dossier: DashboardDossier;
  pending: boolean;
  error: string | null;
  onFactSelect: (factorId: string) => void;
}) {
  const { resultat: result, grille: grid } = dossier;
  const { majeure, prediction } = result;
  const [low, high] = prediction.intervalle;
  // The interval is returned for the employment outcome; show it for the leading outcome.
  const [leadLow, leadHigh] = majeure.issue ? [low, high] : [1 - high, 1 - low];
  const openQuestions = result.pivots.filter((id) => result.facteurs[id]?.type === "a_documenter");

  return (
    <section className={styles.brief} aria-labelledby="brief-title" aria-busy={pending}>
      <div className={styles.briefPosition}>
        <h2 id="brief-title" className={styles.briefEyebrow}>Leading position</h2>
        <p className={styles.briefAnswer}>
          <strong>{outcomeLabel(majeure.issue, grid.issue)}</strong> {percent(majeure.probabilite)}
        </p>
        <p className={styles.briefMeta}>
          {percent(dossier.parametres.niveau_intervalle)} interval {percent(leadLow)}–{percent(leadHigh)}
          {prediction.incertain && <span className={styles.badge}>Uncertain</span>}
          <span className={styles.badge} data-tone={openQuestions.length ? "warning" : "settled"}>{openQuestions.length ? "Provisional" : "Settled"}</span>
        </p>
        {pending && <p className={styles.briefNote} role="status">Updating the analysis…</p>}
        {error && <p className={styles.briefError} role="alert">{error}</p>}
      </div>

      <div className={styles.briefQuestions}>
        <h3 className={styles.briefHeading}><FiHelpCircle size={15} aria-hidden="true" />Questions for the data room</h3>
        {openQuestions.length ? <ol className={styles.questionList}>
          {openQuestions.map((id) => {
            const factor = grid.facteurs.find((item) => item.id === id);
            const analysis = result.facteurs[id];
            return <li key={id}>
              <button type="button" className={styles.questionButton} onClick={() => onFactSelect(id)}>
                <span>{factor ? factCopy(factor).question : factLabel(id)}</span>
                <span className={styles.questionImpact}>If yes {percent(analysis.probabilite_si_vrai)} · If no {percent(analysis.probabilite_si_faux)} employment</span>
              </button>
            </li>;
          })}
        </ol> : <p className={styles.briefNote}>No unknown fact would change the outcome on its own.</p>}
        {!openQuestions.length && result.pivots_combines.length > 0 && <p className={styles.briefNote}>
          Facts that would change it together: {result.pivots_combines[0].facteurs.map((id, index) => `${factLabel(id)} (${factValueLabel(result.pivots_combines[0].valeurs[index])})`).join(" + ")}.
        </p>}
      </div>
    </section>
  );
}
