import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiRequest } from "../api";
import { useAuth } from "../auth/AuthContext";

interface GradingRow {
  id: number;
  student_id: number;
  student_name: string;
  student_email: string;
  submitted_at: string;
  answer_text: string | null;
  marks: number | string | null;
  feedback: string | null;
  max_marks: number | string;
  tab_switches: number;
  redo_count: number;
}

interface AttemptRow {
  id: number;
  student_name: string;
  student_email: string;
  status: string;
  tab_switches: number;
}

function GradeRowEditor({ row, onSaved }: { row: GradingRow; onSaved: () => void }) {
  const { accessToken } = useAuth();
  const [marks, setMarks] = useState(row.marks == null ? "" : String(row.marks));
  const [feedback, setFeedback] = useState(row.feedback ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    setError(null);
    setMessage(null);
    if (marks.trim() === "" || Number.isNaN(Number(marks))) {
      setError("Enter the marks as a number.");
      return;
    }
    setSaving(true);
    try {
      await apiRequest(
        `/faculty/submissions/${row.id}/grade`,
        { method: "PUT", body: JSON.stringify({ marks: Number(marks), feedback: feedback.trim() || null }) },
        accessToken ?? undefined,
      );
      setMessage("Grade saved.");
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save the grade.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "0.5rem", padding: "0.75rem 0", borderTop: "1px solid #ddd" }}>
      <strong><Link className="text-link" to={`/faculty/students/${row.student_id}`}>{row.student_name}</Link></strong>
      <span>{row.student_email} · submitted {new Date(row.submitted_at).toLocaleString()}</span>
      <span>Tab switches: {row.tab_switches} · Cancelled attempts: {row.redo_count}</span>
      <p style={{ whiteSpace: "pre-wrap" }}>{row.answer_text ?? "No answer text was saved for this submission."}</p>
      <label htmlFor={`grade-marks-${row.id}`}>Marks (out of {row.max_marks})</label>
      <input
        id={`grade-marks-${row.id}`}
        min="0"
        onChange={(event) => setMarks(event.target.value)}
        step="0.01"
        type="number"
        value={marks}
      />
      <label htmlFor={`grade-feedback-${row.id}`}>Feedback</label>
      <textarea
        id={`grade-feedback-${row.id}`}
        maxLength={5000}
        onChange={(event) => setFeedback(event.target.value)}
        rows={3}
        value={feedback}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
      <div>
        <button className="button button-small" disabled={saving} onClick={() => void save()} type="button">
          {saving ? "Saving..." : "Save grade"}
        </button>
      </div>
    </div>
  );
}

export function SubmissionsPanel({ assignmentId }: { assignmentId: number }) {
  const { accessToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<GradingRow[] | null>(null);
  const [attempts, setAttempts] = useState<AttemptRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<GradingRow[]>(
        `/faculty/assignments/${assignmentId}/submissions`,
        { method: "GET" },
        accessToken ?? undefined,
      );
      setRows(data);
      const activity = await apiRequest<AttemptRow[]>(
        `/faculty/assignments/${assignmentId}/attempts`,
        { method: "GET" },
        accessToken ?? undefined,
      );
      setAttempts(activity);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load submissions.");
    } finally {
      setLoading(false);
    }
  }, [assignmentId, accessToken]);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  return (
    <div>
      <button
        aria-expanded={open}
        className="button button-small button-outline"
        onClick={() => setOpen(!open)}
        type="button"
      >
        {open ? "Hide submissions" : "Submissions"}
      </button>
      {open && (
        <div>
          {loading && !rows && <p role="status">Loading submissions...</p>}
          {error && (
            <p className="form-error" role="alert">
              {error}{" "}
              <button className="button button-small button-outline" onClick={() => void load()} type="button">
                Try again
              </button>
            </p>
          )}
          {attempts.length > 0 && (
            <div style={{ padding: "0.5rem 0" }}>
              <strong>Attempts in progress or cancelled</strong>
              <ul>
                {attempts.map((item) => (
                  <li key={item.id}>
                    {item.student_name} ({item.student_email}) · {item.status} · {item.tab_switches} tab switches
                  </li>
                ))}
              </ul>
            </div>
          )}
          {rows && rows.length === 0 && <p>No students have submitted this assignment yet.</p>}
          {rows && rows.map((row) => <GradeRowEditor key={row.id} onSaved={() => void load()} row={row} />)}
        </div>
      )}
    </div>
  );
}
