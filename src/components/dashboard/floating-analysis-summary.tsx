import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier, FactValue } from "@/types/dashboard";
import { PivotInsight } from "./pivot-insight";
import styles from "./dashboard.module.css";

export function FloatingAnalysisSummary({ dossier, original, selectedFactor, onFactChange, scoreRef, onHeightChange }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  selectedFactor: string;
  onFactChange: (id: string, value: FactValue) => void;
  scoreRef: RefObject<HTMLDivElement | null>;
  onHeightChange: (height: number) => void;
}) {
  const [showScore, setShowScore] = useState(false);
  const floatingRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const score = scoreRef.current;
    if (!score) return;
    const observer = new IntersectionObserver(([entry]) => {
      // Content below the viewport has not been reached yet, especially on mobile.
      setShowScore(!entry.isIntersecting && entry.boundingClientRect.bottom <= 0);
    });
    observer.observe(score);
    return () => observer.disconnect();
  }, [scoreRef]);

  useLayoutEffect(() => {
    const floating = floatingRef.current;
    if (!floating) return;
    // Reserve its actual height for the last rows and the desktop evidence panel.
    const measure = () => onHeightChange(floating.offsetHeight);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(floating);
    return () => {
      observer.disconnect();
      onHeightChange(0);
    };
  }, [onHeightChange]);

  return (
    <aside ref={floatingRef} className={styles.floatingSummary} aria-label="Current case analysis">
      <PivotInsight compact dossier={dossier} original={original} selectedFactor={selectedFactor} onFactChange={onFactChange} />
      {showScore && <div className={styles.floatingEstimate} aria-hidden="true">
        <span>Employment estimate</span>
        <strong><span key={dossier.resultat.prediction.probabilite} className={styles.valueUpdate}>{percent(dossier.resultat.prediction.probabilite)}</span></strong>
      </div>}
    </aside>
  );
}
