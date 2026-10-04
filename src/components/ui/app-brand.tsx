import { BrandMark } from "./brand-mark";
import styles from "./app-brand.module.css";

// A full page load returns to a blank intake: the case and analysis live in client state on "/".
export function AppBrand() {
  return (
    // <Link> would keep the client state of "/"; a real navigation is the reset we want.
    // eslint-disable-next-line @next/next/no-html-link-for-pages
    <a href="/" className={styles.brand} aria-label="pivot, start a new case">
      <BrandMark className={styles.mark} />
      <span className={styles.name}>pivot<span>.</span></span>
    </a>
  );
}
