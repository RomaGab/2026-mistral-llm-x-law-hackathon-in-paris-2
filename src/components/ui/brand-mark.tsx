import type { CSSProperties } from "react";

import styles from "./brand-mark.module.css";

type GridPoint = readonly [number, number];
type Pixel = {
  id: string;
  logo: GridPoint;
  diamond: GridPoint;
  cross: GridPoint;
};

// Blocks travel on the logo's four-unit grid. Shared destinations let them
// merge and split while staying fully opaque and square throughout the morph.
const pixels: readonly Pixel[] = [
  { id: "top-left", logo: [0, 0], diamond: [1, 1], cross: [2, 1] },
  { id: "top-middle", logo: [1, 0], diamond: [2, 0], cross: [2, 0] },
  { id: "top-right", logo: [2, 0], diamond: [3, 1], cross: [3, 2] },
  { id: "stem-upper", logo: [0, 1], diamond: [0, 2], cross: [0, 2] },
  { id: "bowl-upper", logo: [3, 1], diamond: [3, 2], cross: [3, 2] },
  { id: "stem-middle", logo: [0, 2], diamond: [1, 2], cross: [1, 2] },
  { id: "bowl-lower", logo: [3, 2], diamond: [4, 2], cross: [4, 2] },
  { id: "stem-lower", logo: [0, 3], diamond: [1, 3], cross: [1, 2] },
  { id: "bar-middle", logo: [1, 3], diamond: [2, 3], cross: [2, 3] },
  { id: "bar-right", logo: [2, 3], diamond: [3, 3], cross: [2, 3] },
  { id: "stem-bottom", logo: [0, 4], diamond: [2, 4], cross: [2, 4] },
  { id: "split-top", logo: [1, 0], diamond: [2, 1], cross: [2, 1] },
  { id: "split-stem", logo: [0, 2], diamond: [2, 2], cross: [2, 2] },
];

type PixelStyle = CSSProperties & Record<"--diamond-x" | "--diamond-y" | "--cross-x" | "--cross-y", string>;

type BrandMarkProps = {
  animated?: boolean;
  className?: string;
};

export function BrandMark({ animated = false, className }: BrandMarkProps) {
  return (
    <svg className={className} width="32" height="32" viewBox="0 0 28 28" fill="currentColor" shapeRendering="crispEdges" aria-hidden="true">
      {pixels.map((pixel) => {
        const style: PixelStyle = {
          "--diamond-x": `${(pixel.diamond[0] - pixel.logo[0]) * 4}px`,
          "--diamond-y": `${(pixel.diamond[1] - pixel.logo[1]) * 4}px`,
          "--cross-x": `${(pixel.cross[0] - pixel.logo[0]) * 4}px`,
          "--cross-y": `${(pixel.cross[1] - pixel.logo[1]) * 4}px`,
        };

        return (
          <rect
            key={pixel.id}
            x={4 + pixel.logo[0] * 4}
            y={4 + pixel.logo[1] * 4}
            width="4"
            height="4"
            className={animated ? styles.pixel : undefined}
            style={animated ? style : undefined}
          />
        );
      })}
    </svg>
  );
}
