import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { apiRequest } from "../api";
import { useAuth } from "../auth/AuthContext";

interface FacultyCourse {
  id: number;
  code: string;
  name: string;
  credits: number;
  enrolled_students: number;
}

interface Dashboard {
  courses: FacultyCourse[];
  assigned_students: number;
  at_risk_students: number;
  open_alerts: number;
}

interface FacultyStudent {
  id: number;
  full_name: string;
  email: string;
  attendance_percentage: number | null;
  marks_percentage: number | null;
  latest_risk_level: "low" | "medium" | "high" | null;
}

interface AcademicSubject {
  id: number;
  code: string;
  name: string;
  year: number;
  semester: number;
}

interface AcademicStudent {
  id: number;
  full_name: string;
  email: string;
}

interface AcademicAssignment {
  id: number;
  subject_id: number;
  subject_code: string;
  subject_name: string;
  title: string;
  description: string | null;
  due_date: string;
  max_marks: number;
  created_at: string;
}

interface Resource<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

function useFacultyResource<T>(path: string | null): Resource<T> {
  const { accessToken } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    if (!path) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return () => {
        active = false;
      };
    }
    setData(null);
    setError(null);
    setIsLoading(true);
    apiRequest<T>(path, {}, accessToken ?? undefined)
      .then((value) => {
        if (active) setData(value);
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to load this page.");
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken, path, version]);

  return { data, isLoading, error, reload: () => setVersion((value) => value + 1) };
}

function ScreenState({
  isLoading,
  error,
  isEmpty,
  emptyMessage,
  onRetry,
  children,
}: {
  isLoading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyMessage: string;
  onRetry: () => void;
  children: ReactNode;
}) {
  if (isLoading) return <p className="student-state" role="status">Loading faculty data…</p>;
  if (error) {
    return (
      <div className="student-state student-error" role="alert">
        <p>{error}</p>
        <button className="button button-small button-outline" onClick={onRetry} type="button">
          Try again
        </button>
      </div>
    );
  }
  if (isEmpty) return <p className="student-state">{emptyMessage}</p>;
  return children;
}

function useDashboard(): Resource<Dashboard> {
  return useFacultyResource<Dashboard>("/faculty/dashboard");
}

function CoursePicker({
  courses,
  value,
  onChange,
}: {
  courses: FacultyCourse[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="faculty-picker">
      Course
      <select onChange={(event) => onChange(event.target.value)} value={value}>
        {courses.map((course) => (
          <option key={course.id} value={course.id}>
            {course.code} · {course.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function DashboardScreen() {
  const dashboard = useDashboard();
  return (
    <>
      <header className="student-heading">
        <p className="eyebrow">Teaching overview</p>
        <h1 className="portal-title">Faculty workspace</h1>
        <p className="intro">Manage your assigned courses and coordinate timely support.</p>
      </header>
      <ScreenState
        emptyMessage="No courses are assigned to your account yet."
        error={dashboard.error}
        isEmpty={!dashboard.data || dashboard.data.courses.length === 0}
        isLoading={dashboard.isLoading}
        onRetry={dashboard.reload}
      >
        {dashboard.data && (
          <>
            <div className="student-metrics">
              <article className="student-metric"><span>Assigned courses</span><strong>{dashboard.data.courses.length}</strong></article>
              <article className="student-metric"><span>Assigned students</span><strong>{dashboard.data.assigned_students}</strong></article>
              <article className="student-metric"><span>At risk</span><strong>{dashboard.data.at_risk_students}</strong></article>
              <article className="student-metric"><span>Open alerts</span><strong>{dashboard.data.open_alerts}</strong></article>
            </div>
            <section className="student-panel" aria-labelledby="assigned-courses">
              <p className="eyebrow">Your teaching schedule</p>
              <h2 id="assigned-courses">Assigned courses</h2>
              <div className="course-list">
                {dashboard.data.courses.map((course) => (
                  <article className="course-card" key={course.id}>
                    <div className="course-name">
                      <span>{course.code} · {course.credits} credits</span>
                      <h3>{course.name}</h3>
                      <p>{course.enrolled_students} enrolled students</p>
                    </div>
                    <Link className="text-link" to="/faculty/attendance">Mark attendance</Link>
                    <Link className="text-link" to="/faculty/assessments">Manage marks</Link>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </ScreenState>
      <FacultyAssignmentsSection />
    </>
  );
}

function FacultyAssignmentsSection() {
  const { accessToken } = useAuth();
  const subjects = useFacultyResource<AcademicSubject[]>("/faculty/my-subjects");
  const assignments = useFacultyResource<AcademicAssignment[]>("/faculty/assignments");
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  );
  const [maxMarks, setMaxMarks] = useState("100");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const subject = subjects.data?.find((item) => String(item.id) === selectedSubjectId)
    ?? subjects.data?.[0]
    ?? null;
  const students = useFacultyResource<AcademicStudent[]>(
    subject ? `/faculty/subjects/${subject.id}/students` : null,
  );

  async function submitAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subject) return;
    setIsSaving(true);
    setSaveError(null);
    setSuccess(null);
    try {
      await apiRequest<AcademicAssignment>("/faculty/assignments", {
        method: "POST",
        body: JSON.stringify({
          subject_id: subject.id,
          title,
          description: description || null,
          due_date: dueDate,
          max_marks: Number(maxMarks),
        }),
      }, accessToken ?? undefined);
      setTitle("");
      setDescription("");
      setSuccess("Assignment created.");
      assignments.reload();
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : "Unable to create the assignment.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section aria-labelledby="academic-faculty-heading" className="student-panel">
      <p className="eyebrow">Academic subjects</p>
      <h2 id="academic-faculty-heading">My subjects and assignments</h2>
      <ScreenState
        emptyMessage="No academic subjects are assigned to your account."
        error={subjects.error}
        isEmpty={!subjects.data || subjects.data.length === 0}
        isLoading={subjects.isLoading}
        onRetry={subjects.reload}
      >
        {subjects.data && subjects.data.length > 0 && subject && (
          <>
            <label className="faculty-picker" htmlFor="academic-faculty-subject">
              Subject
              <select
                id="academic-faculty-subject"
                onChange={(event) => setSelectedSubjectId(event.target.value)}
                value={selectedSubjectId || String(subject.id)}
              >
                {subjects.data.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} · {item.name} (Year {item.year}, Semester {item.semester})
                  </option>
                ))}
              </select>
            </label>
            <div className="faculty-academic-grid">
              <section aria-labelledby="faculty-roster-heading">
                <h3 id="faculty-roster-heading">Students in this subject</h3>
                <ScreenState
                  emptyMessage="No students match this subject's department, year, and semester."
                  error={students.error}
                  isEmpty={!students.data || students.data.length === 0}
                  isLoading={students.isLoading}
                  onRetry={students.reload}
                >
                  {students.data && students.data.length > 0 && (
                    <ul className="faculty-student-list">
                      {students.data.map((student) => (
                        <li key={student.id}>
                          <strong>{student.full_name}</strong>
                          <span>{student.email}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </ScreenState>
              </section>
              <form className="academic-assignment-form" onSubmit={submitAssignment}>
                <h3>Post an assignment</h3>
                <label htmlFor="assignment-title">Title</label>
                <input
                  id="assignment-title"
                  maxLength={200}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                  value={title}
                />
                <label htmlFor="assignment-description">Description</label>
                <textarea
                  id="assignment-description"
                  maxLength={5000}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={3}
                  value={description}
                />
                <label htmlFor="assignment-due-date">Due date</label>
                <input
                  id="assignment-due-date"
                  onChange={(event) => setDueDate(event.target.value)}
                  required
                  type="date"
                  value={dueDate}
                />
                <label htmlFor="assignment-max-marks">Maximum marks</label>
                <input
                  id="assignment-max-marks"
                  min="0.01"
                  onChange={(event) => setMaxMarks(event.target.value)}
                  required
                  step="0.01"
                  type="number"
                  value={maxMarks}
                />
                {saveError && <p className="form-error" role="alert">{saveError}</p>}
                {success && <p className="form-success" role="status">{success}</p>}
                <button className="button button-small" disabled={isSaving} type="submit">
                  {isSaving ? "Posting…" : "Post assignment"}
                </button>
              </form>
            </div>
          </>
        )}
      </ScreenState>
      <div className="academic-assignment-list">
        <h3>Your assignments</h3>
        <ScreenState
          emptyMessage="You have not posted any assignments yet."
          error={assignments.error}
          isEmpty={!assignments.data || assignments.data.length === 0}
          isLoading={assignments.isLoading}
          onRetry={assignments.reload}
        >
          {assignments.data && assignments.data.length > 0 && (
            <ul className="faculty-student-list">
              {assignments.data.map((item) => (
                <li key={item.id}>
                  <strong>{item.title} · {item.subject_code}</strong>
                  <span>Due {item.due_date} · {item.max_marks} marks</span>
                </li>
              ))}
            </ul>
          )}
        </ScreenState>
      </div>
    </section>
  );
}

function AttendanceScreen() {
  const dashboard = useDashboard();
  const [courseId, setCourseId] = useState("");
  const course = dashboard.data?.courses.find((item) => String(item.id) === courseId)
    ?? dashboard.data?.courses[0];
  const roster = useFacultyResource<FacultyStudent[]>(
    course ? `/faculty/courses/${course.id}/students` : null,
  );
  const attendance = useFacultyResource<Array<{
    id: number; student_name: string; course_code: string; class_date: string; status: string;
  }>>("/faculty/attendance");
  const { accessToken } = useAuth();
  const [studentId, setStudentId] = useState("");
  const [classDate, setClassDate] = useState(new Date().toISOString().slice(0, 10));
  const [attendanceStatus, setAttendanceStatus] = useState("present");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!course) return;
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      await apiRequest("/faculty/attendance", {
        method: "POST",
        body: JSON.stringify({
          course_id: course.id,
          student_id: Number(studentId),
          class_date: classDate,
          status: attendanceStatus,
        }),
      }, accessToken ?? undefined);
      setSuccess("Attendance saved.");
      attendance.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save attendance.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <ScreenHeading eyebrow="Daily records" title="Attendance" description="Record and review attendance for your assigned students." />
      <section className="student-panel">
        {dashboard.isLoading ? <p className="student-state" role="status">Loading assigned courses…</p>
          : dashboard.error ? <RetryState error={dashboard.error} onRetry={dashboard.reload} />
            : !dashboard.data || dashboard.data.courses.length === 0
              ? <p className="student-state">No assigned courses are available for attendance.</p>
              : (
                <>
                  <CoursePicker courses={dashboard.data.courses} onChange={setCourseId} value={course ? String(course.id) : ""} />
                  <ScreenState
                    emptyMessage="There are no enrolled students in this course."
                    error={roster.error}
                    isEmpty={!roster.data || roster.data.length === 0}
                    isLoading={roster.isLoading}
                    onRetry={roster.reload}
                  >
                    {roster.data && (
                      <form className="faculty-form" onSubmit={submit}>
                        <label htmlFor="attendance-student">Student</label>
                        <select id="attendance-student" onChange={(event) => setStudentId(event.target.value)} required value={studentId}>
                          <option value="">Choose a student</option>
                          {roster.data.map((student) => <option key={student.id} value={student.id}>{student.full_name}</option>)}
                        </select>
                        <label htmlFor="attendance-date">Class date</label>
                        <input id="attendance-date" max={new Date().toISOString().slice(0, 10)} onChange={(event) => setClassDate(event.target.value)} required type="date" value={classDate} />
                        <label htmlFor="attendance-status">Status</label>
                        <select id="attendance-status" onChange={(event) => setAttendanceStatus(event.target.value)} value={attendanceStatus}>
                          <option value="present">Present</option><option value="absent">Absent</option>
                          <option value="late">Late</option><option value="excused">Excused</option>
                        </select>
                        {error && <p className="form-error" role="alert">{error}</p>}
                        {success && <p className="form-success" role="status">{success}</p>}
                        <button className="button" disabled={saving || !studentId} type="submit">{saving ? "Saving…" : "Save attendance"}</button>
                      </form>
                    )}
                  </ScreenState>
                </>
              )}
      </section>
      <section className="student-panel">
        <h2>Recent attendance</h2>
        <ScreenState
          emptyMessage="No attendance has been recorded for your courses."
          error={attendance.error}
          isEmpty={!attendance.data || attendance.data.length === 0}
          isLoading={attendance.isLoading}
          onRetry={attendance.reload}
        >
          {attendance.data && <div className="faculty-table-wrap"><table className="faculty-table"><thead><tr><th>Student</th><th>Course</th><th>Date</th><th>Status</th></tr></thead><tbody>
            {attendance.data.map((row) => <tr key={row.id}><td>{row.student_name}</td><td>{row.course_code}</td><td>{row.class_date}</td><td>{row.status}</td></tr>)}
          </tbody></table></div>}
        </ScreenState>
      </section>
    </>
  );
}

function AssessmentScreen() {
  const dashboard = useDashboard();
  const [courseId, setCourseId] = useState("");
  const course = dashboard.data?.courses.find((item) => String(item.id) === courseId)
    ?? dashboard.data?.courses[0];
  const roster = useFacultyResource<FacultyStudent[]>(course ? `/faculty/courses/${course.id}/students` : null);
  const assessments = useFacultyResource<Array<{ id: number; title: string; assessment_type: string; max_score: number; due_date: string }>>(
    course ? `/faculty/courses/${course.id}/assessments` : null,
  );
  const marks = useFacultyResource<Array<{ id: number; student_id: number; student_name: string; assessment_id: number; assessment_title: string; max_score: number; score: number; is_submitted: boolean }>>(
    course ? `/faculty/courses/${course.id}/marks` : null,
  );
  const { accessToken } = useAuth();
  const [title, setTitle] = useState("");
  const [assessmentType, setAssessmentType] = useState("exam");
  const [maxScore, setMaxScore] = useState("100");
  const [dueDate, setDueDate] = useState(new Date().toISOString().slice(0, 10));
  const [assessmentId, setAssessmentId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [score, setScore] = useState("");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>, kind: "assessment" | "mark") {
    event.preventDefault();
    if (!course) return;
    setSaving(true);
    setMutationError(null);
    setSuccess(null);
    try {
      if (kind === "assessment") {
        await apiRequest(`/faculty/courses/${course.id}/assessments`, {
          method: "POST",
          body: JSON.stringify({ title, assessment_type: assessmentType, max_score: Number(maxScore), due_date: dueDate }),
        }, accessToken ?? undefined);
        assessments.reload();
        setSuccess("Assessment created.");
      } else {
        await apiRequest("/faculty/marks", {
          method: "POST",
          body: JSON.stringify({ assessment_id: Number(assessmentId), student_id: Number(studentId), score: Number(score), is_submitted: true }),
        }, accessToken ?? undefined);
        marks.reload();
        setSuccess("Mark saved.");
      }
    } catch (cause) {
      setMutationError(cause instanceof Error ? cause.message : "Unable to save this record.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <ScreenHeading eyebrow="Assessment records" title="Assessments and marks" description="Create assessments and enter marks for students enrolled in your courses." />
      <section className="student-panel">
        {dashboard.isLoading ? <p className="student-state" role="status">Loading assigned courses…</p>
          : dashboard.error ? <RetryState error={dashboard.error} onRetry={dashboard.reload} />
            : !dashboard.data || dashboard.data.courses.length === 0 ? <p className="student-state">No assigned courses are available.</p>
              : <CoursePicker courses={dashboard.data.courses} onChange={setCourseId} value={course ? String(course.id) : ""} />}
      </section>
      {course && (
        <>
          <section className="student-panel">
            <h2>Create assessment</h2>
            <form className="faculty-form" onSubmit={(event) => save(event, "assessment")}>
              <label htmlFor="assessment-title">Title</label><input id="assessment-title" maxLength={160} onChange={(event) => setTitle(event.target.value)} required value={title} />
              <label htmlFor="assessment-type">Type</label><select id="assessment-type" onChange={(event) => setAssessmentType(event.target.value)} value={assessmentType}><option value="exam">Exam</option><option value="quiz">Quiz</option><option value="assignment">Assignment</option><option value="project">Project</option></select>
              <label htmlFor="assessment-max">Maximum score</label><input id="assessment-max" min="0.01" onChange={(event) => setMaxScore(event.target.value)} required step="0.01" type="number" value={maxScore} />
              <label htmlFor="assessment-due">Due date</label><input id="assessment-due" onChange={(event) => setDueDate(event.target.value)} required type="date" value={dueDate} />
              {mutationError && <p className="form-error" role="alert">{mutationError}</p>}
              {success && <p className="form-success" role="status">{success}</p>}
              <button className="button" disabled={saving} type="submit">{saving ? "Saving…" : "Create assessment"}</button>
            </form>
          </section>
          <section className="student-panel">
            <h2>Enter marks</h2>
            <ScreenState
              emptyMessage="Create an assessment before entering marks."
              error={assessments.error}
              isEmpty={!assessments.data || assessments.data.length === 0}
              isLoading={assessments.isLoading}
              onRetry={assessments.reload}
            >
              {assessments.data && (
                <ScreenState
                  emptyMessage="No enrolled students are available."
                  error={roster.error}
                  isEmpty={!roster.data || roster.data.length === 0}
                  isLoading={roster.isLoading}
                  onRetry={roster.reload}
                >
                  {roster.data && (
                    <form className="faculty-form" onSubmit={(event) => save(event, "mark")}>
                      <label htmlFor="mark-assessment">Assessment</label><select id="mark-assessment" onChange={(event) => setAssessmentId(event.target.value)} required value={assessmentId}>
                        <option value="">Choose assessment</option>{assessments.data.map((item) => <option key={item.id} value={item.id}>{item.title} · out of {item.max_score}</option>)}
                      </select>
                      <label htmlFor="mark-student">Student</label><select id="mark-student" onChange={(event) => setStudentId(event.target.value)} required value={studentId}>
                        <option value="">Choose student</option>{roster.data.map((student) => <option key={student.id} value={student.id}>{student.full_name}</option>)}
                      </select>
                      <label htmlFor="mark-score">Score</label><input id="mark-score" min="0" onChange={(event) => setScore(event.target.value)} required step="0.01" type="number" value={score} />
                      {mutationError && <p className="form-error" role="alert">{mutationError}</p>}
                      {success && <p className="form-success" role="status">{success}</p>}
                      <button className="button" disabled={saving || !assessmentId || !studentId} type="submit">{saving ? "Saving…" : "Save mark"}</button>
                    </form>
                  )}
                </ScreenState>
              )}
            </ScreenState>
          </section>
          <section className="student-panel">
            <h2>Recorded marks</h2>
            <ScreenState emptyMessage="No marks recorded for this course." error={marks.error} isEmpty={!marks.data || marks.data.length === 0} isLoading={marks.isLoading} onRetry={marks.reload}>
              {marks.data && <div className="faculty-table-wrap"><table className="faculty-table"><thead><tr><th>Student</th><th>Assessment</th><th>Score</th><th>Submission</th></tr></thead><tbody>
                {marks.data.map((mark) => <tr key={mark.id}><td>{mark.student_name}</td><td>{mark.assessment_title}</td><td>{mark.score} / {mark.max_score}</td><td>{mark.is_submitted ? "Submitted" : "Missing"}</td></tr>)}
              </tbody></table></div>}
            </ScreenState>
          </section>
        </>
      )}
    </>
  );
}

function SupportScreen() {
  const dashboard = useDashboard();
  const atRisk = useFacultyResource<Array<{ student_id: number; student_name: string; course_codes: string[]; risk_score: number; risk_level: string; contributing_factors: Array<{ key: string; observation: string }>; open_alerts: number }>>("/faculty/at-risk");
  const alerts = useFacultyResource<Array<{ id: number; student_id: number; student_name: string; course_codes: string[]; alert_type: string; severity: string; status: string; created_at: string }>>("/faculty/alerts");
  const [courseId, setCourseId] = useState("");
  const course = dashboard.data?.courses.find((item) => String(item.id) === courseId) ?? dashboard.data?.courses[0];
  const roster = useFacultyResource<FacultyStudent[]>(course ? `/faculty/courses/${course.id}/students` : null);
  const [studentId, setStudentId] = useState("");
  const notes = useFacultyResource<Array<{ id: number; content: string; author_name: string; created_at: string }>>(
    studentId ? `/faculty/students/${studentId}/notes` : null,
  );
  const interventions = useFacultyResource<Array<{ id: number; intervention_type: string; description: string; start_date: string; status: string }>>(
    studentId ? `/faculty/students/${studentId}/interventions` : null,
  );
  const { accessToken } = useAuth();
  const [note, setNote] = useState("");
  const [interventionType, setInterventionType] = useState("mentoring");
  const [description, setDescription] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function createRecord(event: FormEvent<HTMLFormElement>, kind: "note" | "intervention") {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (kind === "note") {
        await apiRequest("/faculty/notes", { method: "POST", body: JSON.stringify({ student_id: Number(studentId), content: note }) }, accessToken ?? undefined);
        notes.reload();
        setNote("");
        setSuccess("Observation saved.");
      } else {
        await apiRequest("/faculty/interventions", { method: "POST", body: JSON.stringify({ student_id: Number(studentId), intervention_type: interventionType, description, start_date: startDate }) }, accessToken ?? undefined);
        interventions.reload();
        setDescription("");
        setSuccess("Intervention assigned.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save this record.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <ScreenHeading eyebrow="Early support" title="Student support" description="Review risk signals and alerts, and document support for your assigned students." />
      <section className="student-panel">
        <h2>At-risk students</h2>
        <ScreenState emptyMessage="No at-risk students are currently identified in your assigned courses." error={atRisk.error} isEmpty={!atRisk.data || atRisk.data.length === 0} isLoading={atRisk.isLoading} onRetry={atRisk.reload}>
          {atRisk.data && <div className="course-list">{atRisk.data.map((item) => <article className="feedback-card" key={item.student_id}>
            <div className="feedback-meta"><strong>{item.student_name}</strong><span>{item.risk_level} · {Math.round(item.risk_score * 100)}%</span></div>
            <p>{item.course_codes.join(", ")} · {item.open_alerts} open alerts</p>
            <ul>{item.contributing_factors.map((factor) => <li key={factor.key}>{factor.key}: {factor.observation}</li>)}</ul>
          </article>)}</div>}
        </ScreenState>
      </section>
      <section className="student-panel">
        <h2>Open alerts</h2>
        <ScreenState emptyMessage="There are no open alerts for your assigned students." error={alerts.error} isEmpty={!alerts.data || alerts.data.length === 0} isLoading={alerts.isLoading} onRetry={alerts.reload}>
          {alerts.data && <div className="feedback-list">{alerts.data.map((item) => <article className="feedback-card" key={item.id}>
            <div className="feedback-meta"><strong>{item.student_name} · {item.alert_type}</strong><span>{item.severity}</span></div>
            <p>{item.course_codes.join(", ")} · {item.status}</p>
          </article>)}</div>}
        </ScreenState>
      </section>
      <section className="student-panel">
        <h2>Notes and interventions</h2>
        {dashboard.isLoading ? <p className="student-state" role="status">Loading assigned courses…</p>
          : dashboard.error ? <RetryState error={dashboard.error} onRetry={dashboard.reload} />
            : !dashboard.data || dashboard.data.courses.length === 0 ? <p className="student-state">No assigned courses are available.</p>
              : <>
                <CoursePicker courses={dashboard.data.courses} onChange={(value) => { setCourseId(value); setStudentId(""); }} value={course ? String(course.id) : ""} />
                <ScreenState emptyMessage="This course has no enrolled students." error={roster.error} isEmpty={!roster.data || roster.data.length === 0} isLoading={roster.isLoading} onRetry={roster.reload}>
                  {roster.data && <label className="faculty-picker">Student<select onChange={(event) => setStudentId(event.target.value)} value={studentId}><option value="">Choose a student</option>{roster.data.map((student) => <option key={student.id} value={student.id}>{student.full_name}</option>)}</select></label>}
                </ScreenState>
              </>}
        {studentId && <>
          <form className="faculty-form" onSubmit={(event) => createRecord(event, "note")}>
            <h3>Add observation</h3><label htmlFor="student-note">Private faculty note</label><textarea id="student-note" maxLength={2000} onChange={(event) => setNote(event.target.value)} required rows={3} value={note} />
            {error && <p className="form-error" role="alert">{error}</p>}{success && <p className="form-success" role="status">{success}</p>}
            <button className="button" disabled={saving} type="submit">{saving ? "Saving…" : "Add note"}</button>
          </form>
          <ScreenState emptyMessage="No faculty notes have been recorded for this student." error={notes.error} isEmpty={!notes.data || notes.data.length === 0} isLoading={notes.isLoading} onRetry={notes.reload}>
            {notes.data && <div className="feedback-list">{notes.data.map((item) => <article className="feedback-card" key={item.id}><strong>{item.author_name}</strong><p>{item.content}</p></article>)}</div>}
          </ScreenState>
          <form className="faculty-form" onSubmit={(event) => createRecord(event, "intervention")}>
            <h3>Assign intervention</h3><label htmlFor="intervention-type">Support type</label><select id="intervention-type" onChange={(event) => setInterventionType(event.target.value)} value={interventionType}><option value="mentoring">Mentoring</option><option value="remedial_class">Remedial class</option><option value="counseling_referral">Counseling referral</option></select>
            <label htmlFor="intervention-description">Plan</label><textarea id="intervention-description" maxLength={2000} onChange={(event) => setDescription(event.target.value)} required rows={3} value={description} />
            <label htmlFor="intervention-date">Start date</label><input id="intervention-date" max={new Date().toISOString().slice(0, 10)} onChange={(event) => setStartDate(event.target.value)} required type="date" value={startDate} />
            {error && <p className="form-error" role="alert">{error}</p>}{success && <p className="form-success" role="status">{success}</p>}
            <button className="button" disabled={saving} type="submit">{saving ? "Saving…" : "Assign intervention"}</button>
          </form>
          <ScreenState emptyMessage="No interventions have been assigned to this student." error={interventions.error} isEmpty={!interventions.data || interventions.data.length === 0} isLoading={interventions.isLoading} onRetry={interventions.reload}>
            {interventions.data && <div className="feedback-list">{interventions.data.map((item) => <article className="feedback-card" key={item.id}><div className="feedback-meta"><strong>{item.intervention_type.replace(/_/g, " ")}</strong><span>{item.status}</span></div><p>{item.description}</p><time>{item.start_date}</time></article>)}</div>}
          </ScreenState>
        </>}
      </section>
    </>
  );
}

function FeedbackScreen() {
  const feedback = useFacultyResource<Array<{ id: number; student_name: string; course_name: string | null; rating: number; comments: string | null; submitted_at: string }>>("/faculty/feedback");
  return (
    <>
      <ScreenHeading eyebrow="Student voice" title="Course feedback" description="Review feedback submitted about you in your assigned courses." />
      <section className="student-panel">
        <ScreenState emptyMessage="No student feedback has been submitted about your courses yet." error={feedback.error} isEmpty={!feedback.data || feedback.data.length === 0} isLoading={feedback.isLoading} onRetry={feedback.reload}>
          {feedback.data && <div className="feedback-list">{feedback.data.map((item) => <article className="feedback-card" key={item.id}>
            <div className="feedback-meta"><strong>{item.course_name ?? "Course feedback"}</strong><time>{new Date(item.submitted_at).toLocaleDateString()}</time></div>
            <p>{item.student_name} · {item.rating} / 5</p>{item.comments && <p>{item.comments}</p>}
          </article>)}</div>}
        </ScreenState>
      </section>
    </>
  );
}

function ScreenHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="student-heading"><p className="eyebrow">{eyebrow}</p><h1 className="portal-title">{title}</h1><p className="intro">{description}</p></header>;
}

function RetryState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return <div className="student-state student-error" role="alert"><p>{error}</p><button className="button button-small button-outline" onClick={onRetry} type="button">Try again</button></div>;
}

const facultyNavigation = [
  { to: "/faculty", label: "Overview", end: true },
  { to: "/faculty/attendance", label: "Attendance", end: false },
  { to: "/faculty/assessments", label: "Assessments", end: false },
  { to: "/faculty/support", label: "Student support", end: false },
  { to: "/faculty/feedback", label: "Feedback", end: false },
];

export function FacultyPortalLayout() {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function handleLogout() {
    setIsLoggingOut(true);
    setError(null);
    try {
      await logout();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign out.");
      setIsLoggingOut(false);
    }
  }
  return (
    <main className="portal-page">
      <header className="topbar"><Link className="brand" to="/faculty"><span className="brand-mark" aria-hidden="true">S</span>Student Success</Link>
        <div className="account-menu"><span className="account-name">{user?.full_name}</span><button className="button button-small button-outline" disabled={isLoggingOut} onClick={handleLogout} type="button">{isLoggingOut ? "Signing out…" : "Sign out"}</button></div>
      </header>
      <nav aria-label="Faculty portal" className="student-navigation">{facultyNavigation.map((item) => <NavLink className={({ isActive }) => `student-nav-link${isActive ? " active" : ""}`} end={item.end} key={item.to} to={item.to}>{item.label}</NavLink>)}</nav>
      <div className="student-content">{error && <p className="form-error" role="alert">{error}</p>}<Outlet /></div>
    </main>
  );
}

export const FacultyDashboard = DashboardScreen;
export const FacultyAttendance = AttendanceScreen;
export const FacultyAssessments = AssessmentScreen;
export const FacultySupport = SupportScreen;
export const FacultyFeedback = FeedbackScreen;
