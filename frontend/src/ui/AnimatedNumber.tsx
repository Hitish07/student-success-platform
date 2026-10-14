import { useEffect, useRef, useState } from "react";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  durationMs?: number;
}

/**
 * Counts up from 0 to `value` on mount. Uses requestAnimationFrame for
 * smooth motion and honours prefers-reduced-motion.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  prefix = "",
  durationMs = 900,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0);
  const startRef = useRef<number | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const prefersReduced =
      typeof window !== "undefined"
      && window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReduced) {
      setDisplay(value);
      return undefined;
    }

    startRef.current = null;

    const step = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(1, elapsed / durationMs);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        setDisplay(value);
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [value, durationMs]);

  return <>{prefix}{display.toFixed(decimals)}{suffix}</>;
}
