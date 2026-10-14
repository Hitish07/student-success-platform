import ReactECharts from "echarts-for-react";
import "echarts-gl";

import type { ScoredStudent } from "./AnalyticsDashboard";

interface Props {
  students: ScoredStudent[];
}

export function HighRiskByDepartment3D({ students }: Props) {
  const grouped = new Map<string, { academic: number; placement: number }>();
  for (const student of students) {
    const department = student.department ?? "Unassigned";
    const totals = grouped.get(department) ?? { academic: 0, placement: 0 };
    if (student.academic_risk.level === "High") totals.academic += 1;
    if (student.placement_risk.level === "High") totals.placement += 1;
    grouped.set(department, totals);
  }
  const rows = Array.from(grouped, ([department, counts]) => ({
    department,
    ...counts,
  }));

  const departments = rows.map((row) => row.department);

  // Two y-rows: y=0 -> academic, y=1 -> placement
  const data: [number, number, number][] = [];
  rows.forEach((row, xIndex) => {
    data.push([xIndex, 0, row.academic]);
    data.push([xIndex, 1, row.placement]);
  });

  const maxCount = Math.max(
    1,
    ...rows.map((row) => Math.max(row.academic, row.placement)),
  );

  const option = {
    tooltip: {
      formatter: (params: { value: [number, number, number] }) => {
        const [xIndex, yIndex, count] = params.value;
        const series = yIndex === 0 ? "Academic risk" : "Placement risk";
        return `${departments[xIndex]}<br/>${series}: ${count} student${count === 1 ? "" : "s"}`;
      },
    },
    visualMap: {
      show: false,
      min: 0,
      max: maxCount,
      inRange: {
        color: ["#fef3c7", "#f59e0b", "#dc2626", "#7f1d1d"],
      },
    },
    xAxis3D: {
      type: "category",
      data: departments,
      name: "Department",
      nameTextStyle: { color: "#4c1d95" },
      axisLabel: { color: "#4c1d95", fontSize: 9, interval: 0 },
    },
    yAxis3D: {
      type: "category",
      data: ["Academic", "Placement"],
      name: "Risk type",
      nameTextStyle: { color: "#4c1d95" },
      axisLabel: { color: "#4c1d95", fontSize: 10 },
    },
    zAxis3D: {
      type: "value",
      name: "Students",
      nameTextStyle: { color: "#4c1d95" },
      axisLabel: { color: "#4c1d95", fontSize: 10 },
    },
    grid3D: {
      boxWidth: 100,
      boxDepth: 50,
      boxHeight: 55,
      viewControl: {
        projection: "perspective",
        autoRotate: false,
        alpha: 22,
        beta: 35,
        distance: 190,
      },
      light: {
        main: {
          intensity: 1.1,
          shadow: true,
          alpha: 30,
          beta: 30,
        },
        ambient: { intensity: 0.5 },
      },
      axisLine: { lineStyle: { color: "#fcd34d" } },
      splitLine: { lineStyle: { color: "#fef3c7" } },
    },
    series: [
      {
        type: "bar3D",
        data,
        shading: "lambert",
        barSize: 8,
        bevelSize: 0.4,
        itemStyle: { opacity: 0.95 },
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: "320px" }}
      notMerge
      lazyUpdate
    />
  );
}
