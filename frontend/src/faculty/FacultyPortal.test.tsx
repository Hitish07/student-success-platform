import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";

const facultySession = {
  access_token: "faculty-access-token",
  refresh_token: "faculty-refresh-token",
  expires_in: 900,
  user: {
    id: 22,
    email: "faculty@example.invalid",
    full_name: "Faculty Example",
    role: "faculty",
    department_id: 1,
  },
};

function installFacultyApi(mode: "populated" | "empty" | "error" = "populated") {
  sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      let body: unknown = {};
      let status = 200;
      if (url.endsWith("/auth/refresh")) {
        body = facultySession;
      } else if (url.endsWith("/faculty/dashboard")) {
        if (mode === "error") {
          body = { detail: "Faculty dashboard unavailable." };
          status = 503;
        } else {
          body = {
            courses: mode === "empty" ? [] : [
              { id: 3, code: "FAC101", name: "Faculty Course", credits: 3, enrolled_students: 2 },
            ],
            assigned_students: mode === "empty" ? 0 : 2,
            at_risk_students: 1,
            open_alerts: 1,
          };
        }
      } else {
        body = [];
      }
      return Promise.resolve(new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }));
    }),
  );
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("faculty portal", () => {
  it("renders assigned-course dashboard after restoring a faculty session", async () => {
    installFacultyApi();

    render(
      <MemoryRouter initialEntries={["/faculty"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("FAC101 · 3 credits")).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Faculty portal" })).toBeTruthy();
  });

  it("shows an empty course state when the faculty member has no assignments", async () => {
    installFacultyApi("empty");

    render(
      <MemoryRouter initialEntries={["/faculty"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No courses are assigned to your account yet.")).toBeTruthy();
  });

  it("shows a recoverable dashboard error", async () => {
    installFacultyApi("error");

    render(
      <MemoryRouter initialEntries={["/faculty"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Faculty dashboard unavailable.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });
});
