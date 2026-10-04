import { useId } from "react";
import type { FactValue } from "@/types/dashboard";
import styles from "./dashboard.module.css";

const choices: { value: FactValue; label: string }[] = [
  { value: true, label: "Yes" }, { value: false, label: "No" }, { value: null, label: "Unknown" },
];

export function FactValueControl({ label, value, onChange }: {
  label: string;
  value: FactValue;
  onChange: (value: FactValue) => void;
}) {
  // A fact can appear both in the focused question and the expanded list.
  const name = useId();
  return (
    <fieldset className={styles.factChoices}>
      <legend className={styles.srOnly}>{label}</legend>
      {choices.map((choice) => (
        <label key={choice.label} data-checked={value === choice.value}>
          <input type="radio" name={name} checked={value === choice.value} onChange={() => onChange(choice.value)} />
          <span>{choice.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
