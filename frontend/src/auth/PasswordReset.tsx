import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { apiRequest } from "../api";

function Frame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">S</span>
          Student Success
        </Link>
        <Link className="nav-link" to="/login">Sign in</Link>
      </header>
      <section className="auth-card">{children}</section>
    </main>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await apiRequest("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: email.trim() }),
      });
      setSent(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to send the reset request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Frame>
      <p className="eyebrow">Account recovery</p>
      <h1 className="auth-title">Forgot password</h1>
      {sent ? (
        <>
          <p className="form-success" role="status">
            If an account with that email exists, a reset link has been sent.
          </p>
          <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
        </>
      ) : (
        <>
          <p className="auth-copy">Enter your account email and we will send a reset link.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <label htmlFor="forgot-email">Email address</label>
            <input
              autoComplete="username"
              id="forgot-email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
          <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
        </>
      )}
    </Frame>
  );
}

export function ResetPasswordPage() {
  const token = new URLSearchParams(useLocation().search).get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiRequest("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setDone(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reset the password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!token) {
    return (
      <Frame>
        <h1 className="auth-title">Reset password</h1>
        <p className="form-error" role="alert">This reset link is missing its token.</p>
        <p className="auth-switch"><Link to="/forgot-password">Request a new link</Link></p>
      </Frame>
    );
  }

  return (
    <Frame>
      <p className="eyebrow">Account recovery</p>
      <h1 className="auth-title">Choose a new password</h1>
      {done ? (
        <>
          <p className="form-success" role="status">Your password was updated. You can sign in now.</p>
          <p className="auth-switch"><Link to="/login">Go to sign in</Link></p>
        </>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="new-password">New password</label>
          <input
            autoComplete="new-password"
            id="new-password"
            maxLength={72}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          <label htmlFor="confirm-password">Confirm new password</label>
          <input
            autoComplete="new-password"
            id="confirm-password"
            maxLength={72}
            onChange={(event) => setConfirm(event.target.value)}
            required
            type="password"
            value={confirm}
          />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Saving..." : "Update password"}
          </button>
        </form>
      )}
    </Frame>
  );
}
