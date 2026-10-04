import type { Ref } from "react";
import { FiArrowRight } from "react-icons/fi";
import { factLabel, factValueLabel, outcomeLabel, percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier, FactOverride } from "@/types/dashboard";
import { DashboardPanel } from "./dashboard-panel";
import styles from "./dashboard.module.css";

export function BalancePanel({ dossier, originalProbability, override, scoreRef }: {
  dossier: DashboardDossier;
  originalProbability: number;
  override: FactOverride | null;
  scoreRef: Ref<HTMLDivElement>;
}) {
  const prediction = dossier.resultat.prediction;
  const [low, high] = prediction.intervalle;
  const labels = dossier.grille.issue;
  const isSimulation = override !== null;
  const pointChange = Math.round(prediction.probabilite * 100) - Math.round(originalProbability * 100);
  const changeLabel = `${pointChange > 0 ? "+" : pointChange < 0 ? "−" : ""}${Math.abs(pointChange)} ${Math.abs(pointChange) === 1 ? "point" : "points"}`;

  return (
    <DashboardPanel id="balance-title" title="The balance">
      <div className={styles.balanceBody}>
        <div className={styles.score}>
          <div ref={scoreRef} className={styles.scoreValue}><span key={prediction.probabilite} className={styles.valueUpdate}>{percent(prediction.probabilite)}</span></div>
          <span>Employment estimate</span>
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
      {override && <div className={styles.estimateChange}>
        <p className={styles.changedFact}>{factLabel(override.factorId)} <strong>{factValueLabel(override.value)}</strong></p>
        <div className={styles.estimateComparison} role="group" aria-label={`Employment estimate: originally ${percent(originalProbability)}, now ${percent(prediction.probabilite)}. Change of ${pointChange} percentage points.`}>
          <span className={styles.originalEstimate}>{percent(originalProbability)}</span>
          <FiArrowRight size={14} aria-hidden="true" />
          <strong>{percent(prediction.probabilite)}</strong>
          <span className={styles.pointChange}>{changeLabel}</span>
        </div>
      </div>}
    </DashboardPanel>
  );
}
