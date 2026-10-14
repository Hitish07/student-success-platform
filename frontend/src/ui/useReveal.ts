import { useEffect, useRef, useState } from "react";

/**
 * Adds a class when the element scrolls into view, once.
 * Returns a ref to attach to the container and a boolean `shown`.
 */
export function useReveal<T extends HTMLElement>(options?: { rootMargin?: string; threshold?: number }) {
  const ref = useRef<T | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      setShown(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true);
            observer.disconnect();
            break;
          }
        }
      },
      {
        rootMargin: options?.rootMargin ?? "0px 0px -40px 0px",
        threshold: options?.threshold ?? 0.05,
      },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [options?.rootMargin, options?.threshold]);

  return { ref, shown };
}
