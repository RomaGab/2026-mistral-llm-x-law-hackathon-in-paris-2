import { BrandMark } from "./brand-mark";
import styles from "./app-brand.module.css";

export function AppBrand() {
  return (
    <div className={styles.brand} aria-label="pivot">
      <BrandMark className={styles.mark} />
      <span className={styles.name}>pivot<span>.</span></span>
    </div>
  );
}
