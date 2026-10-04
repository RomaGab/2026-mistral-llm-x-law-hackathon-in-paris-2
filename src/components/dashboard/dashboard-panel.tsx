import type { ReactNode } from "react";
import styles from "./dashboard.module.css";

export function DashboardPanel({ id, title, action, children }: {
  id: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={styles.panel} aria-labelledby={id}>
      <header className={styles.panelHeader}>
        <h2 id={id}>{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}
