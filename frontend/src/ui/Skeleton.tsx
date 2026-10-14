import "./Skeleton.css";

interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: string;
  className?: string;
}

export function Skeleton({
  width = "100%",
  height = "1rem",
  radius = "6px",
  className = "",
}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`skeleton ${className}`.trim()}
      style={{ width, height, borderRadius: radius }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <Skeleton width="30%" height="0.85rem" />
      <Skeleton width="70%" height="1.5rem" />
      <Skeleton width="45%" height="0.9rem" />
    </div>
  );
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton-rows" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <div className="skeleton-row" key={index}>
          <Skeleton width="60%" height="1rem" />
          <Skeleton width="30%" height="1rem" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton-chart" aria-hidden="true">
      <Skeleton width="40%" height="1.1rem" />
      <Skeleton height="180px" radius="10px" />
    </div>
  );
}
