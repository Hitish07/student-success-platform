import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

function tokenResponse(role: "student" | "faculty" | "dean" | "principal") {
  return {
    access_token: "demo-access-token",
    refresh_token: "rotated-refresh-token",
    expires_in: 900,
    user: {
      id: 7,
      email: `demo.${role}@example.invalid`,
      full_name: `Demo ${role}`,
      role,
      department_id: 1,
    },
  };
}

function responseFor(url: string) {
  if (url.endsWith("/auth/refresh")) {
    return tokenResponse("student");
  }
  if (url.endsWith("/student/dashboard")) {
    return {
      attendance_percentage: 80,
      marks_percentage: 75,
      enrolled_courses: 0,
      courses: [],
      risk: null,
    };
  }
  return {};
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("role-protected portals", () => {
  it("redirects a signed-in user away from a portal for another role", async () => {
    sessionStorage.setItem("student-success.refresh-token", "stored-refresh-token");
    const fetchMock = vi.fn().mockImplementation((url: string) =>
      Promise.resolve(new Response(JSON.stringify(responseFor(url)), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/faculty"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Your student journey" }),
    ).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Student portal" })).toBeTruthy();
    expect(await screen.findByText(/dashboard is ready/i)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/auth/refresh",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("requires sign-in for protected routes", async () => {
    render(
      <MemoryRouter initialEntries={["/principal"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });
});
