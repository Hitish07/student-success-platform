import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";

const demoStudent = {
  student_id: 15,
  student_name: "Avery Demo",
  department: "Computer Science",
  cohort: "Fall 2026",
  success_score: 76.5,
  academic_score: 82,
  placement_score: 54,
  engagement_score: 67,
  academic_risk: {
    level: "Low",
    risk_score: 18,
    drivers: {
      positive: [{ indicator: "CGPA", student_value: 80, cohort_average: 70, contribution: 4 }],
      negative: [],
    },
  },
  placement_risk: {
    level: "Medium",
    risk_score: 43,
    drivers: {
      positive: [{ indicator: "Coding assessment", student_value: 30, cohort_average: 70, contribution: 6 }],
      negative: [],
    },
  },
  score_drivers: {
    positive: [{ indicator: "CGPA", student_value: 80, cohort_average: 70, contribution: 2 }],
    negative: [{ indicator: "Coding assessment", student_value: 30, cohort_average: 70, contribution: -4 }],
  },
  data_completeness: 93.33,
  confidence: "standard",
  imputed_fields: ["feedback_rating"],
};

const integration = {
  students: [{
    student_id: 15,
    student_name: "Avery Demo",
    department: "Computer Science",
    cohort: "Fall 2026",
    cgpa: 8.4,
    attendance_percentage: 72,
    lms_logins: 30,
    source_coverage: ["academic", "attendance"],
    imputed_fields: ["feedback_rating"],
  }],
  quality_report: {
    rows_ingested: 30,
    rows_cleaned: 25,
    nulls_imputed: 12,
    duplicates_removed: 3,
    out_of_range_values: 2,
    unresolved_rows: 1,
    invalid_rows: 0,
    source_rows: { academic: 8, attendance: 8, lms: 4 },
    cleaned_source_rows: { academic: 7, attendance: 7, lms: 4 },
    before_after_example: {
      source: "academic",
      external_student_id: " student_15 ",
      canonical_student_id: 15,
      before: { cgpa: 8.4, marks_percentage: 130 },
      after: { cgpa: 8.4, marks_percentage: null },
    },
  },
};

const segment = {
  student_id: 15,
  student_name: "Avery Demo",
  department: "Computer Science",
  cohort: "Fall 2026",
  segment: "Strong academics, placement gap",
  suggested_action: "Provide coding practice and mock interviews.",
};

const principalDashboard = {
  total_students: 120,
  average_attendance: 78.5,
  average_marks: 68.2,
  academic_trend: {
    institution: [
      { label: "2026-05", value: 65.0 },
      { label: "2026-06", value: 68.0 },
      { label: "2026-07", value: 72.0 },
      { label: "2026-08", value: 70.0 },
      { label: "2026-09", value: 73.0 },
      { label: "2026-10", value: 75.0 },
    ],
    by_department: [
      {
        name: "Computer Science",
        points: [
          { label: "2026-05", value: 70.0 },
          { label: "2026-06", value: 72.0 },
          { label: "2026-07", value: 76.0 },
          { label: "2026-08", value: 77.0 },
          { label: "2026-09", value: 79.0 },
          { label: "2026-10", value: 81.0 },
        ],
      },
      {
        name: "Mechanical",
        points: [
          { label: "2026-05", value: 60.0 },
          { label: "2026-06", value: 62.0 },
          { label: "2026-07", value: 64.0 },
          { label: "2026-08", value: 61.0 },
          { label: "2026-09", value: 63.0 },
          { label: "2026-10", value: 62.0 },
        ],
      },
    ],
    overall_average: 71.4,
  },
  placement_readiness: {
    points: [
      { label: "2026-05", value: 0.0 },
      { label: "2026-06", value: 0.0 },
      { label: "2026-07", value: 0.0 },
      { label: "2026-08", value: 0.0 },
      { label: "2026-09", value: 0.0 },
      { label: "2026-10", value: 71.0 },
    ],
    overall_average: 71.0,
    note: "Average of aptitude, coding, and mock interview scores.",
  },
  ai_summary: "Computer Science leads the campus with a rising average, while Mechanical has slipped slightly over the last quarter.",
};

function mockApi(options: { loginRole?: "dean" | "principal"; failScores?: boolean } = {}) {
  const role = options.loginRole ?? "dean";
  const user = {
    id: role === "dean" ? 40 : 50,
    email: role === "dean" ? "dean.cs@demo.invalid" : "principal@demo.invalid",
    full_name: role === "dean" ? "Dean Demo" : "Principal Demo",
    role,
    department_id: role === "dean" ? 1 : null,
  };
  const tokenResponse = {
    access_token: "access-demo",
    refresh_token: "refresh-demo",
    expires_in: 900,
    user,
  };
  sessionStorage.setItem("student-success.refresh-token", "stored-refresh");
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    let status = 200;
    let body: unknown = {};
    if (url.endsWith("/auth/refresh") || url.endsWith("/auth/login")) {
      body = tokenResponse;
    } else if (url.endsWith("/analytics/success-scores")) {
      if (options.failScores) {
        status = 503;
        body = { detail: "Analytics service unavailable." };
      } else {
        body = { students: [demoStudent] };
      }
    } else if (url.endsWith("/analytics/segments")) {
      body = { students: [segment], segment_counts: { [segment.segment]: 1 } };
    } else if (url.endsWith("/analytics/data-integration")) {
      body = integration;
    } else if (url.endsWith("/principal/dashboard")) {
      body = principalDashboard;
    }
    return Promise.resolve(new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("dean and principal analytics dashboard", () => {
  it.each([
    ["dean", "Try Dean demo", "Department success dashboard", "Your department"],
    ["principal", "Try Principal demo", "Campus success dashboard", "All departments"],
  ])("loads the seeded %s dashboard", async (role, demoButton, title, scope) => {
    const fetchMock = mockApi({ loginRole: role as "dean" | "principal" });
    sessionStorage.clear();
    render(<MemoryRouter initialEntries={["/login"]}><App /></MemoryRouter>);

    fireEvent.click(await screen.findByRole("button", { name: demoButton }));
    expect(fetchMock).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
    expect(await screen.findByRole("heading", { name: title })).toBeTruthy();
    expect(await screen.findByText("Success Score distribution")).toBeTruthy();
    expect(screen.getByText(scope)).toBeTruthy();
    expect(screen.getByText("76.5")).toBeTruthy();
    expect(screen.getByText("High academic risk")).toBeTruthy();
  });

  it("filters by segment and opens a student drill-down", async () => {
    mockApi();
    render(<MemoryRouter initialEntries={["/dean"]}><App /></MemoryRouter>);

    await screen.findByRole("heading", { name: "Department success dashboard" });
    await screen.findByText("Success Score distribution");
    fireEvent.click(screen.getByRole("button", { name: "Segments" }));
    fireEvent.click(screen.getByRole("button", { name: /Strong academics, placement gap/ }));
    expect(await screen.findByText(/1 of 1 students/)).toBeTruthy();
    fireEvent.click(screen.getByText("Avery Demo"));
    expect(await screen.findByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Positive score drivers")).toBeTruthy();
    expect(within(screen.getByRole("dialog")).getByText(/Strong academics, placement gap/)).toBeTruthy();
  });

  it("shows scoped source quality counts and a before/after example", async () => {
    mockApi({ loginRole: "principal" });
    render(<MemoryRouter initialEntries={["/principal"]}><App /></MemoryRouter>);

    await screen.findByRole("heading", { name: "Campus success dashboard" });
    fireEvent.click(screen.getByRole("button", { name: "Data quality" }));
    expect(await screen.findByText("Duplicates removed")).toBeTruthy();
    expect(screen.getByText("student_15")).toBeTruthy();
    expect(screen.getByText("Before cleaning")).toBeTruthy();
    expect(screen.getByText("After cleaning")).toBeTruthy();
  });

  it("shows a retryable error when an analytics endpoint fails", async () => {
    mockApi({ failScores: true });
    render(<MemoryRouter initialEntries={["/dean"]}><App /></MemoryRouter>);

    expect(await screen.findByText("Analytics service unavailable.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });

  it("shows the AI briefing and headline numbers on the principal trends tab", async () => {
    mockApi({ loginRole: "principal" });
    render(<MemoryRouter initialEntries={["/principal"]}><App /></MemoryRouter>);

    await screen.findByRole("heading", { name: "Campus success dashboard" });
    fireEvent.click(screen.getByRole("button", { name: "Institution trends" }));

    expect(await screen.findByText(/Computer Science leads the campus/)).toBeTruthy();
    expect(screen.getByText("Total students")).toBeTruthy();
    expect(screen.getByText("120")).toBeTruthy();
    expect(screen.getByText("Average attendance")).toBeTruthy();
    expect(screen.getByText("78.5")).toBeTruthy();
    expect(screen.getByText("Average marks")).toBeTruthy();
    expect(screen.getByText("68.2")).toBeTruthy();
    expect(screen.getAllByText("Placement readiness").length).toBeGreaterThan(0);
    expect(screen.getByText("71.0")).toBeTruthy();
  });

});
