import type { Ref } from "react";
import { AppBrand } from "./app-brand";
import styles from "./app-header.module.css";

export function AppHeader({ ref }: { ref?: Ref<HTMLElement> }) {
  return <header ref={ref} className={styles.header}><AppBrand /></header>;
}
