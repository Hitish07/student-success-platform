import ReactECharts from "echarts-for-react";
import "echarts-gl";

import type { ScoredStudent } from "./AnalyticsDashboard";

interface Props {
  students: ScoredStudent[];
}

export function SuccessScoreDistribution3D({ students }: Props) {
  // 10 buckets of 10 points each
  const buckets = Array.from({ length: 10 }, (_, index) => {
    const lower = index * 10;
    const count = students.filter(
      (student) =>
        student.success_score >= lower
        && student.success_score < (index === 9 ? 101 : lower + 10),
    ).length;
    return { range: `${lower}-${lower + 9}`, count };
  });

  const data: [number, number, number][] = buckets.map((bucket, index) => [
    index,
    0,
    bucket.count,
  ]);

  const maxCount = Math.max(1, ...buckets.map((bucket) => bucket.count));

  const option = {
    tooltip: {
      formatter: (params: { value: [number, number, number] }) => {
        const [xIndex, , count] = params.value;
        return `${buckets[xIndex].range}<br/>${count} students`;
      },
    },
    visualMap: {
      show: false,
      min: 0,
      max: maxCount,
      inRange: {
        color: ["#ddd6fe", "#a78bfa", "#7c3aed", "#5b21b6"],
      },
    },
    xAxis3D: {
      type: "category",
      data: buckets.map((bucket) => bucket.range),
      name: "Score range",
      nameTextStyle: { color: "#4c1d95" },
      axisLabel: { color: "#4c1d95", fontSize: 10 },
    },
    yAxis3D: {
      type: "category",
      data: [""],
      show: false,
    },
    zAxis3D: {
      type: "value",
      name: "Students",
      nameTextStyle: { color: "#4c1d95" },
      axisLabel: { color: "#4c1d95", fontSize: 10 },
    },
    grid3D: {
      boxWidth: 100,
      boxDepth: 40,
      boxHeight: 60,
      viewControl: {
        projection: "perspective",
        autoRotate: false,
        alpha: 20,
        beta: 40,
        distance: 180,
      },
      light: {
        main: {
          intensity: 1.2,
          shadow: true,
          alpha: 30,
          beta: 30,
        },
        ambient: { intensity: 0.4 },
      },
      axisLine: { lineStyle: { color: "#c4b5fd" } },
      splitLine: { lineStyle: { color: "#ede9fe" } },
    },
    series: [
      {
        type: "bar3D",
        data,
        shading: "lambert",
        barSize: 8,
        bevelSize: 0.4,
        itemStyle: {
          opacity: 0.95,
        },
        emphasis: {
          itemStyle: {
            color: "#ec4899",
          },
        },
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
