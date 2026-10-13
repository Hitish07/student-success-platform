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

function useStudentResource<T>(path: string): Resource<T> {
  const { accessToken } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let mounted = true;
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
