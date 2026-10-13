import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function tokenResponse() {
  return {
    access_token: "student-access-token",
    refresh_token: "student-refresh-token",
    expires_in: 900,
    user: {
      id: 8,
      email: "new.student@example.invalid",
      full_name: "New Student",
      role: "student",
      department_id: 1,
    },
  };
}

describe("student registration", () => {
  it("loads departments, creates a student account, and opens the student portal", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/auth/departments") {
        return Promise.resolve(jsonResponse([{ id: 1, name: "Computer Science", code: "CS" }]));
      }
      if (url === "/auth/register") {
        return Promise.resolve(jsonResponse(tokenResponse(), 201));
      }
      if (url === "/student/dashboard") {
        return Promise.resolve(jsonResponse({
          attendance_percentage: 80,
          marks_percentage: 75,
          enrolled_courses: 0,
          courses: [],
          risk: null,
        }));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryRouter initialEntries={["/register"]}><App /></MemoryRouter>);

    await screen.findByRole("option", { name: "Computer Science" });
    fireEvent.change(await screen.findByLabelText("Full name"), {
      target: { value: "New Student" },
    });
    fireEvent.change(screen.getByLabelText("Institution email"), {
      target: { value: "new.student@example.invalid" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "LongDemoPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create student account" }));

    expect(await screen.findByRole("navigation", { name: "Student portal" })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/auth/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "new.student@example.invalid",
          full_name: "New Student",
          password: "LongDemoPassword123!",
          department_id: 1,
        }),
      }),
    );
  });

  it("shows the API error when account creation fails", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/auth/departments") {
        return Promise.resolve(jsonResponse([{ id: 1, name: "Computer Science", code: "CS" }]));
      }
      return Promise.resolve(jsonResponse({ detail: "An account with this email already exists." }, 409));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryRouter initialEntries={["/register"]}><App /></MemoryRouter>);

    await screen.findByRole("option", { name: "Computer Science" });
    fireEvent.change(await screen.findByLabelText("Full name"), {
      target: { value: "New Student" },
    });
    fireEvent.change(screen.getByLabelText("Institution email"), {
      target: { value: "new.student@example.invalid" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "LongDemoPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create student account" }));

    const error = await screen.findByRole("alert");
    expect(error.textContent).toContain("An account with this email already exists.");
  });

  it("shows a department loading error and retries the request", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error("API unavailable"))
      .mockResolvedValueOnce(
        jsonResponse([{ id: 1, name: "Computer Science", code: "CS" }]),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryRouter initialEntries={["/register"]}><App /></MemoryRouter>);

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Unable to load departments. Check that the API and database are running, then retry.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry loading departments" }));

    expect(await screen.findByRole("option", { name: "Computer Science" })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
