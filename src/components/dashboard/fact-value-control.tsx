import { useId, type CSSProperties } from "react";
import { factValueChoices } from "@/lib/dashboard/presentation";
import type { FactValue } from "@/types/dashboard";
import styles from "./dashboard.module.css";

export function FactValueControl({ label, value, onChange }: {
  label: string;
  value: FactValue;
  onChange: (value: FactValue) => void;
}) {
  const name = useId();
  const selectionStyle: CSSProperties & { "--choice-index": number } = {
    "--choice-index": factValueChoices.findIndex((choice) => choice.value === value),
  };
  return (
    <fieldset className={styles.factChoices} style={selectionStyle}>
      <legend className={styles.srOnly}>{label}</legend>
      <span className={styles.choiceIndicator} aria-hidden="true" />
      {factValueChoices.map((choice) => (
        <label key={choice.label} data-checked={value === choice.value}>
          <input type="radio" name={name} checked={value === choice.value} onChange={() => onChange(choice.value)} />
          <span>{choice.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
