import { useLayoutEffect, useRef, useState, type CSSProperties, type UIEvent } from "react";
import { FiAlignLeft, FiCheckCircle, FiEdit3, FiInfo, FiXCircle, FiZap } from "react-icons/fi";
import { decisionLabel, decisionStatusChange, factLabel, factValueLabel } from "@/lib/dashboard/presentation";
import type { DashboardDetail, DashboardDossier, FactorDefinition, FactValue } from "@/types/dashboard";
import { FactValueCell } from "./fact-value-cell";
import styles from "./dashboard.module.css";

/** Narrowest a case or precedent column may get before the table scrolls. */
const MIN_COLUMN_WIDTH = 148;

/**
 * Width that makes the visible area end exactly on a column edge: the space beside the sticky
 * fact column is split evenly between as many whole columns as fit.
 */
function wholeColumnWidth(visibleWidth: number, factColumnWidth: number, columnCount: number) {
  const available = visibleWidth - factColumnWidth;
  const visibleColumns = Math.min(columnCount, Math.max(1, Math.floor(available / MIN_COLUMN_WIDTH)));
  return available / visibleColumns;
}

export function CaseFactsTable({ dossier, original, factors, selectedFactor, detail, onInspect, onFactChange, onFactSelect }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  factors: FactorDefinition[];
  selectedFactor: string;
  detail: DashboardDetail | null;
  onInspect: (detail: DashboardDetail, trigger: HTMLButtonElement) => void;
  onFactChange: (id: string, value: FactValue) => void;
  onFactSelect: (id: string, trigger: HTMLSelectElement) => void;
}) {
  const headerRef = useRef<HTMLTableSectionElement>(null);
  const bodyRef = useRef<HTMLTableSectionElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const [columnWidth, setColumnWidth] = useState(MIN_COLUMN_WIDTH);
  const columnCount = dossier.decisions.length + 1;
  const columnStyle: CSSProperties & { "--column-count": number; "--column-width": string } = {
    "--column-count": columnCount,
    "--column-width": `${columnWidth}px`,
  };

  useLayoutEffect(() => {
    const table = tableRef.current;
    const body = bodyRef.current;
    if (!table || !body) return;
    const measure = () => {
      const factColumnWidth = parseFloat(getComputedStyle(table).getPropertyValue("--fact-column")) || 0;
      setColumnWidth(wholeColumnWidth(body.clientWidth, factColumnWidth, columnCount));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(body);
    return () => observer.disconnect();
  }, [columnCount]);
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
        <table ref={tableRef} className={styles.matrix} style={columnStyle} role="table">
          <caption className={styles.srOnly}>Case facts beside precedents. Your case values are editable. Precedent buttons open a detail panel.</caption>
          <thead ref={headerRef} onScroll={syncHorizontalScroll} role="rowgroup"><tr role="row">
            <th scope="col" role="columnheader"><span className={styles.columnLabel}><FiAlignLeft size={16} aria-hidden="true" />Case fact</span></th>
            <th scope="col" role="columnheader" className={styles.caseColumn}>
              <span className={styles.columnLabel}><FiEdit3 size={16} aria-hidden="true" />Your case</span>
            </th>
            {dossier.decisions.map((decision) => {
              const result = results.find((item) => item.id === decision.id);
              const StatusIcon = result?.retenue ? FiCheckCircle : FiXCircle;
              const change = decisionStatusChange(result, original.resultat.decisions.find((item) => item.id === decision.id));
              const selected = detail?.kind === "decision" && detail.decisionId === decision.id && !detail.factorId;
              return <th scope="col" role="columnheader" key={decision.id} data-excluded={!result?.retenue} data-status-changed={change !== null}>
                <button type="button" aria-label={`${decisionLabel(decision.intitule)}: ${change ?? (result?.retenue ? "Retained" : "Not retained")}. View precedent details.`} aria-haspopup="dialog" aria-pressed={selected} aria-controls={selected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "decision", decisionId: decision.id }, event.currentTarget)}>
                  <span className={styles.columnLabel}><StatusIcon className={styles.retentionIcon} data-retained={result?.retenue === true} size={16} aria-hidden="true" />{decisionLabel(decision.intitule)}</span>
                  {change && <small className={styles.changeReason}>See why <FiInfo size={12} aria-hidden="true" /></small>}
                </button>
              </th>;
            })}
          </tr></thead>
          <tbody ref={bodyRef} onScroll={syncHorizontalScroll} role="rowgroup" tabIndex={0} aria-label="Case facts; scroll horizontally for more precedents">{factors.map((factor) => {
            const factSelected = detail?.kind === "fact" && detail.factorId === factor.id;
            const isPivot = dossier.resultat.facteurs[factor.id]?.est_pivot === true;
            return (
              <tr key={factor.id} role="row" data-selected={factor.id === selectedFactor} data-pivot={isPivot}>
                <th scope="row" role="rowheader"><button type="button" className={styles.factCell} aria-haspopup="dialog" aria-pressed={factSelected} aria-controls={factSelected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "fact", factorId: factor.id }, event.currentTarget)}>
                  <span className={styles.factLabel}>{factLabel(factor.id)}</span>
                  {isPivot && <span className={styles.pivotBadge}><FiZap size={11} aria-hidden="true" />Pivot</span>}
                </button></th>
                <td className={styles.caseColumn} role="cell">
                  <FactValueCell label={`Edit your case: ${factLabel(factor.id)}`} value={dossier.cas.facteurs[factor.id]} originalValue={original.cas.facteurs[factor.id]} evidenceOpen={factSelected} onChange={(value) => onFactChange(factor.id, value)} onActivate={(trigger) => onFactSelect(factor.id, trigger)} />
                </td>
                {dossier.decisions.map((decision) => {
                  const result = results.find((item) => item.id === decision.id);
                  const selected = detail?.kind === "decision" && detail.decisionId === decision.id && detail.factorId === factor.id;
                  return <td key={decision.id} role="cell" data-excluded={!result?.retenue}>
                    <button type="button" className={styles.precedentCell} aria-label={`${decisionLabel(decision.intitule)}, ${factLabel(factor.id)}: ${factValueLabel(decision.facteurs[factor.id])}. Read-only. View supporting information`} aria-haspopup="dialog" aria-pressed={selected} aria-controls={selected ? "case-details" : undefined} onClick={(event) => onInspect({ kind: "decision", decisionId: decision.id, factorId: factor.id }, event.currentTarget)}>
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
        <span><span className={styles.pivotMarker} aria-hidden="true" />Pivot fact</span>
        <span>Grey text = excluded</span>
      </div>
    </>
  );
}
