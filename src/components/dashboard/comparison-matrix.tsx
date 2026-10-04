import { useRef, type CSSProperties, type UIEvent } from "react";
import { FiAlignLeft, FiCheckCircle, FiEdit3, FiInfo, FiXCircle } from "react-icons/fi";
import { decisionLabel, decisionStatusChange, factLabel, factValueLabel } from "@/lib/dashboard/presentation";
import type { DashboardDetail, DashboardDossier, FactorDefinition, FactValue } from "@/types/dashboard";
import { FactValueCell } from "./fact-value-cell";
import styles from "./dashboard.module.css";

export function CaseFactsTable({ dossier, original, factors, selectedFactor, detail, onInspect, onFactChange, onFactSelect }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  factors: FactorDefinition[];
  selectedFactor: string;
  detail: DashboardDetail | null;
  onInspect: (detail: DashboardDetail, trigger: HTMLButtonElement) => void;
  onFactChange: (id: string, value: FactValue) => void;
  onFactSelect: (id: string) => void;
}) {
  const headerRef = useRef<HTMLTableSectionElement>(null);
  const bodyRef = useRef<HTMLTableSectionElement>(null);
  const columnStyle: CSSProperties & { "--precedent-count": number } = { "--precedent-count": dossier.decisions.length };
  const results = dossier.resultat.decisions;
  const retained = results.filter((decision) => decision.retenue).length;

  function syncHorizontalScroll(event: UIEvent<HTMLTableSectionElement>) {
    const source = event.currentTarget;
    const target = source === headerRef.current ? bodyRef.current : headerRef.current;
    if (target && Math.abs(target.scrollLeft - source.scrollLeft) > 0.5) {
      target.scrollLeft = source.scrollLeft;
    }
  }

  return (
    <>
      <div className={styles.matrixScroll} role="region" aria-label="Case facts and precedents">
        <table className={styles.matrix} style={columnStyle} role="table">
          <caption className={styles.srOnly}>Case facts beside precedents. Your case values are editable. Precedent buttons open a detail panel.</caption>
          <thead ref={headerRef} onScroll={syncHorizontalScroll} role="rowgroup"><tr role="row">
            <th scope="col" role="columnheader"><span className={styles.columnLabel}><FiAlignLeft size={16} aria-hidden="true" />Case fact</span></th>
            <th scope="col" role="columnheader" className={styles.caseColumn}>
              <span className={styles.columnLabel}><FiEdit3 size={16} aria-hidden="true" />Your case</span>
              <small className={styles.editableColumnHint}>Editable</small>
            </th>
            {dossier.decisions.map((decision) => {
              const result = results.find((item) => item.id === decision.id);
              const StatusIcon = result?.retenue ? FiCheckCircle : FiXCircle;
              const change = decisionStatusChange(result, original.resultat.decisions.find((item) => item.id === decision.id));
              const selected = detail?.kind === "decision" && detail.decisionId === decision.id && !detail.factorId;
              return <th scope="col" role="columnheader" key={decision.id} data-excluded={!result?.retenue} data-status-changed={change !== null}>
                <button type="button" aria-haspopup="dialog" aria-pressed={selected} aria-controls={selected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "decision", decisionId: decision.id }, event.currentTarget)}>
                  <span className={styles.columnLabel}><StatusIcon className={styles.retentionIcon} data-retained={result?.retenue === true} size={16} aria-hidden="true" />{decisionLabel(decision.intitule)}</span>
                  <small className={styles.decisionState}>
                    <span>{change ?? (result?.retenue ? "Retained" : "Excluded")}</span>
                    {change && <span className={styles.changeReason}>See why <FiInfo size={12} aria-hidden="true" /></span>}
                  </small>
                </button>
              </th>;
            })}
          </tr></thead>
          <tbody ref={bodyRef} onScroll={syncHorizontalScroll} role="rowgroup" tabIndex={0} aria-label="Case facts; scroll horizontally for more precedents">{factors.map((factor) => {
            const factSelected = detail?.kind === "fact" && detail.factorId === factor.id;
            return (
              <tr key={factor.id} role="row" data-selected={factor.id === selectedFactor}>
                <th scope="row" role="rowheader"><button type="button" className={styles.factCell} aria-haspopup="dialog" aria-pressed={factSelected} aria-controls={factSelected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "fact", factorId: factor.id }, event.currentTarget)}>
                  {factLabel(factor.id)}
                  {dossier.resultat.facteurs[factor.id]?.est_pivot && <span className={styles.pivotDot} aria-label="Pivot fact" />}
                </button></th>
                <td className={styles.caseColumn} role="cell">
                  <FactValueCell label={`Edit your case: ${factLabel(factor.id)}`} value={dossier.cas.facteurs[factor.id]} originalValue={original.cas.facteurs[factor.id]} onChange={(value) => onFactChange(factor.id, value)} onActivate={() => onFactSelect(factor.id)} />
                </td>
                {dossier.decisions.map((decision) => {
                  const result = results.find((item) => item.id === decision.id);
                  const selected = detail?.kind === "decision" && detail.decisionId === decision.id && detail.factorId === factor.id;
                  return <td key={decision.id} role="cell" data-excluded={!result?.retenue}>
                    <button type="button" className={styles.precedentCell} title="View supporting information" aria-label={`${decisionLabel(decision.intitule)}, ${factLabel(factor.id)}: ${factValueLabel(decision.facteurs[factor.id])}. Read-only. View supporting information`} aria-haspopup="dialog" aria-pressed={selected} aria-controls={selected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "decision", decisionId: decision.id, factorId: factor.id }, event.currentTarget)}>
                      <span>{factValueLabel(decision.facteurs[factor.id])}</span><FiInfo size={14} aria-hidden="true" />
                    </button>
                  </td>;
                })}
              </tr>
            );
          })}</tbody>
        </table>
      </div>
      <div className={styles.matrixLegend}>
        <span>{retained} of {results.length} precedents retained</span>
        <span><span className={styles.pivotDot} />Pivot fact</span>
        <span>Greyed = excluded</span>
      </div>
    </>
  );
}
