import { ChangePassword } from "../auth/ChangePassword";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { apiRequest } from "../api";
import { useAuth } from "../auth/AuthContext";

interface CourseProgress {
  course_id: number;
  code: string;
  name: string;
  credits: number;
  faculty_id: number;
  faculty_name: string;
  attendance_percentage: number | null;
  marks_percentage: number | null;
  completed_assessments: number;
  total_assessments: number;
}

interface RiskFactor {
  key: string;
  label: string;
  observation: string;
  contribution: number;
}

interface PersonalRisk {
  score: number;
  level: "low" | "medium" | "high";
  computed_at: string;
  contributing_factors: RiskFactor[];
}

interface Dashboard {
  attendance_percentage: number | null;
  marks_percentage: number | null;
  enrolled_courses: number;
  courses: CourseProgress[];
  risk: PersonalRisk | null;
}

interface AcademicProfile {
  name: string;
  department: string;
  department_id: number;
  year: number;
  semester: number;
}

interface AcademicSubject {
  code: string;
  name: string;
  faculty: string[];
}

interface AcademicSubjects {
  year: number;
  semester: number;
  subjects: AcademicSubject[];
}

interface StudentAssignment {
  id: number;
  subject_id: number;
  subject_code: string;
  subject_name: string;
  title: string;
  description: string | null;
  due_date: string;
  max_marks: number;
  status: "open" | "overdue" | "submitted";
  submitted_at: string | null;
  answer_text: string | null;
  marks?: number | string | null;
  feedback?: string | null;
}

interface JourneyEvent {
  occurred_at: string;
  event_type: string;
  title: string;
  description: string;
}

interface Journey {
  events: JourneyEvent[];
}

interface ReceivedFeedback {
  id: number;
  faculty_name: string;
  course_name: string | null;
  message: string;
  created_at: string;
}

interface GivenFeedback {
  id: number;
  faculty_name: string;
  course_name: string;
  rating: number;
  comments: string | null;
  submitted_at: string;
}

interface FeedbackCollection {
  received: ReceivedFeedback[];
  submitted: GivenFeedback[];
}

interface Resource<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

function useStudentResource<T>(path: string | null): Resource<T> {
  const { accessToken } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let mounted = true;
    if (path === null) {
      return () => {
        mounted = false;
      };
    }
    setData(null);
    setError(null);
    setIsLoading(true);
    apiRequest<T>(path, {}, accessToken ?? undefined)
      .then((value) => {
        if (mounted) {
          setData(value);
        }
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(cause instanceof Error ? cause.message : "Unable to load this page.");
        }
      })
      .finally(() => {
        if (mounted) {
          setIsLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [accessToken, path, requestVersion]);

  return {
    data,
    isLoading,
    error,
    reload: () => setRequestVersion((version) => version + 1),
  };
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
  if (isLoading) {
    return <div className="student-state" role="status">Loading your information…</div>;
  }
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
  if (isEmpty) {
    return <div className="student-state">{emptyMessage}</div>;
  }
  return children;
}

function MetricCard({
  label,
  value,
  suffix = "%",
}: {
  label: string;
  value: number | null;
  suffix?: string;
}) {
  return (
    <article className="student-metric">
      <span>{label}</span>
      <strong>{value === null ? "—" : `${value}${suffix}`}</strong>
      <p>{value === null ? "No records yet" : "Based on your recorded activity"}</p>
    </article>
  );
}

function MyAcademics() {
  const { accessToken } = useAuth();
  const profile = useStudentResource<AcademicProfile>("/student/profile");
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedSemester, setSelectedSemester] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const year = selectedYear ?? profile.data?.year;
  const semester = selectedSemester ?? profile.data?.semester;
  const subjectsPath = profile.data && year !== undefined && semester !== undefined
    ? `/student/subjects?year=${year}&semester=${semester}`
    : null;
  const subjects = useStudentResource<AcademicSubjects>(subjectsPath);
  const hasChanges = profile.data !== null
    && (year !== profile.data.year || semester !== profile.data.semester);

  async function saveAcademicYear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (year === undefined || semester === undefined) {
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      await apiRequest<AcademicProfile>(
        "/student/profile",
        {
          method: "PUT",
          body: JSON.stringify({ year, semester }),
        },
        accessToken ?? undefined,
      );
      setSaveMessage("Your current year and semester were updated.");
      profile.reload();
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : "Unable to update your academic profile.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section aria-labelledby="academics-heading" className="student-panel">
      <div className="student-panel-heading">
        <div>
          <p className="eyebrow">Department and curriculum</p>
          <h2 id="academics-heading">My academics</h2>
        </div>
      </div>
      <ScreenState
        emptyMessage=""
        error={profile.error}
        isEmpty={false}
        isLoading={profile.isLoading}
        onRetry={profile.reload}
      >
        {profile.data && year !== undefined && semester !== undefined && (
          <>
            <form className="academic-controls" onSubmit={saveAcademicYear}>
              <div className="academic-field" style={{ display: "grid", gap: "0.35rem" }}><label htmlFor="academic-department">Department</label>
              <select
                disabled
                id="academic-department"
                value={profile.data.department_id}
              >
                <option value={profile.data.department_id}>{profile.data.department}</option>
              </select></div>
              <div className="academic-field" style={{ display: "grid", gap: "0.35rem" }}><label htmlFor="academic-year">Year</label>
              <select
                id="academic-year"
                onChange={(event) => {
                  setSelectedYear(Number(event.target.value));
                  setSaveMessage(null);
                }}
                value={year}
              >
                {[1, 2, 3, 4].map((value) => (
                  <option key={value} value={value}>Year {value}</option>
                ))}
              </select></div>
              <div className="academic-field" style={{ display: "grid", gap: "0.35rem" }}><label htmlFor="academic-semester">Semester</label>
              <select
                id="academic-semester"
                onChange={(event) => {
                  setSelectedSemester(Number(event.target.value));
                  setSaveMessage(null);
                }}
                value={semester}
              >
                {[1, 2].map((value) => (
                  <option key={value} value={value}>Semester {value}</option>
                ))}
              </select></div>
              <button className="button button-small" disabled={!hasChanges || isSaving} type="submit">
                {isSaving ? "Saving…" : "Save current year"}
              </button>
            </form>
            {saveError && <p className="form-error" role="alert">{saveError}</p>}
            {saveMessage && <p className="form-success" role="status">{saveMessage}</p>}
            <div className="academic-subjects">
              <h3>Year {year} · Semester {semester} subjects</h3>
              <ScreenState
                emptyMessage="No subjects are listed for this year and semester yet."
                error={subjects.error}
                isEmpty={!subjects.data || subjects.data.subjects.length === 0}
                isLoading={subjects.isLoading}
                onRetry={subjects.reload}
              >
                {subjects.data && subjects.data.subjects.length > 0 && (
                  <div className="academic-table-scroll">
                    <table className="academic-table">
                      <thead>
                        <tr>
                          <th scope="col">Code</th>
                          <th scope="col">Subject</th>
                          <th scope="col">Faculty</th>
                        </tr>
                      </thead>
                      <tbody>
                        {subjects.data.subjects.map((subject) => (
                          <tr key={subject.code}>
                            <td>{subject.code}</td>
                            <td>{subject.name}</td>
                            <td>{subject.faculty.length ? subject.faculty.join(", ") : "Faculty not assigned yet"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </ScreenState>
            </div>
            <StudentAssignmentList />
          </>
        )}
      </ScreenState>
    </section>
  );
}

function StudentAssignmentList() {
  const { accessToken } = useAuth();
  const assignments = useStudentResource<StudentAssignment[]>("/student/assignments");
  const [openId, setOpenId] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  async function submit(assignmentId: number) {
    const answer = (answers[assignmentId] ?? "").trim();
    if (!answer) {
      setSubmitError("Write your answer before submitting.");
      return;
    }
    setSubmittingId(assignmentId);
    setSubmitError(null);
    setSubmitMessage(null);
    try {
      await apiRequest(`/student/assignments/${assignmentId}/submit`, {
        method: "POST",
        body: JSON.stringify({ answer_text: answer }),
      }, accessToken ?? undefined);
      setSubmitMessage("Assignment submitted.");
      assignments.reload();
    } catch (cause) {
      setSubmitError(cause instanceof Error ? cause.message : "Unable to submit this assignment.");
    } finally {
      setSubmittingId(null);
    }
  }

  return (
    <section aria-labelledby="student-assignments-heading" className="academic-subjects">
      <h3 id="student-assignments-heading">Assignments</h3>
      {submitError && <p className="form-error" role="alert">{submitError}</p>}
      {submitMessage && <p className="form-success" role="status">{submitMessage}</p>}
      <ScreenState
        emptyMessage="There are no assignments for your current subjects."
        error={assignments.error}
        isEmpty={!assignments.data || assignments.data.length === 0}
        isLoading={assignments.isLoading}
        onRetry={assignments.reload}
      >
        {assignments.data && assignments.data.length > 0 && (
          <div className="academic-table-scroll">
            <table className="academic-table">
              <thead>
                <tr>
                  <th scope="col">Subject</th>
                  <th scope="col">Assignment</th>
                  <th scope="col">Due date</th>
                  <th scope="col">Status</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              {assignments.data.map((assignment) => {
                const isOpen = openId === assignment.id;
                const isSubmitted = assignment.status === "submitted";
                return (
                  <tbody key={assignment.id}>
                    <tr>
                      <td>{assignment.subject_code} - {assignment.subject_name}</td>
                      <td><strong>{assignment.title}</strong></td>
                      <td>{assignment.due_date}</td>
                      <td>{assignment.status}</td>
                      <td>
                        <button
                          aria-expanded={isOpen}
                          className="button button-small button-outline"
                          onClick={() => setOpenId(isOpen ? null : assignment.id)}
                          type="button"
                        >
                          {isOpen ? "Close" : isSubmitted ? "View" : "Open"}
                        </button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={5}>
                          <div style={{ display: "grid", gap: "0.75rem", padding: "0.75rem 0" }}>
                            <p>
                              <strong>{assignment.title}</strong> (due {assignment.due_date}, max marks {assignment.max_marks})
                            </p>
                            <p style={{ whiteSpace: "pre-wrap" }}>
                              {assignment.description ?? "No instructions were added for this assignment."}
                            </p>
                            {isSubmitted ? (
                              <>
                                {assignment.marks != null && (
                              <p><strong>Marks: {assignment.marks} / {assignment.max_marks}</strong></p>
                            )}
                            {assignment.feedback && (
                              <p style={{ whiteSpace: "pre-wrap" }}>Faculty feedback: {assignment.feedback}</p>
                            )}
                            <p><strong>Your submitted answer</strong></p>
                                <p style={{ whiteSpace: "pre-wrap" }}>
                                  {assignment.answer_text ?? "No answer text was saved for this submission."}
                                </p>
                              </>
                            ) : (
                              <>
                                <label htmlFor={`assignment-answer-${assignment.id}`}>Your answer</label>
                                <textarea
                                  id={`assignment-answer-${assignment.id}`}
                                  maxLength={10000}
                                  onChange={(event) =>
                                    setAnswers((current) => ({ ...current, [assignment.id]: event.target.value }))
                                  }
                                  rows={8}
                                  value={answers[assignment.id] ?? ""}
                                />
                                <div>
                                  <button
                                    className="button button-small"
                                    disabled={submittingId === assignment.id}
                                    onClick={() => void submit(assignment.id)}
                                    type="button"
                                  >
                                    {submittingId === assignment.id ? "Submitting..." : "Submit assignment"}
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                );
              })}
            </table>
          </div>
        )}
      </ScreenState>
    </section>
  );
}

function DashboardScreen() {
  const { data, isLoading, error, reload } = useStudentResource<Dashboard>("/student/dashboard");

  return (
    <>
      <header className="student-heading">
        <p className="eyebrow">Your learning snapshot</p>
        <h1 className="portal-title">Your student journey</h1>
        <p className="intro">A personal overview of your courses and recorded progress.</p>
      </header>
      <ScreenState
        emptyMessage="Your dashboard is ready. Course activity will appear here when it is recorded."
        error={error}
        isEmpty={!data || data.enrolled_courses === 0}
        isLoading={isLoading}
        onRetry={reload}
      >
        {data && (
          <>
            <div className="student-metrics">
              <MetricCard label="Attendance" value={data.attendance_percentage} />
              <MetricCard label="Average marks" value={data.marks_percentage} />
              <MetricCard label="Courses" suffix="" value={data.enrolled_courses} />
            </div>
            <section aria-labelledby="course-heading" className="student-panel">
              <div className="student-panel-heading">
                <div>
                  <p className="eyebrow">This semester</p>
                  <h2 id="course-heading">My courses</h2>
                </div>
                <Link className="text-link" to="/student/journey">View your journey</Link>
              </div>
              {data.courses.length === 0 ? (
                <p className="student-state">No courses have been added to your schedule yet.</p>
              ) : (
                <div className="course-list">
                  {data.courses.map((course) => (
                    <article className="course-card" key={course.course_id}>
                      <div className="course-name">
                        <span>{course.code} · {course.credits} credits</span>
                        <h3>{course.name}</h3>
                        <p>Instructor: {course.faculty_name}</p>
                      </div>
                      <div className="course-progress">
                        <span>Attendance</span>
                        <strong>{course.attendance_percentage === null ? "—" : `${course.attendance_percentage}%`}</strong>
                      </div>
                      <div className="course-progress">
                        <span>Marks</span>
                        <strong>{course.marks_percentage === null ? "—" : `${course.marks_percentage}%`}</strong>
                      </div>
                      <div className="course-assessments">
                        {course.completed_assessments} of {course.total_assessments} assessments submitted
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
            <section aria-labelledby="risk-heading" className="student-panel risk-panel">
              <div className="student-panel-heading">
                <div>
                  <p className="eyebrow">Personal progress signal</p>
                  <h2 id="risk-heading">Risk status</h2>
                </div>
                {data.risk && (
                  <span className={`risk-badge risk-${data.risk.level}`}>
                    {data.risk.level} risk
                  </span>
                )}
              </div>
              {!data.risk ? (
                <p className="student-state">No personal risk assessment is available yet.</p>
              ) : (
                <>
                  <p className="risk-summary">
                    Current score: <strong>{Math.round(data.risk.score * 100)} / 100</strong>
                    <span> · Updated {formatDate(data.risk.computed_at)}</span>
                  </p>
                  {data.risk.contributing_factors.length === 0 ? (
                    <p className="student-state">No contributing-factor details are available for this assessment.</p>
                  ) : (
                    <ul className="factor-list">
                      {data.risk.contributing_factors.map((factor) => (
                        <li key={factor.key}>
                          <strong>{factor.label}</strong>
                          <span>{factor.observation}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="student-disclaimer">
                    This indicator is a support signal, not a judgment or diagnosis.
                  </p>
                </>
              )}
            </section>
          </>
        )}
      </ScreenState>
      <MyAcademics />
    </>
  );
}

function JourneyScreen() {
  const { data, isLoading, error, reload } = useStudentResource<Journey>("/student/journey");

  return (
    <>
      <header className="student-heading">
        <p className="eyebrow">Your learning history</p>
        <h1 className="portal-title">Journey timeline</h1>
        <p className="intro">Course enrollments, class attendance, assessment submissions, and support activity.</p>
      </header>
      <ScreenState
        emptyMessage="Your timeline is empty. Course activity will appear here as it is recorded."
        error={error}
        isEmpty={!data || data.events.length === 0}
        isLoading={isLoading}
        onRetry={reload}
      >
        {data && data.events.length > 0 && (
          <ol aria-label="Student journey" className="journey-timeline">
            {data.events.map((event, index) => (
              <li className="journey-event" key={`${event.event_type}-${event.occurred_at}-${index}`}>
                <span aria-hidden="true" className={`journey-marker marker-${event.event_type}`} />
                <div className="journey-event-content">
                  <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
                  <h2>{event.title}</h2>
                  <p>{event.description}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </ScreenState>
    </>
  );
}

function FeedbackScreen() {
  const { accessToken } = useAuth();
  const feedback = useStudentResource<FeedbackCollection>("/student/feedback");
  const courses = useStudentResource<Dashboard>("/student/dashboard");
  const [courseId, setCourseId] = useState("");
  const [rating, setRating] = useState("5");
  const [comments, setComments] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (courses.data && courses.data.courses.length > 0 && !courseId) {
      setCourseId(String(courses.data.courses[0].course_id));
    }
  }, [courseId, courses.data]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);
    const selectedCourse = courses.data?.courses.find(
      (course) => course.course_id === Number(courseId),
    );
    if (!selectedCourse) {
      setSubmitError("Select one of your enrolled courses.");
      setIsSubmitting(false);
      return;
    }

    try {
      await apiRequest<{ id: number; message: string }>(
        "/student/feedback",
        {
          method: "POST",
          body: JSON.stringify({
            course_id: selectedCourse.course_id,
            faculty_id: selectedCourse.faculty_id,
            rating: Number(rating),
            comments: comments.trim() || null,
          }),
        },
        accessToken ?? undefined,
      );
      setComments("");
      setSuccessMessage("Thank you. Your feedback was submitted.");
      feedback.reload();
    } catch (cause) {
      setSubmitError(cause instanceof Error ? cause.message : "Unable to submit feedback.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <header className="student-heading">
        <p className="eyebrow">A two-way conversation</p>
        <h1 className="portal-title">Feedback</h1>
        <p className="intro">Read feedback from faculty and share feedback about your courses.</p>
      </header>
      <section aria-labelledby="received-heading" className="student-panel">
        <div className="student-panel-heading">
          <div>
            <p className="eyebrow">From your faculty</p>
            <h2 id="received-heading">Feedback received</h2>
          </div>
        </div>
        <ScreenState
          emptyMessage="You have not received faculty feedback yet."
          error={feedback.error}
          isEmpty={!feedback.data || feedback.data.received.length === 0}
          isLoading={feedback.isLoading}
          onRetry={feedback.reload}
        >
          {feedback.data && feedback.data.received.length > 0 && (
            <div className="feedback-list">
              {feedback.data.received.map((item) => (
                <article className="feedback-card" key={item.id}>
                  <div className="feedback-meta">
                    <strong>{item.faculty_name}</strong>
                    <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                  </div>
                  {item.course_name && <p className="feedback-course">{item.course_name}</p>}
                  <p>{item.message}</p>
                </article>
              ))}
            </div>
          )}
        </ScreenState>
      </section>
      <section aria-labelledby="submit-heading" className="student-panel">
        <p className="eyebrow">Help improve your learning experience</p>
        <h2 id="submit-heading">Share course feedback</h2>
        {courses.isLoading ? (
          <p className="student-state" role="status">Loading your enrolled courses…</p>
        ) : courses.error ? (
          <div className="student-state student-error" role="alert">
            <p>{courses.error}</p>
            <button className="button button-small button-outline" onClick={courses.reload} type="button">Try again</button>
          </div>
        ) : !courses.data || courses.data.courses.length === 0 ? (
          <p className="student-state">Enroll in a course before submitting feedback.</p>
        ) : (
          <form className="student-feedback-form" onSubmit={handleSubmit}>
            <label htmlFor="feedback-course">Course and faculty</label>
            <select
              id="feedback-course"
              onChange={(event) => setCourseId(event.target.value)}
              required
              value={courseId}
            >
              {courses.data.courses.map((course) => (
                <option key={course.course_id} value={course.course_id}>
                  {course.code} · {course.name} — {course.faculty_name}
                </option>
              ))}
            </select>
            <label htmlFor="feedback-rating">Rating</label>
            <select
              id="feedback-rating"
              onChange={(event) => setRating(event.target.value)}
              value={rating}
            >
              <option value="5">5 — Excellent</option>
              <option value="4">4 — Good</option>
              <option value="3">3 — Satisfactory</option>
              <option value="2">2 — Needs improvement</option>
              <option value="1">1 — Poor</option>
            </select>
            <label htmlFor="feedback-comments">Comments (optional)</label>
            <textarea
              id="feedback-comments"
              maxLength={2000}
              onChange={(event) => setComments(event.target.value)}
              rows={4}
              value={comments}
            />
            {submitError && <p className="form-error" role="alert">{submitError}</p>}
            {successMessage && <p className="form-success" role="status">{successMessage}</p>}
            <button className="button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Submitting…" : "Submit feedback"}
            </button>
          </form>
        )}
      </section>
      <section aria-labelledby="submitted-heading" className="student-panel">
        <p className="eyebrow">Your voice</p>
        <h2 id="submitted-heading">Feedback submitted</h2>
        {feedback.isLoading ? (
          <p className="student-state" role="status">Loading your feedback history…</p>
        ) : feedback.error ? (
          <div className="student-state student-error" role="alert">
            <p>{feedback.error}</p>
            <button className="button button-small button-outline" onClick={feedback.reload} type="button">Try again</button>
          </div>
        ) : !feedback.data || feedback.data.submitted.length === 0 ? (
          <p className="student-state">You have not submitted feedback yet.</p>
        ) : (
          <div className="feedback-list">
            {feedback.data.submitted.map((item) => (
              <article className="feedback-card" key={item.id}>
                <div className="feedback-meta">
                  <strong>{item.course_name}</strong>
                  <time dateTime={item.submitted_at}>{formatDate(item.submitted_at)}</time>
                </div>
                <p>{item.faculty_name} · {item.rating} / 5</p>
                {item.comments && <p>{item.comments}</p>}
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Date unavailable"
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

const studentNavigation = [
  { to: "/student", label: "Overview", end: true },
  { to: "/student/journey", label: "My journey", end: false },
  { to: "/student/feedback", label: "Feedback", end: false },
];

export function StudentPortalLayout() {
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setLogoutError(null);
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (cause) {
      setLogoutError(cause instanceof Error ? cause.message : "Unable to sign out.");
      setIsLoggingOut(false);
    }
  }

  return (
    <main className="portal-page">
      <header className="topbar">
        <Link className="brand" to="/student">
          <span className="brand-mark" aria-hidden="true">S</span>
          Student Success
        </Link>
        <div className="account-menu">
          <span className="account-name">{user?.full_name}</span>
          <ChangePassword />
<button className="button button-small button-outline" disabled={isLoggingOut} onClick={handleLogout} type="button">
            {isLoggingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </header>
      <nav aria-label="Student portal" className="student-navigation">
        {studentNavigation.map((item) => (
          <NavLink
            className={({ isActive }) => `student-nav-link${isActive ? " active" : ""}`}
            end={item.end}
            key={item.to}
            to={item.to}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="student-content">
        {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
        <Outlet />
      </div>
    </main>
  );
}

export const StudentDashboard = DashboardScreen;
export const StudentJourney = JourneyScreen;
export const StudentFeedback = FeedbackScreen;
