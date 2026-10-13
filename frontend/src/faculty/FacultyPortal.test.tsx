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
      } else if (url.endsWith("/faculty/doubts")) {
        body = mode === "empty"
          ? { topics: [], total_doubts: 0 }
          : {
              topics: [
                {
                  subject_id: 1,
                  subject_code: "CS201",
                  subject_name: "Data Structures",
                  total: 3,
                  recent: [
                    {
                      question: "How do I think about recursion?",
                      answer_preview: "Think about the base case first...",
                      created_at: "2026-10-13T10:00:00Z",
                    },
                  ],
                },
              ],
              total_doubts: 3,
            };
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

  it("shows doubts grouped by subject on the faculty doubts screen", async () => {
    installFacultyApi("populated");

    render(
      <MemoryRouter initialEntries={["/faculty/doubts"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Doubts and questions")).toBeTruthy();
    expect(await screen.findByText("CS201 - Data Structures")).toBeTruthy();
    expect(screen.getByText("3 questions")).toBeTruthy();
    expect(screen.getByText(/How do I think about recursion\?/)).toBeTruthy();
    expect(screen.getByText(/base case first/i)).toBeTruthy();
  });

});
