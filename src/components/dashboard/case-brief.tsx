import { FiAlertTriangle, FiHelpCircle } from "react-icons/fi";
import { decisionLabel, factCopy, factLabel, factValueLabel, outcomeLabel, percent } from "@/lib/dashboard/presentation";
import { englishExclusionReason } from "@/lib/dashboard/source-copy";
import type { DashboardDossier } from "@/types/dashboard";
import styles from "./dashboard.module.css";

// Answer first: everything below is read from the returned analysis; nothing is calculated here.
export function CaseBrief({ dossier, pending, error, onFactSelect }: {
  dossier: DashboardDossier;
  pending: boolean;
  error: string | null;
  onFactSelect: (factorId: string) => void;
}) {
  const { resultat: result, grille: grid } = dossier;
  const { majeure, exception, prediction } = result;
  const [low, high] = prediction.intervalle;
  // The interval is returned for the employment outcome; show it for the leading outcome.
  const [leadLow, leadHigh] = majeure.issue ? [low, high] : [1 - high, 1 - low];
  const openQuestions = result.pivots.filter((id) => result.facteurs[id]?.type === "a_documenter");
  const excluded = result.decisions.filter((decision) => !decision.retenue);
  const title = (id: string) => decisionLabel(dossier.decisions.find((decision) => decision.id === id)?.intitule ?? id);

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

      <div className={styles.briefColumns}>
        <div>
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

        <div>
          {exception && <>
            <h3 className={styles.briefHeading}>Exception</h3>
            <p className={styles.briefText}>
              {outcomeLabel(exception.issue, grid.issue)} {percent(exception.probabilite)}
              {exception.conditions.length > 0 && <> if {exception.conditions.map((condition) => `${factLabel(condition.facteur)}: ${factValueLabel(condition.valeur)}`).join(", or ")}</>}
              {exception.decision_reference && <>. Reference: {title(exception.decision_reference)}</>}.
            </p>
          </>}
          <h3 className={styles.briefHeading}>Excluded precedents</h3>
          {excluded.length ? <ul className={styles.briefList}>
            {excluded.map((decision) => <li key={decision.id}>
              <strong>{title(decision.id)}</strong> — {decision.motif_exclusion ? englishExclusionReason(decision.motif_exclusion, grid.facteurs) : "Excluded."}
            </li>)}
          </ul> : <p className={styles.briefNote}>None: every precedent applies to your facts.</p>}
        </div>
      </div>

      {result.avertissements.length > 0 && <ul className={styles.briefWarnings} aria-label="Warnings">
        {result.avertissements.map((warning) => <li key={warning}><FiAlertTriangle size={14} aria-hidden="true" /><span lang="fr">{warning}</span></li>)}
      </ul>}
    </section>
  );
}
