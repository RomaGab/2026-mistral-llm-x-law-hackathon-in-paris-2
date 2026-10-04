import { FiChevronDown } from "react-icons/fi";
import { factValueChoices, factValueLabel } from "@/lib/dashboard/presentation";
import type { FactValue } from "@/types/dashboard";
import styles from "./dashboard.module.css";

export function FactValueCell({ label, value, originalValue, onChange, onActivate }: {
  label: string;
  value: FactValue;
  originalValue: FactValue;
  onChange: (value: FactValue) => void;
  onActivate: () => void;
}) {
  const inputValue = factValueChoices.find((choice) => choice.value === value)?.inputValue ?? "unknown";
  return (
    <div className={styles.valueCell} data-changed={value !== originalValue} data-value={inputValue} onPointerDown={onActivate} onClick={onActivate} onFocus={onActivate}>
      <select
        aria-label={label}
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
