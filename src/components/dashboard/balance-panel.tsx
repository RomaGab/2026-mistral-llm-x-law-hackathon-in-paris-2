import { useState } from "react";
import { FiInfo } from "react-icons/fi";
import { outcomeLabel, percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier } from "@/types/dashboard";
import { DashboardPanel } from "./dashboard-panel";
import styles from "./dashboard.module.css";

export function BalancePanel({ dossier, originalProbability, isSimulation, submittedQuestion }: {
  dossier: DashboardDossier;
  originalProbability: number;
  isSimulation: boolean;
  submittedQuestion?: string;
}) {
  const [showExplanation, setShowExplanation] = useState(false);
  const prediction = dossier.resultat.prediction;
  const [low, high] = prediction.intervalle;
  const labels = dossier.grille.issue;
  return (
    <DashboardPanel id="balance-title" title="The balance" action={
      <div className={styles.balanceActions}>
        <span className={styles.status}>{prediction.incertain ? "Uncertain" : "Clear direction"}</span>
        <button type="button" className={styles.infoButton} aria-label="About this estimate" aria-expanded={showExplanation} aria-controls="balance-explanation" onClick={() => setShowExplanation(!showExplanation)}><FiInfo size={17} aria-hidden="true" /></button>
      </div>
    }>
      <div className={styles.balanceBody}>
        <div className={styles.score}>
          <div className={styles.scoreValue}>{percent(prediction.probabilite)}</div>
          <span>Employment estimate</span>
          {isSimulation && <small>Original: {percent(originalProbability)}</small>}
        </div>
        <div className={styles.balanceChart}>
          <div className={styles.outcomeLabels}>
            <span data-leading={!prediction.issue}>{outcomeLabel(false, labels)}</span>
            <span data-leading={prediction.issue}>{outcomeLabel(true, labels)}</span>
          </div>
          <div className={styles.balanceTrack} role="img" aria-label={`Employment estimate ${percent(prediction.probabilite)}. ${percent(dossier.parametres.niveau_intervalle)} interval: ${percent(low)} to ${percent(high)}.`}>
            <div className={styles.balanceRule} />
            <div className={styles.interval} style={{ left: percent(low), width: percent(high - low) }} />
            <div className={styles.midpoint} />
            {isSimulation && <div className={styles.originalMarker} style={{ left: percent(originalProbability) }} />}
            <div className={styles.balanceMarker} style={{ left: percent(prediction.probabilite) }} />
          </div>
          <div className={styles.scaleLabels}><span>0%</span><span>50%</span><span>100%</span></div>
          <div className={styles.intervalCaption}>
            <span className={styles.intervalSwatch} aria-hidden="true" />
            {percent(dossier.parametres.niveau_intervalle)} interval · {percent(low)}–{percent(high)}
          </div>
        </div>
      </div>
      <div className={styles.balanceNote} id="balance-explanation" hidden={!showExplanation}>
        <p>{prediction.incertain
        ? "The interval crosses the midpoint. More evidence is needed to resolve the uncertainty."
        : `The interval falls on the ${outcomeLabel(prediction.issue, labels).toLowerCase()} side of the midpoint.`}</p>
        {submittedQuestion && <><p>Your draft is saved. This example does not analyse your documents.</p><blockquote>{submittedQuestion}</blockquote></>}
        {dossier.resultat.avertissements.map((warning) => <p key={warning} lang="fr">{warning}</p>)}
      </div>
    </DashboardPanel>
  );
}
