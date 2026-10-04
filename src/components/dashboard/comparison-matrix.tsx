import { FiArrowUpRight, FiMinus } from "react-icons/fi";
import { decisionLabel, factLabel, percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier } from "@/types/dashboard";
import styles from "./dashboard.module.css";

function AlignmentMark({ alignment }: { alignment: string }) {
  const label = alignment === "identique" ? "Same fact" : alignment === "oppose" ? "Opposite fact" : "Unknown";
  return <span className={styles.alignment} data-alignment={alignment} aria-label={label} title={label}>
    {alignment === "inconnu" ? "?" : alignment === "oppose" ? <span className={styles.openDot} /> : <span className={styles.solidDot} />}
  </span>;
}

export function ComparisonMatrix({ dossier, selectedFactor, onSelectFactor, selectedDecision, onSelectDecision }: {
  dossier: DashboardDossier;
  selectedFactor: string;
  onSelectFactor: (id: string) => void;
  selectedDecision: string | null;
  onSelectDecision: (id: string) => void;
}) {
  const results = dossier.resultat.decisions;
  const retained = results.filter((decision) => decision.retenue).length;
  return (
    <>
      <p className={styles.comparisonNote}>{retained} of {results.length} retained · Select a decision to see why.</p>
      <div className={styles.matrixScroll} tabIndex={0} role="region" aria-label="Precedent comparison matrix, scroll for more facts and decisions">
        <table className={styles.matrix}>
          <caption className={styles.srOnly}>Fictional precedents compared with the example case. Excluded decisions remain visible.</caption>
          <thead><tr><th scope="col">Case fact</th>{dossier.decisions.map((decision) => {
            const result = results.find((item) => item.id === decision.id);
            return <th scope="col" key={decision.id} data-excluded={!result?.retenue}>
              <button type="button" aria-pressed={selectedDecision === decision.id} onClick={() => onSelectDecision(decision.id)}>
                {decisionLabel(decision.intitule)}<FiArrowUpRight size={12} aria-hidden="true" />
                <small>{result?.retenue ? "Retained" : "Excluded"}</small>
              </button>
            </th>;
          })}</tr></thead>
          <tbody>{dossier.grille.facteurs.map((factor) => <tr key={factor.id} data-selected={factor.id === selectedFactor}>
            <th scope="row"><button type="button" onClick={() => onSelectFactor(factor.id)} aria-pressed={factor.id === selectedFactor}>{factLabel(factor.id)}{dossier.resultat.facteurs[factor.id]?.est_pivot && <span className={styles.pivotDot} aria-label="Pivot fact" />}</button></th>
            {results.map((decision) => <td key={decision.id} data-excluded={!decision.retenue}><AlignmentMark alignment={decision.alignement[factor.id] ?? "inconnu"} /></td>)}
          </tr>)}</tbody>
        </table>
      </div>
      <div className={styles.matrixLegend}>
        <span><span className={styles.solidDot} />Same</span>
        <span><span className={styles.openDot} />Opposite</span>
        <span><b>?</b>Unknown</span>
        <span><FiMinus size={13} aria-hidden="true" />Greyed = excluded</span>
      </div>
    </>
  );
}

export function DecisionDetail({ dossier, decisionId }: { dossier: DashboardDossier; decisionId: string }) {
  const decision = dossier.decisions.find((item) => item.id === decisionId);
  const result = dossier.resultat.decisions.find((item) => item.id === decisionId);
  if (!decision || !result) return null;
  const missing = result.arguments_manquants?.filter((argument) => dossier.cas.facteurs[argument.facteur] === null) ?? [];
  return (
    <div className={styles.decisionDetail}>
      <div className={styles.decisionHeading}><h3>{decisionLabel(decision.intitule)}</h3><span className={styles.status}>{result.retenue ? "Retained" : "Excluded"}</span></div>
      <p className={styles.decisionMeta}>Fictional precedent · {new Date(`${decision.date}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })} · Similarity {percent(result.proximite)}</p>
      {result.motif_exclusion && <p className={styles.sourceNote} lang="fr">{result.motif_exclusion}</p>}
      {result.s_applique_a_fortiori === true && <p>This precedent applies a fortiori to the case.</p>}
      {missing.length > 0 && <><h4>Evidence to establish</h4><ul>{missing.map((argument) => <li key={argument.facteur}>{factLabel(argument.facteur)}</li>)}</ul></>}
      {!!result.arguments_contraires?.length && <><h4>What distinguishes your case</h4><ul>{result.arguments_contraires.map((argument) => <li key={argument.facteur}>{factLabel(argument.facteur)}</li>)}</ul></>}
      {decision.url && <a href={decision.url} target="_blank" rel="noreferrer">Read the decision <FiArrowUpRight size={12} aria-hidden="true" /></a>}
    </div>
  );
}
