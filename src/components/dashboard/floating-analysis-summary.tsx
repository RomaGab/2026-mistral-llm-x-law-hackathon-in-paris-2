import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { FiX } from "react-icons/fi";
import { percent } from "@/lib/dashboard/presentation";
import type { DashboardDossier, FactValue } from "@/types/dashboard";
import { PivotInsight } from "./pivot-insight";
import styles from "./dashboard.module.css";

export function FloatingAnalysisSummary({ dossier, original, selectedFactor, onFactChange, scoreRef, headerRef, onHeightChange, onDismiss }: {
  dossier: DashboardDossier;
  original: DashboardDossier;
  selectedFactor: string;
  onFactChange: (id: string, value: FactValue) => void;
  scoreRef: RefObject<HTMLDivElement | null>;
  headerRef: RefObject<HTMLElement | null>;
  onHeightChange: (height: number) => void;
  onDismiss: () => void;
}) {
  const [showScore, setShowScore] = useState(false);
  const floatingRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const score = scoreRef.current;
    if (!score) return;
    const header = headerRef.current;
    let observer: IntersectionObserver | undefined;
    let observedHeight = -1;
    function observeVisibleArea() {
      if (!score) return;
      const headerHeight = header?.offsetHeight ?? 0;
      if (headerHeight === observedHeight) return;
      observedHeight = headerHeight;
      observer?.disconnect();
      observer = new IntersectionObserver(([entry]) => {
        // Treat the area behind the sticky navbar as outside the visible viewport.
        setShowScore(!entry.isIntersecting && entry.boundingClientRect.bottom <= headerHeight);
      }, { rootMargin: `-${headerHeight}px 0px 0px 0px` });
      observer.observe(score);
    }
    observeVisibleArea();
    const resizeObserver = new ResizeObserver(observeVisibleArea);
    if (header) resizeObserver.observe(header);
    return () => {
      observer?.disconnect();
      resizeObserver.disconnect();
    };
  }, [scoreRef, headerRef]);

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
      <button type="button" className={`${styles.closePanel} ${styles.floatingClose}`} aria-label="Hide the pivotal question" onClick={onDismiss}><FiX size={18} aria-hidden="true" /></button>
      <PivotInsight compact dossier={dossier} original={original} selectedFactor={selectedFactor} onFactChange={onFactChange} />
      {showScore && <div className={styles.floatingEstimate} aria-hidden="true">
        <span>Employment estimate</span>
        <strong><span key={dossier.resultat.prediction.probabilite} className={styles.valueUpdate}>{percent(dossier.resultat.prediction.probabilite)}</span></strong>
      </div>}
    </aside>
  );
}
