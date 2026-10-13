import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

describe("foundation page", () => {
  it("shows the welcome message and demo-data notice", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Every student journey matters." }),
    ).toBeTruthy();
    expect(screen.getByText(/fictional and for demonstration only/i)).toBeTruthy();
  });
});
