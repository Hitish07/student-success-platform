import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";

const studentResponse = {
  access_token: "demo-access-token",
  refresh_token: "rotated-refresh-token",
  expires_in: 900,
  user: {
    id: 7,
    email: "student.demo@example.invalid",
    full_name: "Demo Student",
    role: "student",
    department_id: 1,
  },
};

function apiResponse(url: string) {
  if (url.endsWith("/auth/refresh")) {
    return { status: 200, body: studentResponse };
  }
  if (url.endsWith("/student/profile")) {
    return {
      status: 200,
      body: {
        name: "Demo Student",
        department: "Computer Science",
        department_id: 1,
        year: 2,
        semester: 1,
      },
    };
  }
  if (url.startsWith("/student/subjects")) {
    const advanced = url.includes("year=3");
    return {
      status: 200,
      body: {
        year: advanced ? 3 : 2,
        semester: 1,
        subjects: [
          {
            code: advanced ? "CS301" : "CS201",
            name: advanced ? "Algorithms" : "Data Structures",
            faculty: ["Faculty Member"],
          },
        ],
      },
    };
  }
  if (url.endsWith("/student/assignments")) {
    return { status: 200, body: [] };
  }
  if (url.endsWith("/student/dashboard")) {
    return {
      status: 200,
      body: {
        attendance_percentage: 80,
        marks_percentage: 75,
        enrolled_courses: 1,
        courses: [
          {
            course_id: 9,
            code: "CS101",
            name: "Foundations of Computer Science",
            credits: 3,
            faculty_id: 12,
            faculty_name: "Faculty Member",
            attendance_percentage: 80,
            marks_percentage: 75,
            completed_assessments: 2,
            total_assessments: 2,
          },
        ],
        risk: {
          score: 0.2,
          level: "medium",
          computed_at: "2026-10-12T10:00:00Z",
          contributing_factors: [
            {
              key: "attendance",
              label: "Attendance",
              observation: "80% attendance",
              contribution: 0.09,
            },
          ],
        },
      },
    };
  }
  if (url.endsWith("/student/journey")) {
    return {
      status: 200,
      body: {
        events: [
          {
            occurred_at: "2026-10-12T10:00:00Z",
            event_type: "assessment",
            title: "Submitted · Course project",
            description: "CS101 · 75 of 100 points.",
          },
        ],
      },
    };
  }
  if (url.endsWith("/student/feedback")) {
    return {
      status: 200,
      body: { received: [], submitted: [] },
    };
  }
  return { status: 404, body: { detail: "Not found." } };
}

function installSessionFetch() {
  sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    const response = apiResponse(url);
    return Promise.resolve(
      new Response(JSON.stringify(response.body), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("student portal screens", () => {
  it("loads course, marks, attendance, and personal risk data", async () => {
    const fetchMock = installSessionFetch();

    render(
      <MemoryRouter initialEntries={["/student"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("CS101 · 3 credits")).toBeTruthy();
    expect(screen.getAllByText("80%")).toHaveLength(2);
    expect(screen.getAllByText("75%")).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledWith(
      "/student/dashboard",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
  });

  it("loads academics, browses subjects, and saves the current year and semester", async () => {
    const fetchMock = installSessionFetch();

    render(
      <MemoryRouter initialEntries={["/student"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Data Structures")).toBeTruthy();
    expect(screen.getByLabelText("Department")).toHaveProperty("value", "1");
    expect(screen.getByLabelText("Year")).toHaveProperty("value", "2");
    expect(screen.getByLabelText("Semester")).toHaveProperty("value", "1");
    expect(screen.getByText("Faculty Member")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Year"), { target: { value: "3" } });
    expect(await screen.findByText("Algorithms")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Save current year" }));
    expect(await screen.findByText("Your current year and semester were updated.")).toBeTruthy();
    expect(
      fetchMock.mock.calls.some(
        ([url, options]) =>
          url === "/student/profile"
          && options?.method === "PUT"
          && options.body === JSON.stringify({ year: 3, semester: 1 }),
      ),
    ).toBe(true);
  });

  it("shows academic subject errors and the empty state after retry", async () => {
    sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
    let subjectAttempts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.startsWith("/student/subjects")) {
          subjectAttempts += 1;
          if (subjectAttempts === 1) {
            return Promise.resolve(
              new Response(JSON.stringify({ detail: "Subjects temporarily unavailable." }), {
                status: 503,
                headers: { "Content-Type": "application/json" },
              }),
            );
          }
          return Promise.resolve(
            new Response(JSON.stringify({ year: 2, semester: 1, subjects: [] }), {
              status: 200,
              headers: { "Content-Type": "application/json" },
            }),
          );
        }
        const response = apiResponse(url);
        return Promise.resolve(
          new Response(JSON.stringify(response.body), {
            status: response.status,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );

    render(
      <MemoryRouter initialEntries={["/student"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Subjects temporarily unavailable.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No subjects are listed for this year and semester yet.")).toBeTruthy();
  });

  it("renders the journey timeline and its empty state", async () => {
    installSessionFetch();

    render(
      <MemoryRouter initialEntries={["/student/journey"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Submitted · Course project")).toBeTruthy();

    cleanup();
    sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        const body = url.endsWith("/auth/refresh")
          ? studentResponse
          : url.endsWith("/student/journey")
            ? { events: [] }
            : {};
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
      }),
    );

    render(
      <MemoryRouter initialEntries={["/student/journey"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/timeline is empty/i)).toBeTruthy();
  });

  it("shows a retryable error when the journey request fails", async () => {
    sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/student/journey")) {
          return Promise.resolve(
            new Response(JSON.stringify({ detail: "Timeline unavailable." }), {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }),
          );
        }
        const body = url.endsWith("/auth/refresh") ? studentResponse : {};
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
      }),
    );

    render(
      <MemoryRouter initialEntries={["/student/journey"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Timeline unavailable.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });

  it("shows explicit error and empty states on the feedback screen", async () => {
    sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/student/dashboard")) {
          return Promise.resolve(
            new Response(JSON.stringify({ detail: "Dashboard temporarily unavailable." }), {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }),
          );
        }
        const body = url.endsWith("/auth/refresh") ? studentResponse : { received: [], submitted: [] };
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
      }),
    );

    render(
      <MemoryRouter initialEntries={["/student/feedback"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("You have not received faculty feedback yet.")).toBeTruthy();
    expect(screen.getByText("You have not submitted feedback yet.")).toBeTruthy();
    expect(await screen.findByText("Dashboard temporarily unavailable.")).toBeTruthy();
  });
});
