"use client";

import { useLayoutEffect, useRef } from "react";

import { BrandMark } from "@/components/ui/brand-mark";

import styles from "./case-preparation.module.css";

export function CasePreparation() {
  const statusRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    statusRef.current?.focus({ preventScroll: true });
  }, []);

  return (
    <div ref={statusRef} className={styles.preparing} role="status" tabIndex={-1}>
      <BrandMark animated className={styles.mark} />
      <span>Preparing your case…</span>
    </div>
  );
}
