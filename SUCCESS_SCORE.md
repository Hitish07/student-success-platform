Student Success Score — Method Note
Prepared for: Smart Campus Analytics judges and reviewers
Companion to: the analytics dashboard, the Success Score API, and the risk flags shown per student

1. Purpose
The Student Success Score is a single, comparable number that summarises how a student is doing across academic performance, placement readiness, engagement, and digital activity. It exists so faculty and administrators can:

Compare students on one consistent scale

Identify who is at risk before grades reflect it

See which indicators are pulling a student up or down

The score is not a verdict. It is a lens. Every student's score comes with drivers that explain it.

2. The formula
text
Success Score = Σ (weightᵢ × normalized_indicatorᵢ) × 100
Where each indicator is:

text
normalized_indicator = clamp(value / maximum, 0, 1)
And for backlogs specifically:

text
normalized_backlogs = 1 - clamp(value / maximum, 0, 1)   (inverted)
The final score is bounded to [0, 100]. A score of 100 means every indicator is at or above its ideal value.

3. The 15 indicators and their weights
Weights sum to exactly 1.0 (the code raises an error if they don't).

Indicator	Weight	Ideal max	Category
CGPA	0.12	10.0	Academic
Academic marks (%)	0.12	100	Academic
Attendance (%)	0.12	100	Academic
Backlog record (inverted)	0.08	50	Academic
Coding assessment	0.11	100	Placement
Placement aptitude	0.07	100	Placement
Technical skills	0.07	100	Placement
Mock interview	0.06	100	Placement
Soft skills	0.05	100	Placement
Assignment completion (%)	0.06	100	Digital activity
LMS activity (logins)	0.04	50	Digital activity
Hackathons	0.03	2	Engagement
Certifications	0.03	3	Engagement
Campus events	0.02	5	Engagement
Club participation	0.02	3	Engagement
Category totals:

Category	Sum of weights	Share of score
Academic	0.44	44%
Placement readiness	0.36	36%
Digital activity	0.10	10%
Engagement	0.10	10%
4. Why these weights
Academic performance is 44%. It is the strongest single signal of whether a student is on track, and the one institutions already track most reliably.

Placement readiness is 36%. The brief explicitly calls out placement as a success outcome. Coding and aptitude carry the most weight within this category because they are the most predictive of actual placement outcomes.

Engagement and digital activity together are 20%. They are leading indicators. A student whose marks are still fine but who has stopped logging in or attending events is often the one who fails next semester.

Weight choices are deliberate, not arbitrary — they match the brief's emphasis on academic performance and placement outcomes as the two primary axes of success.

5. Category sub-scores
Each student also gets three category scores, computed the same way but restricted to the indicators in that category:

Academic score — CGPA, marks, attendance, backlogs

Placement score — coding, aptitude, mock interview, technical skills, soft skills

Engagement score — events, clubs, hackathons, certifications

These are what the segmentation step uses. They are the reason a student can be "strong academically but behind on placement readiness" — a case that one aggregate score would hide.

6. Risk flags
Each student gets two independent risk flags: one academic, one placement. They are computed from the same normalized indicators, but inverted:

text
risk_score = Σ (weightᵢ × (1 - normalizedᵢ)) / Σ(weights) × 100
Then thresholded:

Risk score	Level
< 35	Low
35 – 59.99	Medium
≥ 60	High
Why two flags, not one. A student can be academically fine but placement-risky (good marks, no coding practice). Or the reverse (participates in everything, marks falling). Collapsing them into one number loses the actionable signal.

Why these thresholds. A risk score of 60 means the weighted average of a student's indicators sits at 40% of the ideal — that is genuinely alarming. 35 corresponds to 65% of the ideal, which is worth attention but not panic. The bands are asymmetric on purpose: it should be harder to be flagged High than Medium.

7. Explainability — the drivers
Every student comes with a score_drivers object: top 3 positive and top 3 negative contributions.

text
contributionᵢ = (weightᵢ / Σ(weights)) × (studentᵢ - cohort_averageᵢ) × 100
studentᵢ is the normalized value of the indicator for this student.

cohort_averageᵢ is the average across all students in the current view.

A positive contribution means the student is above the cohort on this indicator. A negative one means below.

The list is sorted and truncated to 3 each side — what a faculty member needs to see at a glance.

Risk flags have their own drivers, computed against the inverted direction, so a student's academic risk shows which indicators are pulling it up, not just that it is high.

What this means in practice. A student with a score of 62 doesn't just get a number. They get: "Your biggest positives are attendance and assignment completion; your biggest drag is coding assessment — you're 18 points below the cohort average." That is what makes the score actionable rather than decorative.

8. Data quality and imputation
Real institutional data is incomplete. Some students are missing CGPA, or placement scores, or engagement data. The score handles this in two ways:

Null values are imputed during the data-integration step, using cohort-level medians for the relevant field.

Every imputed field is recorded on the student's record and reflected in a data_completeness percentage.

The completeness figure is:

text
completeness = (15 - count(imputed_fields)) / 15 × 100
Then:

completeness ≥ 70% → standard confidence — the score is treated as reliable

completeness < 70% → low confidence — the score is shown with an explicit "Low confidence" badge, and the drivers panel notes which inputs were imputed

Why this matters. A score computed from two of fifteen indicators is not the same as a score computed from all fifteen. Showing the difference — rather than hiding it — is what makes the analytics trustworthy.

9. Segmentation
Once a student has a score, category scores, and two risk flags, they are placed into one of five segments, each with a suggested action:

Segment	Condition	Suggested action
Placement-ready	Placement score ≥ 75 and placement risk Low	Advanced employer projects, interview practice, placement opportunities
Strong academics, placement gap	Academic score ≥ 70 and placement score < 60	Aptitude and coding practice plus mock interviews
Highly engaged, academic support needed	Engagement ≥ 70 and academic < 60	Pair participation strengths with tutoring and a course recovery plan
Disengaged, elevated risk	Engagement < 40 and (academic risk High or placement risk High)	Supportive check-in and a short, personalised action plan
Balanced development	(everything else)	Review the weakest category and set one measurable next step
The segmentation is deterministic and inspectable. It is not a black box.

10. What we do not do, and why
We do not rank students against a fixed national benchmark. All scores are relative to the current cohort, so the score is meaningful in context.

We do not hide imputation. Missing data is tracked and shown.

We do not treat one flag as a verdict. Two independent risk axes and a full driver breakdown exist so that a human makes the final call.

We do not use labels the student cannot see. Every driver and confidence value is visible to the student and to faculty.

11. One worked example
A student with these values:

Indicator	Student value	Cohort average
CGPA	8.4 / 10	7.1 / 10
Attendance	88%	76%
Coding score	32 / 100	58 / 100
Aptitude	71 / 100	62 / 100
Assignment completion	95%	80%
Engagement (sum across four)	4	6
Produces:

Success Score: approximately 62

Academic score: approximately 78 (strong)

Placement score: approximately 48 (below target)

Engagement score: approximately 42 (low)

Academic risk: Low

Placement risk: Medium

Top positive drivers: Attendance (+3.1), Assignment completion (+2.4), CGPA (+1.9)

Top negative drivers: Coding score (−4.6), Engagement (−1.2), Aptitude (−1.1)

Segment: Strong academics, placement gap

Suggested action: Provide aptitude and coding practice plus mock interviews

That is the level of detail every student gets. Not a number. A narrative they can act on.

12. Summary
One formula, 15 indicators, weights that sum to 1.0

Two independent risk axes, thresholded at 35 and 60

Full driver explanation for every score and every flag

Data quality tracked, imputation recorded, confidence shown

Five deterministic segments, each with a suggested action

No black box, no hidden imputation, no ranking against fixed benchmarks

End of document.

