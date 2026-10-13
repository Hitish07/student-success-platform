import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  Link,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { apiRequest } from "./api";
import { AnalyticsDashboard } from "./analytics/AnalyticsDashboard";
import {
  FacultyAssessments,
  FacultyAttendance,
  FacultyDashboard,
  FacultyFeedback,
  FacultyPortalLayout,
  FacultySupport,
} from "./faculty/FacultyPortal";
import {
  AuthProvider,
  portalPaths,
  roleLabels,
  useAuth,
  type Department,
  type UserRole,
} from "./auth/AuthContext";
import {
  StudentDashboard,
  StudentFeedback,
  StudentJourney,
  StudentPortalLayout,
} from "./student/StudentPortal";

function Home() {
  const { user, isRestoring } = useAuth();
  if (isRestoring) {
    return <LoadingPage />;
  }
  if (user) {
    return <Navigate to={portalPaths[user.role]} replace />;
  }
  return (
    <main className="page">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">S</span>
          Student Success
        </Link>
        <nav aria-label="Account">
          <Link className="nav-link" to="/login">Sign in</Link>
          <Link className="button button-small" to="/register">Create student account</Link>
        </nav>
      </header>
      <section className="welcome" aria-labelledby="welcome-title">
        <p className="eyebrow">A clearer path to student success</p>
        <h1 id="welcome-title">Every student journey matters.</h1>
        <p className="intro">
          A shared foundation for understanding progress, recognizing when
          support may help, and learning which interventions make a difference.
        </p>
        <Link className="button" to="/login">Sign in to your portal</Link>
        <p className="demo-notice">
          Development preview. Seeded records are fictional and for demonstration only.
        </p>
      </section>
    </main>
  );
}

function LoadingPage() {
  return (
    <main className="page loading-page">
      <p role="status">Restoring your secure session…</p>
    </main>
  );
}

function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">S</span>
          Student Success
        </Link>
        <Link className="nav-link" to="/">Home</Link>
      </header>
      <section className="auth-card">{children}</section>
    </main>
  );
}

function LoginPage() {
  const { login, user, isRestoring } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isRestoring) {
    return <LoadingPage />;
  }
  if (user) {
    return <Navigate to={portalPaths[user.role]} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const currentUser = await login(email, password);
      const returnTo = (location.state as { from?: string } | null)?.from;
      navigate(returnTo ?? portalPaths[currentUser.role], { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDemoLogin(email: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      const currentUser = await login(email, "DemoPass123!");
      navigate(portalPaths[currentUser.role], { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in to the demo.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthFrame>
      <p className="eyebrow">Welcome back</p>
      <h1 className="auth-title">Sign in</h1>
      <p className="auth-copy">Use your institution account to continue.</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="email">Email address</label>
        <input
          autoComplete="username"
          id="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
        <label htmlFor="password">Password</label>
        <input
          autoComplete="current-password"
          id="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <section className="demo-login" aria-label="Analytics demo accounts">
        <p>Or open a seeded analytics demo:</p>
        <div>
          <button className="button button-small button-outline" disabled={isSubmitting} onClick={() => void handleDemoLogin("dean.cs@demo.invalid")} type="button">
            Try Dean demo
          </button>
          <button className="button button-small button-outline" disabled={isSubmitting} onClick={() => void handleDemoLogin("principal@demo.invalid")} type="button">
            Try Principal demo
          </button>
        </div>
        <small>Fictional demo data · DemoPass123!</small>
      </section>
      <p className="auth-switch">
        Student without an account? <Link to="/register">Create one</Link>
      </p>
    </AuthFrame>
  );
}

function RegisterPage() {
  const { register, user, isRestoring } = useAuth();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [isLoadingDepartments, setIsLoadingDepartments] = useState(true);
  const [departmentError, setDepartmentError] = useState<string | null>(null);
  const [departmentLoadAttempt, setDepartmentLoadAttempt] = useState(0);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    setIsLoadingDepartments(true);
    setDepartmentError(null);
    apiRequest<Department[]>("/auth/departments", { signal: AbortSignal.timeout(8000) })
      .then((rows) => {
        if (mounted) {
          setDepartments(rows);
          setDepartmentId(String(rows[0]?.id ?? ""));
        }
      })
      .catch(() => {
        if (mounted) {
          setDepartmentError(
            "Unable to load departments. Check that the API and database are running, then retry.",
          );
        }
      })
      .finally(() => {
        if (mounted) {
          setIsLoadingDepartments(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [departmentLoadAttempt]);

  if (isRestoring) {
    return <LoadingPage />;
  }
  if (user) {
    return <Navigate to={portalPaths[user.role]} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const registeredUser = await register({
        email,
        full_name: fullName,
        password,
        department_id: Number(departmentId),
      });
      navigate(portalPaths[registeredUser.role], { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create your account.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthFrame>
      <p className="eyebrow">Student access</p>
      <h1 className="auth-title">Create your account</h1>
      <p className="auth-copy">Registration is for students. Staff accounts are provisioned by the institution.</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="full-name">Full name</label>
        <input
          autoComplete="name"
          id="full-name"
          maxLength={160}
          onChange={(event) => setFullName(event.target.value)}
          required
          value={fullName}
        />
        <label htmlFor="email">Institution email</label>
        <input
          autoComplete="email"
          id="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
        <label htmlFor="department">Department</label>
        <select
          disabled={isLoadingDepartments || departments.length === 0}
          id="department"
          onChange={(event) => setDepartmentId(event.target.value)}
          required
          value={departmentId}
        >
          {departments.length === 0 && (
            <option value="">
              {isLoadingDepartments ? "Loading departments…" : "Departments unavailable"}
            </option>
          )}
          {departments.map((department) => (
            <option key={department.id} value={department.id}>{department.name}</option>
          ))}
        </select>
        {departmentError && <p className="form-error" role="alert">{departmentError}</p>}
        {departmentError && (
          <button
            className="button button-small button-outline"
            disabled={isLoadingDepartments}
            onClick={() => setDepartmentLoadAttempt((attempt) => attempt + 1)}
            type="button"
          >
            Retry loading departments
          </button>
        )}
        <label htmlFor="password">Password</label>
        <input
          autoComplete="new-password"
          id="password"
          minLength={12}
          maxLength={72}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        <p className="field-hint">Use at least 12 characters (maximum 72 UTF-8 bytes).</p>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button" disabled={isSubmitting || isLoadingDepartments || departments.length === 0} type="submit">
          {isSubmitting ? "Creating account…" : "Create student account"}
        </button>
      </form>
      <p className="auth-switch">
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </AuthFrame>
  );
}

function RequireRole({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user, isRestoring } = useAuth();
  const location = useLocation();

  if (isRestoring) {
    return <LoadingPage />;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (user.role !== role) {
    return <Navigate to={portalPaths[user.role]} replace />;
  }
  return children;
}

function RequirePortalRole({ role }: { role: UserRole }) {
  const { user, isRestoring } = useAuth();
  const location = useLocation();

  if (isRestoring) {
    return <LoadingPage />;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (user.role !== role) {
    return <Navigate to={portalPaths[user.role]} replace />;
  }
  return <Outlet />;
}

const portalContent: Record<UserRole, { title: string; description: string }> = {
  student: {
    title: "Your student journey",
    description: "See your courses, progress, feedback, and support in one place.",
  },
  faculty: {
    title: "Faculty workspace",
    description: "Support your assigned students and keep course progress up to date.",
  },
  dean: {
    title: "Department overview",
    description: "Review department progress and support across your academic community.",
  },
  principal: {
    title: "Institution overview",
    description: "Explore student success signals across the institution.",
  },
};

function RolePortal({ role }: { role: UserRole }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const content = portalContent[role];

  async function handleLogout() {
    setLogoutError(null);
    setIsLoggingOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (cause) {
      setIsLoggingOut(false);
      setLogoutError(cause instanceof Error ? cause.message : "Unable to sign out.");
    }
  }

  return (
    <main className="portal-page">
      <header className="topbar">
        <Link className="brand" to={portalPaths[role]}>
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
      <section aria-labelledby="portal-title" className="portal-content">
        <p className="eyebrow">{roleLabels[role]} portal</p>
        <h1 className="portal-title" id="portal-title">{content.title}</h1>
        <p className="intro">{content.description}</p>
        <section aria-label="Account information" className="portal-card">
          <span aria-hidden="true" className="profile-initial">{user?.full_name.charAt(0).toUpperCase()}</span>
          <div className="profile-details">
            <h2>{user?.full_name}</h2>
            <p>{user?.email}</p>
            <span className="role-badge">{roleLabels[role]}</span>
          </div>
        </section>
        {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
        <p className="demo-notice">
          Phase 2 access is active. Course, analytics, and journey data will be added in subsequent phases.
        </p>
      </section>
    </main>
  );
}

function NotFound() {
  return (
    <main className="page">
      <section className="welcome">
        <p className="eyebrow">Page not found</p>
        <h1>Let’s get you back on track.</h1>
        <Link className="back-link" to="/">Return home</Link>
      </section>
    </main>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequirePortalRole role="student" />}>
        <Route element={<StudentPortalLayout />} path="/student">
          <Route element={<StudentDashboard />} index />
          <Route element={<StudentJourney />} path="journey" />
          <Route element={<StudentFeedback />} path="feedback" />
        </Route>
      </Route>
      <Route element={<RequirePortalRole role="faculty" />}>
        <Route element={<FacultyPortalLayout />} path="/faculty">
          <Route element={<FacultyDashboard />} index />
          <Route element={<FacultyAttendance />} path="attendance" />
          <Route element={<FacultyAssessments />} path="assessments" />
          <Route element={<FacultySupport />} path="support" />
          <Route element={<FacultyFeedback />} path="feedback" />
        </Route>
      </Route>
      <Route element={<RequirePortalRole role="dean" />}>
        <Route element={<AnalyticsDashboard role="dean" />} path="/dean" />
      </Route>
      <Route element={<RequirePortalRole role="principal" />}>
        <Route element={<AnalyticsDashboard role="principal" />} path="/principal" />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
