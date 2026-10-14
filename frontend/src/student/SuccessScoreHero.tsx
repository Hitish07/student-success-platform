import { useReveal } from "../ui/useReveal";
import { AnimatedNumber } from "../ui/AnimatedNumber";

import "./SuccessScoreHero.css";

export interface ScoreDriverSummary {
  indicator: string;
  contribution: number;
}

export interface SuccessScoreSummary {
  score: number;
  academic_score: number;
  placement_score: number;
  engagement_score: number;
  academic_risk_level: string;
  placement_risk_level: string;
  confidence: string;
  top_positive_drivers: ScoreDriverSummary[];
  top_negative_drivers: ScoreDriverSummary[];
}

const RISK_ORDER = ["Low", "Medium", "High"];

function worstRisk(a: string, b: string): string {
  const ai = RISK_ORDER.indexOf(a);
  const bi = RISK_ORDER.indexOf(b);
  const worst = Math.max(ai < 0 ? 0 : ai, bi < 0 ? 0 : bi);
  return RISK_ORDER[worst];
}

function riskClass(level: string): string {
  switch (level) {
    case "High": return "hero-risk-high";
    case "Medium": return "hero-risk-medium";
    default: return "hero-risk-low";
  }
}

export function SuccessScoreHero({ score }: { score: SuccessScoreSummary }) {
  const { ref, shown } = useReveal<HTMLDivElement>();
  const highestRisk = worstRisk(score.academic_risk_level, score.placement_risk_level);

  // SVG progress ring: circumference for r=54 is ~339.3
  const R = 54;
  const CIRC = 2 * Math.PI * R;
  const pct = Math.max(0, Math.min(100, score.score));
  const offset = CIRC - (pct / 100) * CIRC;

  return (
    <section
      className={`score-hero ${riskClass(highestRisk)} reveal ${shown ? "reveal-shown" : ""}`}
      ref={ref}
      aria-labelledby="score-hero-heading"
    >
      <header className="score-hero-header">
        <div>
          <p className="eyebrow">Your Success Score</p>
          <h2 id="score-hero-heading">How you're doing right now</h2>
        </div>
        <span className={`risk-chip ${riskClass(highestRisk)}`}>
          {highestRisk} risk
        </span>
      </header>

      <div className="score-hero-body">
        <div className="score-hero-ring" role="img" aria-label={`Success Score ${score.score.toFixed(1)} out of 100`}>
          <svg viewBox="0 0 120 120" className="score-ring-svg">
            <circle className="score-ring-track" cx="60" cy="60" r={R} />
            <circle
              className="score-ring-fill"
              cx="60"
              cy="60"
              r={R}
              strokeDasharray={CIRC}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="score-ring-value">
            <strong>
              <AnimatedNumber value={score.score} decimals={1} />
            </strong>
            <small>of 100</small>
          </div>
        </div>

        <div className="score-hero-tiles">
          <div className="score-tile">
            <span>Academic</span>
            <strong><AnimatedNumber value={score.academic_score} decimals={1} /></strong>
          </div>
          <div className="score-tile">
            <span>Placement</span>
            <strong><AnimatedNumber value={score.placement_score} decimals={1} /></strong>
          </div>
          <div className="score-tile">
            <span>Engagement</span>
            <strong><AnimatedNumber value={score.engagement_score} decimals={1} /></strong>
          </div>
        </div>
      </div>

      <div className="score-hero-drivers">
        <div className="driver-column driver-positive">
          <p className="driver-heading">What helps you</p>
          {score.top_positive_drivers.length === 0 ? (
            <p className="driver-empty">No standout strengths yet.</p>
          ) : (
            <ul>
              {score.top_positive_drivers.map((driver) => (
                <li key={driver.indicator}>
                  <span className="driver-name">{driver.indicator}</span>
                  <span className="driver-value">+{driver.contribution.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="driver-column driver-negative">
          <p className="driver-heading">What's holding you back</p>
          {score.top_negative_drivers.length === 0 ? (
            <p className="driver-empty">Nothing is dragging your score down.</p>
          ) : (
            <ul>
              {score.top_negative_drivers.map((driver) => (
                <li key={driver.indicator}>
                  <span className="driver-name">{driver.indicator}</span>
                  <span className="driver-value">{driver.contribution.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {score.confidence === "low confidence" && (
        <p className="score-hero-note">
          Some of your source data is incomplete, so this score is shown with lower confidence.
        </p>
      )}
    </section>
  );
}
