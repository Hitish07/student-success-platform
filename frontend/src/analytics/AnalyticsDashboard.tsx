import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../api";
import { SkeletonChart, SkeletonRows } from "../ui/Skeleton";
import { Modal } from "../ui/Modal";
import { useReveal } from "../ui/useReveal";
import { AnimatedNumber } from "../ui/AnimatedNumber";
import { useAuth } from "../auth/AuthContext";

type RiskLevel = "Low" | "Medium" | "High";
type Section = "overview" | "segments" | "students" | "quality" | "trends";
type SortKey = "student_name" | "success_score" | "data_completeness";

interface Driver {
  indicator: string;
  student_value: number;
  cohort_average: number;
  contribution: number;
}

interface DriverSet {
  positive: Driver[];
  negative: Driver[];
}

interface RiskFlag {
  level: RiskLevel;
  risk_score: number;
  drivers: DriverSet;
}

interface ScoredStudent {
  student_id: number;
  student_name: string;
  department: string | null;
  cohort: string | null;
  success_score: number;
  academic_score: number;
  placement_score: number;
  engagement_score: number;
  academic_risk: RiskFlag;
  placement_risk: RiskFlag;
  score_drivers: DriverSet;
  data_completeness: number;
  confidence: "standard" | "low confidence";
  imputed_fields: string[];
}

interface StudentSegment {
  student_id: number;
  student_name: string;
  department: string | null;
  cohort: string | null;
  segment: string;
  suggested_action: string;
}

interface UnifiedStudent {
  student_id: number;
  student_name: string;
  department: string | null;
  cohort: string | null;
  cgpa: number;
  attendance_percentage: number;
  lms_logins: number;
  source_coverage: string[];
  imputed_fields: string[];
}

interface DataQuality {
  rows_ingested: number;
  rows_cleaned: number;
  nulls_imputed: number;
  duplicates_removed: number;
  out_of_range_values: number;
  unresolved_rows: number;
  invalid_rows: number;
  source_rows: Record<string, number>;
  cleaned_source_rows: Record<string, number>;
  before_after_example: {
    source: string;
    external_student_id: string;
    canonical_student_id: number;
    before: Record<string, number | null>;
    after: Record<string, number | null>;
  } | null;
}

interface DashboardData {
  students: ScoredStudent[];
  segments: StudentSegment[];
  sourceStudents: UnifiedStudent[];
  quality: DataQuality;
}

const RISK_COLORS: Record<RiskLevel, string> = {
  Low: "#2b8a62",
  Medium: "#d39a20",
  High: "#ca5144",
};
const SEGMENT_COLORS = ["#277c6c", "#3d83a3", "#825caf", "#d18a32", "#59727e"];
function sectionsFor(role: "dean" | "principal"): { id: Section; label: string }[] {
  const base: { id: Section; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "segments", label: "Segments" },
    { id: "students", label: "Students" },
    { id: "quality", label: "Data quality" },
  ];
  if (role === "principal") {
    base.push({ id: "trends", label: "Institution trends" });
  }
  return base;
}

function useDashboardData() {
  const { accessToken } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(null);
    Promise.all([
      apiRequest<{ students: ScoredStudent[] }>("/analytics/success-scores", {}, accessToken ?? undefined),
      apiRequest<{ students: StudentSegment[] }>("/analytics/segments", {}, accessToken ?? undefined),
      apiRequest<{ students: UnifiedStudent[]; quality_report: DataQuality }>(
        "/analytics/data-integration",
        {},
        accessToken ?? undefined,
      ),
    ])
      .then(([scores, segments, integration]) => {
        if (active) {
          setData({
            students: scores.students,
            segments: segments.students,
            sourceStudents: integration.students,
            quality: integration.quality_report,
          });
        }
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to load analytics.");
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken, reload]);

  return { data, isLoading, error, retry: () => setReload((value) => value + 1) };
}

function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk-badge risk-${level.toLowerCase()}`}>{level}</span>;
}

function ChartPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="analytics-panel">
      <div className="analytics-panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function scoreBuckets(students: ScoredStudent[]) {
  return Array.from({ length: 10 }, (_, index) => {
    const lower = index * 10;
    return {
      range: `${lower}–${lower + 9}`,
      students: students.filter((student) =>
        student.success_score >= lower
        && student.success_score < (index === 9 ? 101 : lower + 10),
      ).length,
    };
  });
}

function riskByDepartment(students: ScoredStudent[]) {
  const grouped = new Map<string, { academic: number; placement: number }>();
  for (const student of students) {
    const department = student.department ?? "Unassigned";
    const totals = grouped.get(department) ?? { academic: 0, placement: 0 };
    if (student.academic_risk.level === "High") totals.academic += 1;
    if (student.placement_risk.level === "High") totals.placement += 1;
    grouped.set(department, totals);
  }
  return Array.from(grouped, ([department, counts]) => ({ department, ...counts }));
}

function makeInsights(students: ScoredStudent[], sourceStudents: UnifiedStudent[], segments: StudentSegment[]) {
  if (!students.length) return [];
  const lowAttendance = sourceStudents.filter((student) => student.attendance_percentage < 65);
  const normalAttendance = sourceStudents.filter((student) => student.attendance_percentage >= 65);
  const highAcademicInLowAttendance = lowAttendance.filter((student) =>
    students.find((row) => row.student_id === student.student_id)?.academic_risk.level === "High",
  ).length;
  const highAcademicInNormalAttendance = normalAttendance.filter((student) =>
    students.find((row) => row.student_id === student.student_id)?.academic_risk.level === "High",
  ).length;
  const lowRate = lowAttendance.length ? highAcademicInLowAttendance / lowAttendance.length : 0;
  const regularRate = normalAttendance.length ? highAcademicInNormalAttendance / normalAttendance.length : 0;
  const ratio = regularRate > 0 ? (lowRate / regularRate).toFixed(1) : null;
  const highCgpaPlacement = sourceStudents.filter((source) =>
    source.cgpa >= 8
    && students.find((row) => row.student_id === source.student_id)?.placement_risk.level === "High",
  ).length;
  const lowConfidence = students.filter((student) => student.confidence === "low confidence").length;
  const largestSegment = Object.entries(
    segments.reduce<Record<string, number>>((counts, row) => {
      counts[row.segment] = (counts[row.segment] ?? 0) + 1;
      return counts;
    }, {}),
  ).sort((left, right) => right[1] - left[1])[0];
  const averageScore = students.reduce((sum, student) => sum + student.success_score, 0) / students.length;

  return [
    ratio
      ? `Students with attendance below 65% are ${ratio}× as likely to have High academic risk as students at or above 65%.`
      : `${lowAttendance.length} students have attendance below 65%; there is not enough comparison data to estimate relative risk.`,
    `${highCgpaPlacement} students have CGPA above 8 and High placement risk; consider targeted placement readiness support.`,
    `${lowConfidence} of ${students.length} students have low-confidence scores due to incomplete source data.`,
    largestSegment
      ? `${largestSegment[1]} students (${Math.round((largestSegment[1] / students.length) * 100)}%) are in “${largestSegment[0]}”.`
      : "No segments are available for the current scope.",
    `The average Success Score in this view is ${averageScore.toFixed(1)} out of 100.`,
  ];
}

function DriverChart({ title, drivers }: { title: string; drivers: Driver[] }) {
  const values = drivers.map((driver) => ({
    indicator: driver.indicator,
    contribution: driver.contribution,
  }));
  return (
    <ChartPanel title={title} description="Contribution relative to the visible cohort, in score points.">
      {values.length ? (
        <div className="analytics-chart analytics-driver-chart">
          <ResponsiveContainer width="100%" height={Math.max(190, values.length * 43)}>
            <BarChart data={values} layout="vertical" margin={{ left: 20, right: 18 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" label={{ value: "Contribution (points)", position: "insideBottom", offset: -2 }} />
              <YAxis dataKey="indicator" type="category" width={138} tick={{ fontSize: 11 }} label={{ value: "Indicator", angle: -90, position: "insideLeft" }} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} points`, "Contribution"]} />
              <Bar dataKey="contribution" radius={[0, 5, 5, 0]}>
                {values.map((value, index) => (
                  <Cell key={`${value.indicator}-${index}`} fill={value.contribution >= 0 ? "#2b8a62" : "#ca5144"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="analytics-empty">No above- or below-cohort drivers for this direction.</p>
      )}
    </ChartPanel>
  );
}

function StudentDetail({
  student,
  segment,
  onClose,
}: {
  student: ScoredStudent;
  segment: StudentSegment | undefined;
  onClose: () => void;
}) {
  return (
    <div className="analytics-modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="analytics-detail" aria-labelledby="detail-title" aria-modal="true" role="dialog">
        <div className="analytics-detail-heading">
          <div>
            <p className="eyebrow">Student profile · ID {student.student_id}</p>
            <h2 id="detail-title">{student.student_name}</h2>
            <p>{student.department ?? "Unassigned"}{student.cohort ? ` · ${student.cohort}` : ""}</p>
          </div>
          <button className="button button-small button-outline" onClick={onClose} type="button">Close</button>
        </div>
        <div className="analytics-detail-summary">
          <div
            className="score-gauge"
            role="img"
            aria-label={`Success Score ${student.success_score} out of 100`}
            style={{
              background: `conic-gradient(#277c6c ${student.success_score}%, #dcebe5 ${student.success_score}%)`,
            }}
          >
            <strong>{student.success_score.toFixed(1)}</strong><span>Success Score</span>
          </div>
          {student.confidence === "low confidence" && <span className="confidence-badge">Low confidence · {student.data_completeness}% complete</span>}
          <div className="analytics-detail-risks">
            <p>Academic risk <RiskBadge level={student.academic_risk.level} /></p>
            <p>Placement risk <RiskBadge level={student.placement_risk.level} /></p>
          </div>
        </div>
        <div className="analytics-detail-grid">
          <DriverChart title="Positive score drivers" drivers={student.score_drivers.positive} />
          <DriverChart title="Negative score drivers" drivers={student.score_drivers.negative} />
          <DriverChart
            title="Academic risk drivers"
            drivers={[...student.academic_risk.drivers.positive, ...student.academic_risk.drivers.negative]}
          />
          <DriverChart
            title="Placement risk drivers"
            drivers={[...student.placement_risk.drivers.positive, ...student.placement_risk.drivers.negative]}
          />
        </div>
        <section className="analytics-action">
          <p className="eyebrow">Primary segment · {segment?.segment ?? "Not assigned"}</p>
          <p>{segment?.suggested_action ?? "Review the student's latest indicators and agree on a practical next step."}</p>
        </section>
        {student.imputed_fields.length > 0 && (
          <p className="analytics-muted">Imputed inputs: {student.imputed_fields.join(", ")}</p>
        )}
      </section>
    </div>
  );
}

interface TrendPoint {
  label: string;
  value: number;
}

interface SeriesLine {
  name: string;
  points: TrendPoint[];
}

interface PrincipalDashboardData {
  total_students: number;
  average_attendance: number;
  average_marks: number;
  academic_trend: {
    institution: TrendPoint[];
    by_department: SeriesLine[];
    overall_average: number;
  };
  placement_readiness: {
    points: TrendPoint[];
    overall_average: number;
    note: string;
  };
  placement_trend: {
    points: TrendPoint[];
    total_placed: number;
    placement_rate: number;
    note: string;
  };
  ai_summary: string | null;
}

const DEPARTMENT_COLORS = [
  "#277c6c", "#3d83a3", "#825caf", "#d18a32", "#59727e", "#b25a5a", "#4a7f3f",
];

function PrincipalTrendsPanel() {
  const { accessToken } = useAuth();
  const [data, setData] = useState<PrincipalDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    apiRequest<PrincipalDashboardData>("/principal/dashboard", {}, accessToken ?? undefined)
      .then((value) => {
        if (active) setData(value);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Unable to load institution trends.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken, reload]);

  if (loading) {
    return (
      <div aria-busy="true" className="student-panel">
        <SkeletonRows rows={2} />
        <SkeletonChart />
      </div>
    );
  }
  if (error) {
    return (
      <div className="student-state student-error" role="alert">
        <p>{error}</p>
        <button className="button button-small button-outline" onClick={() => setReload((n) => n + 1)} type="button">
          Try again
        </button>
      </div>
    );
  }
  if (!data) return null;

  // Flatten the department lines into one row per month so Recharts can plot them.
  const monthLabels = data.academic_trend.institution.map((point) => point.label);
  const institutionRows = monthLabels.map((month, index) => {
    const row: Record<string, number | string> = {
      month,
      Institution: data.academic_trend.institution[index]?.value ?? 0,
    };
    data.academic_trend.by_department.forEach((line) => {
      row[line.name] = line.points[index]?.value ?? 0;
    });
    return row;
  });

  const { ref: revealRef, shown: revealShown } = useReveal<HTMLDivElement>();

  return (
    <div
      className={`reveal ${revealShown ? "reveal-shown" : ""}`}
      ref={revealRef}
    >
      {data.ai_summary && (
        <section className="analytics-panel analytics-insights" aria-labelledby="ai-summary-heading">
          <div className="analytics-panel-heading">
            <div>
              <h2 id="ai-summary-heading">Institution briefing</h2>
              <p>Generated from the current numbers. No student identifiers are used.</p>
            </div>
          </div>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.55 }}>{data.ai_summary}</p>
        </section>
      )}

      <section className="analytics-kpis" aria-label="Institution headline numbers">
        <article><span>Total students</span><strong><AnimatedNumber value={data.total_students} /></strong></article>
        <article><span>Average attendance</span><strong><AnimatedNumber value={data.average_attendance} decimals={1} /><small> %</small></strong></article>
        <article><span>Average marks</span><strong><AnimatedNumber value={data.average_marks} decimals={1} /><small> %</small></strong></article>
        <article><span>Placement readiness</span><strong><AnimatedNumber value={data.placement_readiness.overall_average} decimals={1} /></strong></article>
        <article><span>Students placed</span><strong><AnimatedNumber value={data.placement_trend.total_placed} /></strong></article>
      </section>

      <ChartPanel
        title="Academic improvement over time"
        description="Average marks per month across the institution and each department."
      >
        <div className="analytics-chart">
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={institutionRows} margin={{ bottom: 22, left: 0, right: 12 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" label={{ value: "Month", position: "insideBottom", offset: -12 }} />
              <YAxis
                domain={[0, 100]}
                label={{ value: "Average marks (%)", angle: -90, position: "insideLeft" }}
              />
              <Tooltip />
              <Legend />
              <Line
                dataKey="Institution"
                type="monotone"
                stroke="#1a1a1a"
                strokeWidth={3}
                dot={{ r: 3 }}
              />
              {data.academic_trend.by_department.map((line, index) => (
                <Line
                  key={line.name}
                  dataKey={line.name}
                  type="monotone"
                  stroke={DEPARTMENT_COLORS[index % DEPARTMENT_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartPanel>

      <ChartPanel
        title="Placements over time"
        description={data.placement_trend.note}
      >
        <div className="analytics-chart">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={data.placement_trend.points}
              margin={{ bottom: 22, left: 0, right: 12 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" label={{ value: "Month", position: "insideBottom", offset: -12 }} />
              <YAxis allowDecimals={false} label={{ value: "Students placed", angle: -90, position: "insideLeft" }} />
              <Tooltip />
              <Line
                dataKey="value"
                name="Placed"
                type="monotone"
                stroke="#277c6c"
                strokeWidth={3}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartPanel>
    </div>
  );
}

interface SegmentDetailModalProps {
  segment: string;
  action: string;
  students: ScoredStudent[];
  onClose: () => void;
}

function SegmentDetailModal({ segment, action, students, onClose }: SegmentDetailModalProps) {
  const inSegment = students.filter((student) =>
    // The parent computes membership by segment name; this is a defensive filter.
    // The parent passes an already-filtered list, so this returns the same array.
    Boolean(student),
  );
  return (
    <Modal
      onClose={onClose}
      size="large"
      subtitle={`${inSegment.length} student${inSegment.length === 1 ? "" : "s"} in this segment`}
      title={segment}
    >
      <p className="modal-action-line">
        <strong>Suggested next step:</strong> {action}
      </p>
      {inSegment.length === 0 ? (
        <p className="analytics-empty">No students are currently in this segment.</p>
      ) : (
        <div className="analytics-table-wrap">
          <table className="analytics-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Department</th>
                <th>Success Score</th>
                <th>Academic risk</th>
                <th>Placement risk</th>
              </tr>
            </thead>
            <tbody>
              {inSegment.map((student) => (
                <tr key={student.student_id}>
                  <td>
                    <strong>{student.student_name}</strong>
                    <small>ID {student.student_id}</small>
                  </td>
                  <td>{student.department ?? "Unassigned"}</td>
                  <td><strong>{student.success_score.toFixed(1)}</strong></td>
                  <td><RiskBadge level={student.academic_risk.level} /></td>
                  <td><RiskBadge level={student.placement_risk.level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

interface RiskDetailModalProps {
  title: string;
  risk: RiskFlag;
  onClose: () => void;
}

function RiskDetailModal({ title, risk, onClose }: RiskDetailModalProps) {
  const all = [...risk.drivers.positive, ...risk.drivers.negative];
  const maxContribution = Math.max(1, ...all.map((driver) => Math.abs(driver.contribution)));
  return (
    <Modal
      onClose={onClose}
      size="medium"
      subtitle={`Risk score ${risk.risk_score.toFixed(1)} out of 100 · ${risk.level}`}
      title={title}
    >
      <p className="modal-action-line">
        <strong>What pushes this risk up or down:</strong> bars to the right raise the score (more risk),
        bars to the left lower it.
      </p>
      {all.length === 0 ? (
        <p className="analytics-empty">No drivers available for this risk.</p>
      ) : (
        <ul className="risk-driver-list">
          {all.map((driver, index) => {
            const widthPct = Math.round((Math.abs(driver.contribution) / maxContribution) * 50);
            const isPositive = driver.contribution > 0;
            return (
              <li key={`${driver.indicator}-${index}`}>
                <span className="risk-driver-label">{driver.indicator}</span>
                <span className="risk-driver-bar-track">
                  <span
                    className={`risk-driver-bar ${isPositive ? "risk-driver-bar-up" : "risk-driver-bar-down"}`}
                    style={{
                      width: `${widthPct}%`,
                      [isPositive ? "left" : "right"]: "50%",
                    }}
                  />
                </span>
                <span className="risk-driver-value">
                  {isPositive ? "+" : ""}
                  {driver.contribution.toFixed(2)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
  );
}

export function AnalyticsDashboard({ role }: { role: "dean" | "principal" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading, error, retry } = useDashboardData();
  const [section, setSection] = useState<Section>("overview");
  const [selectedStudent, setSelectedStudent] = useState<ScoredStudent | null>(null);
  const [selectedSegmentDetail, setSelectedSegmentDetail] = useState<string | null>(null);
  const [selectedRisk, setSelectedRisk] = useState<{ title: string; risk: RiskFlag } | null>(null);
  const [selectedSegment, setSelectedSegment] = useState("");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [risk, setRisk] = useState("");
  const [scoreRange, setScoreRange] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("success_score");
  const [sortDescending, setSortDescending] = useState(true);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (cause) {
      setLogoutError(cause instanceof Error ? cause.message : "Unable to sign out.");
    }
  }

  const departments = useMemo(
    () => Array.from(new Set(data?.students.map((student) => student.department ?? "Unassigned") ?? [])).sort(),
    [data],
  );
  const visibleStudents = useMemo(() => {
    if (!data) return [];
    const normalizedSearch = search.trim().toLowerCase();
    return data.students
      .filter((student) => !normalizedSearch
        || student.student_name.toLowerCase().includes(normalizedSearch)
        || String(student.student_id).includes(normalizedSearch))
      .filter((student) => !department || (student.department ?? "Unassigned") === department)
      .filter((student) => !risk || student.academic_risk.level === risk || student.placement_risk.level === risk)
      .filter((student) => !selectedSegment
        || data.segments.find((row) => row.student_id === student.student_id)?.segment === selectedSegment)
      .filter((student) => !scoreRange || (scoreRange === "below-50"
        ? student.success_score < 50
        : scoreRange === "50-75"
          ? student.success_score >= 50 && student.success_score < 75
          : student.success_score >= 75))
      .sort((left, right) => {
        const comparison = sortKey === "student_name"
          ? left.student_name.localeCompare(right.student_name)
          : left[sortKey] - right[sortKey];
        return sortDescending ? -comparison : comparison;
      });
  }, [data, search, department, risk, selectedSegment, scoreRange, sortKey, sortDescending]);

  const segmentCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const segment of data?.segments ?? []) {
      counts.set(segment.segment, (counts.get(segment.segment) ?? 0) + 1);
    }
    return Array.from(counts, ([name, students]) => ({ name, students }));
  }, [data]);
  const insights = useMemo(
    () => data ? makeInsights(data.students, data.sourceStudents, data.segments) : [],
    [data],
  );

  function sortBy(key: SortKey) {
    if (sortKey === key) setSortDescending((value) => !value);
    else {
      setSortKey(key);
      setSortDescending(key !== "student_name");
    }
  }

  const averageScore = data?.students.length
    ? data.students.reduce((sum, student) => sum + student.success_score, 0) / data.students.length
    : 0;
  const highAcademic = data?.students.filter((student) => student.academic_risk.level === "High").length ?? 0;
  const highPlacement = data?.students.filter((student) => student.placement_risk.level === "High").length ?? 0;
  const lowConfidence = data?.students.filter((student) => student.confidence === "low confidence").length ?? 0;

  return (
    <main className="analytics-page">
      <header className="analytics-topbar">
        <Link className="brand" to={`/${role}`}>
          <span className="brand-mark" aria-hidden="true">S</span>
          Student Success
        </Link>
        <div className="account-menu">
          <span className="analytics-role">{role === "dean" ? "Department analytics" : "Institution analytics"}</span>
          <span className="account-name">{user?.full_name}</span>
          <button className="button button-small button-outline" onClick={() => void handleLogout()} type="button">Sign out</button>
        </div>
      </header>
      <div className="analytics-shell">
        <header className="analytics-heading">
          <div>
            <p className="eyebrow">{role === "dean" ? "Department view" : "Institution view"}</p>
            <h1>{role === "dean" ? `${user?.full_name ? "Department" : "Dean"} success dashboard` : "Campus success dashboard"}</h1>
            <p>Understand outcomes, identify risk patterns, and target student support.</p>
          </div>
          <span className="analytics-scope">{role === "dean" ? "Your department" : "All departments"}</span>
        </header>
        <nav className="analytics-nav" aria-label="Analytics sections">
          {sectionsFor(role).map((item) => (
            <button
              aria-current={section === item.id ? "page" : undefined}
              className={section === item.id ? "analytics-nav-active" : ""}
              key={item.id}
              onClick={() => setSection(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>

        {isLoading && <p className="student-state" role="status">Loading dashboard analytics…</p>}
        {error && !isLoading && (
          <div className="student-state student-error" role="alert">
            <p>{error}</p>
            <button className="button button-small button-outline" onClick={retry} type="button">Try again</button>
          </div>
        )}
        {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
        {!isLoading && !error && data && data.students.length === 0 && (
          <p className="student-state">No student analytics are available for this scope yet.</p>
        )}

        {!isLoading && !error && data && data.students.length > 0 && (
          <>
            {section === "overview" && (
              <>
                <section className="analytics-kpis" aria-label="Success dashboard key performance indicators">
                  <article><span>Average Success Score</span><strong>{averageScore.toFixed(1)}<small> / 100</small></strong></article>
                  <article><span>High academic risk</span><strong>{highAcademic}</strong></article>
                  <article><span>High placement risk</span><strong>{highPlacement}</strong></article>
                  <article><span>Low-confidence scores</span><strong>{lowConfidence}</strong></article>
                </section>
                <div className="analytics-chart-grid">
                  <ChartPanel title="Success Score distribution" description="Number of students in each score band.">
                    <div className="analytics-chart">
                      <ResponsiveContainer width="100%" height={285}>
                        <BarChart data={scoreBuckets(data.students)} margin={{ bottom: 22, left: 0, right: 12 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="range" label={{ value: "Success Score range", position: "insideBottom", offset: -12 }} />
                          <YAxis allowDecimals={false} label={{ value: "Students", angle: -90, position: "insideLeft" }} />
                          <Tooltip />
                          <Bar dataKey="students" name="Students" fill="#277c6c" radius={[5, 5, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </ChartPanel>
                  <ChartPanel title="High-risk students by department" description="Counts of students with High risk flags.">
                    <div className="analytics-chart">
                      <ResponsiveContainer width="100%" height={285}>
                        <BarChart data={riskByDepartment(data.students)} margin={{ bottom: 22, left: 0, right: 12 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="department" tick={{ fontSize: 10 }} label={{ value: "Department", position: "insideBottom", offset: -12 }} />
                          <YAxis allowDecimals={false} label={{ value: "Students", angle: -90, position: "insideLeft" }} />
                          <Tooltip />
                          <Bar dataKey="academic" name="Academic risk" fill={RISK_COLORS.High} />
                          <Bar dataKey="placement" name="Placement risk" fill={RISK_COLORS.Medium} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </ChartPanel>
                </div>
                <section className="analytics-panel analytics-insights">
                  <div className="analytics-panel-heading"><div><h2>Key insights</h2><p>Patterns in the currently visible cohort; association is not causation.</p></div></div>
                  <ol>{insights.map((insight) => <li key={insight}>{insight}</li>)}</ol>
                </section>
              </>
            )}

            {section === "segments" && (
              <div className="analytics-chart-grid analytics-segment-grid">
                <ChartPanel title="Student segment breakdown" description="Select a chart bar to filter the student table.">
                  <div className="analytics-chart">
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart data={segmentCounts} margin={{ bottom: 32, left: 0, right: 12 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" interval={0} angle={-15} textAnchor="end" tick={{ fontSize: 10 }} label={{ value: "Primary segment", position: "insideBottom", offset: -22 }} />
                        <YAxis allowDecimals={false} label={{ value: "Students", angle: -90, position: "insideLeft" }} />
                        <Tooltip />
                        <Bar dataKey="students" name="Students" onClick={(entry) => {
                          if (typeof entry.name === "string") {
                            setSelectedSegment(entry.name);
                            setSection("students");
                          }
                        }} cursor="pointer" radius={[5, 5, 0, 0]}>
                          {segmentCounts.map((row, index) => (
                            <Cell key={row.name} fill={SEGMENT_COLORS[index % SEGMENT_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </ChartPanel>
                <section className="analytics-panel">
                  <div className="analytics-panel-heading"><div><h2>Suggested actions</h2><p>One practical next step for each segment.</p></div></div>
                  <div className="segment-card-grid">
                    {(() => {
                      const total = data.students.length || 1;
                      return Array.from(new Map(data.segments.map((item) => [item.segment, item])).values()).map((item, index) => {
                        const count = segmentCounts.find((row) => row.name === item.segment)?.students ?? 0;
                        const pct = Math.round((count / total) * 100);
                        const color = SEGMENT_COLORS[index % SEGMENT_COLORS.length];
                        return (
                          <button
                            className="segment-card"
                            key={item.segment}
                            onClick={() => setSelectedSegmentDetail(item.segment)}
                            style={{ ["--segment-color" as string]: color }}
                            type="button"
                          >
                            <span className="segment-card-top">
                              <span className="segment-card-dot" />
                              <span className="segment-card-count">{count}</span>
                            </span>
                            <span className="segment-card-name">{item.segment}</span>
                            <span className="segment-card-bar-track">
                              <span className="segment-card-bar" style={{ width: `${pct}%` }} />
                            </span>
                            <span className="segment-card-meta">{pct}% of the cohort</span>
                            <span className="segment-card-action">{item.suggested_action}</span>
                            <span className="segment-card-cta">View students →</span>
                          </button>
                        );
                      });
                    })()}
                  </div>
                </section>
              </div>
            )}

            {section === "students" && (
              <section className="analytics-panel">
                <div className="analytics-panel-heading">
                  <div><h2>Student outcomes</h2><p>{visibleStudents.length} of {data.students.length} students · select a row to see score drivers.</p></div>
                </div>
                <div className="analytics-filters" aria-label="Filter students">
                  <label>Search name or ID<input onChange={(event) => setSearch(event.target.value)} placeholder="Name or student ID" value={search} /></label>
                  <label>Department<select onChange={(event) => setDepartment(event.target.value)} value={department}><option value="">All departments</option>{departments.map((value) => <option key={value}>{value}</option>)}</select></label>
                  <label>Risk level<select onChange={(event) => setRisk(event.target.value)} value={risk}><option value="">Any risk</option><option>Low</option><option>Medium</option><option>High</option></select></label>
                  <label>Segment<select onChange={(event) => setSelectedSegment(event.target.value)} value={selectedSegment}><option value="">All segments</option>{segmentCounts.map((item) => <option key={item.name}>{item.name}</option>)}</select></label>
                  <label>Score range<select onChange={(event) => setScoreRange(event.target.value)} value={scoreRange}><option value="">Any score</option><option value="below-50">Below 50</option><option value="50-75">50 to under 75</option><option value="75-up">75 and above</option></select></label>
                  {(selectedSegment || search || department || risk || scoreRange) && <button className="text-link analytics-clear" onClick={() => { setSelectedSegment(""); setSearch(""); setDepartment(""); setRisk(""); setScoreRange(""); }} type="button">Clear filters</button>}
                </div>
                <div className="analytics-table-wrap">
                  {visibleStudents.length ? (
                    <table className="analytics-table">
                      <thead><tr>
                        <th><button onClick={() => sortBy("student_name")} type="button">Student{sortKey === "student_name" ? (sortDescending ? " ↓" : " ↑") : ""}</button></th>
                        <th>Department</th>
                        <th><button onClick={() => sortBy("success_score")} type="button">Score{sortKey === "success_score" ? (sortDescending ? " ↓" : " ↑") : ""}</button></th>
                        <th>Academic risk</th><th>Placement risk</th><th>Segment</th>
                        <th><button onClick={() => sortBy("data_completeness")} type="button">Completeness{sortKey === "data_completeness" ? (sortDescending ? " ↓" : " ↑") : ""}</button></th>
                      </tr></thead>
                      <tbody>{visibleStudents.map((student) => (
                        <tr key={student.student_id} onClick={() => setSelectedStudent(student)} tabIndex={0} onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") setSelectedStudent(student);
                        }}>
                          <td><strong>{student.student_name}</strong><small>ID {student.student_id}</small></td>
                          <td>{student.department ?? "Unassigned"}</td>
                          <td><strong>{student.success_score.toFixed(1)}</strong>{student.confidence === "low confidence" && <small className="confidence-inline">Low confidence</small>}</td>
                          <td>
                            <button
                              className="risk-badge-button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedRisk({
                                  title: `${student.student_name} · Academic risk`,
                                  risk: student.academic_risk,
                                });
                              }}
                              type="button"
                            >
                              <RiskBadge level={student.academic_risk.level} />
                            </button>
                          </td>
                          <td>
                            <button
                              className="risk-badge-button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedRisk({
                                  title: `${student.student_name} · Placement risk`,
                                  risk: student.placement_risk,
                                });
                              }}
                              type="button"
                            >
                              <RiskBadge level={student.placement_risk.level} />
                            </button>
                          </td>
                          <td>{data.segments.find((item) => item.student_id === student.student_id)?.segment ?? "—"}</td>
                          <td>{student.data_completeness.toFixed(0)}%</td>
                        </tr>
                      ))}</tbody>
                    </table>
                  ) : <p className="analytics-empty">No students match these filters.</p>}
                </div>
              </section>
            )}

            {section === "trends" && role === "principal" && <PrincipalTrendsPanel />}

            {section === "quality" && (
              <>
                <section className="analytics-quality-kpis">
                  <article><span>Rows received</span><strong>{data.quality.rows_ingested}</strong></article>
                  <article><span>Duplicates removed</span><strong>{data.quality.duplicates_removed}</strong></article>
                  <article><span>Unmatched IDs</span><strong>{data.quality.unresolved_rows}</strong></article>
                  <article><span>Out-of-range values rejected</span><strong>{data.quality.out_of_range_values}</strong></article>
                  <article><span>Nulls imputed</span><strong>{data.quality.nulls_imputed}</strong></article>
                </section>
                <div className="analytics-chart-grid">
                  <ChartPanel title="Rows received by source" description="Raw rows received and retained after deduplication.">
                    <div className="analytics-chart">
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={Object.entries(data.quality.source_rows).map(([source, rows]) => ({
                          source,
                          received: rows,
                          retained: data.quality.cleaned_source_rows[source] ?? 0,
                        }))} margin={{ bottom: 22, left: 0, right: 12 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="source" label={{ value: "Data source", position: "insideBottom", offset: -12 }} />
                          <YAxis allowDecimals={false} label={{ value: "Rows", angle: -90, position: "insideLeft" }} />
                          <Tooltip />
                          <Bar dataKey="received" name="Rows received" fill="#3d83a3" />
                          <Bar dataKey="retained" name="Rows retained" fill="#2b8a62" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </ChartPanel>
                  <ChartPanel title="Cleaning example" description="A raw value and identifier compared with the normalized pipeline output.">
                    {data.quality.before_after_example ? (
                      <div className="quality-example">
                        <p><strong>Source:</strong> {data.quality.before_after_example.source}</p>
                        <p><strong>Raw ID:</strong> <code>{data.quality.before_after_example.external_student_id}</code> → <strong>Matched student:</strong> {data.quality.before_after_example.canonical_student_id}</p>
                        <div className="quality-before-after">
                          <div><h3>Before cleaning</h3><pre>{JSON.stringify(data.quality.before_after_example.before, null, 2)}</pre></div>
                          <div><h3>After cleaning</h3><pre>{JSON.stringify(data.quality.before_after_example.after, null, 2)}</pre></div>
                        </div>
                      </div>
                    ) : <p className="analytics-empty">No invalid source row was encountered for this scope, so there is no before/after example to show.</p>}
                  </ChartPanel>
                </div>
                <p className="analytics-muted">Quality counts are computed for the authorized scope. Rejected metric values are treated as missing and may be imputed; review source systems before acting on low-confidence scores.</p>
              </>
            )}
          </>
        )}
      </div>
      {selectedSegmentDetail !== null && data && (
        <SegmentDetailModal
          action={
            data.segments.find((row) => row.segment === selectedSegmentDetail)
              ?.suggested_action ?? ""
          }
          onClose={() => setSelectedSegmentDetail(null)}
          segment={selectedSegmentDetail}
          students={data.students.filter(
            (student) =>
              data.segments.find((row) => row.student_id === student.student_id)?.segment ===
              selectedSegmentDetail,
          )}
        />
      )}
      {selectedRisk !== null && (
        <RiskDetailModal
          onClose={() => setSelectedRisk(null)}
          risk={selectedRisk.risk}
          title={selectedRisk.title}
        />
      )}
      {selectedStudent && data && (
        <StudentDetail
          student={selectedStudent}
          segment={data.segments.find((item) => item.student_id === selectedStudent.student_id)}
          onClose={() => setSelectedStudent(null)}
        />
      )}
    </main>
  );
}
