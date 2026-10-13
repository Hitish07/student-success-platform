import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest } from "../api";
import { useAuth } from "../auth/AuthContext";

interface Student360Header {
  student_id: number;
  full_name: string;
  email: string;
  department: string | null;
  year: number;
  semester: number;
}

interface Student360Risk {
  score: number | null;
  level: string | null;
  computed_at: string | null;
}

interface Student360Metrics {
  attendance_percentage: number | null;
  marks_percentage: number | null;
  pending_assignments: number;
  submitted_assignments: number;
}

interface Student360JourneyEvent {
  occurred_at: string;
  event_type: string;
  title: string;
  description: string;
}

interface Student360Doubt {
  subject_code: string;
  subject_name: string;
  asked_at: string;
}

interface Student360Submission {
  assignment_title: string;
  subject_code: string;
  submitted_at: string | null;
  marks: number | null;
  max_marks: number;
  tab_switches: number;
}

interface Student360View {
  header: Student360Header;
  risk: Student360Risk;
  metrics: Student360Metrics;
  journey: Student360JourneyEvent[];
  doubts: Student360Doubt[];
  submissions: Student360Submission[];
}

function formatDate(value: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatPercent(value: number | null): string {
  return value === null ? "-" : `${value.toFixed(1)}%`;
}

export function StudentDetailScreen() {
  const { studentId } = useParams<{ studentId: string }>();
  const { accessToken } = useAuth();
  const [data, setData] = useState<Student360View | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!studentId) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    apiRequest<Student360View>(
      `/faculty/students/${studentId}/summary`,
      {},
      accessToken ?? undefined,
    )
      .then((value) => {
        if (active) setData(value);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Unable to load this student.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [studentId, accessToken, reload]);

  if (loading) {
    return <p className="student-state" role="status">Loading student profile...</p>;
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

  const { header, risk, metrics, journey, doubts, submissions } = data;

  return (
    <>
      <header className="student-heading">
        <p className="eyebrow">
          <Link className="text-link" to="/faculty/support">Back to student support</Link>
        </p>
        <h1 className="portal-title">{header.full_name}</h1>
        <p className="intro">
          {header.email} - {header.department ?? "Unassigned"} - Year {header.year}, Semester {header.semester}
        </p>
      </header>

      <section className="analytics-kpis" aria-label="Student headline numbers">
        <article>
          <span>Risk level</span>
          <strong>{risk.level ?? "Unknown"}</strong>
          {risk.score !== null && <small>score {risk.score.toFixed(2)}</small>}
        </article>
        <article>
          <span>Attendance</span>
          <strong>{formatPercent(metrics.attendance_percentage)}</strong>
        </article>
        <article>
          <span>Average marks</span>
          <strong>{formatPercent(metrics.marks_percentage)}</strong>
        </article>
        <article>
          <span>Pending assignments</span>
          <strong>{metrics.pending_assignments}</strong>
          <small>{metrics.submitted_assignments} submitted</small>
        </article>
      </section>

      <section className="student-panel">
        <h2>Journey</h2>
        {journey.length === 0 ? (
          <p className="student-state">No journey events recorded yet.</p>
        ) : (
          <ol className="journey-timeline">
            {journey.map((event, index) => (
              <li className="journey-event" key={`${event.event_type}-${event.occurred_at}-${index}`}>
                <span aria-hidden="true" className={`journey-marker marker-${event.event_type}`} />
                <div className="journey-event-content">
                  <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
                  <h3>{event.title}</h3>
                  <p>{event.description}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="student-panel">
        <h2>Recent doubts</h2>
        {doubts.length === 0 ? (
          <p className="student-state">This student has not asked any doubts yet.</p>
        ) : (
          <ul className="faculty-student-list">
            {doubts.map((doubt, index) => (
              <li key={`${doubt.subject_code}-${doubt.asked_at}-${index}`}>
                <strong>{doubt.subject_code} - {doubt.subject_name}</strong>
                <span>asked {formatDate(doubt.asked_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="student-panel">
        <h2>Recent submissions</h2>
        {submissions.length === 0 ? (
          <p className="student-state">No submissions recorded for this student yet.</p>
        ) : (
          <div className="faculty-table-wrap">
            <table className="faculty-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Assignment</th>
                  <th>Submitted</th>
                  <th>Marks</th>
                  <th>Tab switches</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((row, index) => (
                  <tr key={`${row.subject_code}-${row.assignment_title}-${index}`}>
                    <td>{row.subject_code}</td>
                    <td>{row.assignment_title}</td>
                    <td>{formatDate(row.submitted_at)}</td>
                    <td>{row.marks === null ? "-" : `${row.marks} / ${row.max_marks}`}</td>
                    <td>{row.tab_switches}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
