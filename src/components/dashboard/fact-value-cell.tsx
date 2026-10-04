import { useRef } from "react";
import { FiChevronDown } from "react-icons/fi";
import { factValueChoices, factValueLabel } from "@/lib/dashboard/presentation";
import type { FactValue } from "@/types/dashboard";
import styles from "./dashboard.module.css";

export function FactValueCell({ label, value, originalValue, evidenceOpen, onChange, onActivate }: {
  label: string;
  value: FactValue;
  originalValue: FactValue;
  evidenceOpen: boolean;
  onChange: (value: FactValue) => void;
  onActivate: (trigger: HTMLSelectElement) => void;
}) {
  const selectRef = useRef<HTMLSelectElement>(null);
  const inputValue = factValueChoices.find((choice) => choice.value === value)?.inputValue ?? "unknown";
  function activate() {
    if (selectRef.current) onActivate(selectRef.current);
  }
  return (
    <div className={styles.valueCell} data-changed={value !== originalValue} data-value={inputValue} onPointerDown={activate} onClick={activate} onFocus={activate}>
      <select
        ref={selectRef}
        aria-label={label}
        aria-details={evidenceOpen ? "case-details" : undefined}
        title={value !== originalValue ? `Original: ${factValueLabel(originalValue)}` : label}
        value={inputValue}
        onChange={(event) => {
          const choice = factValueChoices.find((item) => item.inputValue === event.target.value);
          if (choice) onChange(choice.value);
        }}
      >
        {factValueChoices.map((choice) => <option key={choice.inputValue} value={choice.inputValue}>{choice.label}</option>)}
      </select>
      <FiChevronDown size={12} aria-hidden="true" />
    </div>
  );
}
