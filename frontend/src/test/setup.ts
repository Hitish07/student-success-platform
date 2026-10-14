

import { vi } from "vitest";

// ECharts + echarts-gl need a real canvas. In jsdom we replace the whole
// chart with a lightweight placeholder so tests do not emit canvas errors.
vi.mock("echarts-for-react", () => ({
  default: () => null,
}));

vi.mock("echarts-gl", () => ({}));
