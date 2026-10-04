"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { FiAlignLeft, FiClipboard, FiFileText, FiHelpCircle, FiMessageSquare, FiSearch } from "react-icons/fi";

import { BrandMark } from "@/components/ui/brand-mark";
import { getPreparationPreviewSteps, PREPARATION_PREVIEW_MS } from "@/mocks/case-preparation";
import type { CasePreparationStep } from "@/types/case-intake";

import styles from "./case-preparation.module.css";

type CasePreparationProps = {
  steps: readonly CasePreparationStep[];
  currentStep: number;
};

const stepIcons = {
  question: FiMessageSquare,
  document: FiFileText,
  context: FiAlignLeft,
  facts: FiSearch,
  missing: FiHelpCircle,
  review: FiClipboard,
};

export function CasePreparation({ steps, currentStep }: CasePreparationProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const followProgressRef = useRef(true);

  useLayoutEffect(() => {
    headingRef.current?.focus({ preventScroll: true });
  }, []);

  useLayoutEffect(() => {
    const viewport = progressRef.current;
    if (!viewport || !followProgressRef.current) return;
    viewport.scrollTo({
      top: Math.max(0, viewport.scrollHeight - viewport.clientHeight),
    });
  }, [currentStep]);

  return (
    <div className={styles.preparing}>
      <div className={styles.heading}>
        <BrandMark animated className={styles.mark} />
        <h2 ref={headingRef} tabIndex={-1}>Preparing your case…</h2>
      </div>
      <div
        ref={progressRef}
        className={styles.progressWindow}
        role="region"
        aria-label="Preparation updates"
        tabIndex={0}
        onScroll={(event) => {
          const viewport = event.currentTarget;
          followProgressRef.current = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <= 2;
        }}
      >
        <div>
          {steps.slice(0, currentStep + 1).map((step) => {
            const Icon = stepIcons[step.kind];
            return (
              <div key={step.id} className={styles.progressLine}>
                <Icon className={styles.progressIcon} size={14} strokeWidth={1.6} aria-hidden="true" />
                <span>{step.label}</span>
              </div>
            );
          })}
        </div>
      </div>
      <p className={styles.srOnly} role="status" aria-atomic="true">{steps[currentStep]?.label}</p>
    </div>
  );
}

export function CasePreparationPreview({ hasDocuments }: { hasDocuments: boolean }) {
  const steps = getPreparationPreviewSteps(hasDocuments);
  const [currentStep, setCurrentStep] = useState(0);
  const stepCount = steps.length;

  useEffect(() => {
    const timers = Array.from({ length: stepCount - 1 }, (_, index) => window.setTimeout(
      () => setCurrentStep(index + 1),
      (index + 1) * PREPARATION_PREVIEW_MS / stepCount,
    ));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [stepCount]);

  return <CasePreparation steps={steps} currentStep={currentStep} />;
}
