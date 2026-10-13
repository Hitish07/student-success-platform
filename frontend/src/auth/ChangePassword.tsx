import { useState, type FormEvent } from "react";

import { apiRequest } from "../api";
import { useAuth } from "./AuthContext";

export function ChangePassword() {
  const { accessToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function close() {
    setOpen(false);
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (next.length < 12) {
      setError("New password must be at least 12 characters.");
      return;
    }
    if (next !== confirm) {
      setError("The new passwords do not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiRequest(
        "/auth/change-password",
        { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) },
        accessToken ?? undefined,
      );
      close();
      setMessage("Password changed.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to change the password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <button
        aria-expanded={open}
        className="button button-small button-outline"
        onClick={() => (open ? close() : setOpen(true))}
        type="button"
      >
        Change password
      </button>
      {message && <span role="status">{message}</span>}
      {open && (
        <form
          onSubmit={handleSubmit}
          style={{
            position: "fixed", top: "4rem", right: "1rem", zIndex: 50, display: "grid", gap: "0.5rem",
            width: "min(20rem, 90vw)", padding: "1rem", background: "#fff", color: "#111",
            border: "1px solid #ccc", borderRadius: "8px", boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
          }}
        >
          <label htmlFor="cp-current">Current password</label>
          <input autoComplete="current-password" id="cp-current" maxLength={72} onChange={(e) => setCurrent(e.target.value)} required type="password" value={current} />
          <label htmlFor="cp-new">New password</label>
          <input autoComplete="new-password" id="cp-new" maxLength={72} onChange={(e) => setNext(e.target.value)} required type="password" value={next} />
          <label htmlFor="cp-confirm">Confirm new password</label>
          <input autoComplete="new-password" id="cp-confirm" maxLength={72} onChange={(e) => setConfirm(e.target.value)} required type="password" value={confirm} />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-small" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Saving..." : "Save password"}
          </button>
        </form>
      )}
    </>
  );
}
