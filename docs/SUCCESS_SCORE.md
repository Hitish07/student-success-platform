# Student Success Score, risk and segments

The transparent **Student Success Score** is a weighted sum of 15 direction-aligned indicators normalized to `[0, 1]`; the published score is `100 * sum(weight × normalized indicator)`, bounded to `[0, 100]`. Weights below are the single source of truth in `backend/app/services/success_analytics.py` and sum to 1.

| Domain | Indicator and normalization | Weight |
| --- | --- | ---: |
| Academic | CGPA / 10; marks / 100; backlogs: `1 - min(backlogs / 50, 1)` | 12%, 12%, 8% |
| Attendance | Overall attendance / 100 | 12% |
| LMS | `min(logins / 50, 1)`; assignment completion / 100 | 4%, 6% |
| Engagement | `min(count / cap, 1)`: events cap 5, clubs 3, hackathons 2, certifications 3 | 2%, 2%, 3%, 3% |
| Placement | Aptitude / 100; coding / 100; mock interview / 100 | 7%, 11%, 6% |
| Skills | Technical / 100; soft skills / 100 | 7%, 5% |

Feedback is collected but excluded from this score: subjective ratings are not comparable indicators of an individual student's capability. Category scores renormalize the weights of their own indicators. Academic risk uses CGPA, marks, backlogs and attendance; placement risk uses aptitude, coding, mock interview and both skills indicators. Each risk score is the weighted average of the indicators' *inverse* readiness (`1 - normalized value`) on a 0–100 scale. For both flags: **Low** is `<35`, **Medium** is `35–<60`, **High** is `>=60`.

For the total score and each risk flag, the API compares each student's normalized indicator to the mean of the endpoint's permitted cohort. A driver's contribution is its within-score/flag normalized weight multiplied by the student's deviation from that mean, in score points. Positive and negative lists return the three largest drivers in each direction, if present. For risk flags the direction is risk burden, so a positive driver increases risk relative to peers.

Completeness is the percentage of the 15 scoring inputs that were not imputed. Scores below **70% completeness** are labeled `low confidence`; they remain visible but should not be treated as precise. The deterministic, mutually exclusive segment rules are applied in this order: (1) Placement-ready: placement score `>=75` and placement risk Low; (2) Strong academics, placement gap: academic `>=70`, placement `<60`; (3) Highly engaged, academic support needed: engagement `>=70`, academic `<60`; (4) Disengaged, elevated risk: engagement `<40` and either flag High; (5) Balanced development: all remaining students, with an action suggested from their lowest category score.

These are explainable demo heuristics, not validated predictions, diagnoses, or causal claims. Source data may be sparse or imputed; the cohort average is descriptive and can change with department scope. Engagement caps, indicator choices, weights and thresholds require institutional review before operational use. Dean results are department-scoped; principal results are institution-wide.
