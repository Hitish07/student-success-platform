Smart Campus Analytics — Pitch Deck
6 slides. Total talk time: ~5 minutes plus a live demo.
Speaker notes are in italics beneath each slide.

Slide 1 — The problem
Colleges know that students struggle. They rarely know why, or what to do next.

Data lives in disconnected systems: attendance in one, marks in another, placement in a third, LMS in a fourth

By the time a student fails a semester, the signals were visible 6–8 weeks earlier

Faculty see 40+ students per class. Nobody can spot every quiet decline by eye

Administrators see aggregate charts, not the students behind them

The gap we close: turn scattered student data into one score, one risk flag, one recommended action — before the semester ends.

Speaker note: Open with the second bullet — the 6-to-8-week lead time. It's the fact that makes everything else matter. Most institutions only act on grades. Grades are the last signal, not the first.

Slide 2 — Data integration
Eight source systems, one unified student view.

Source	Indicators
Academic	CGPA, marks, backlogs, subject performance
Attendance	Overall %, subject-wise
LMS	Login frequency, assignment completion
Engagement	Events, clubs, hackathons, certifications
Placement	Aptitude, coding, mock interviews
Skills	Technical and soft-skill assessments
Feedback	Student satisfaction, faculty feedback
Source records	Raw ingested rows from each system
How they come together

Every source is loaded into a staging table with its raw external ID

Records are cleaned: nulls imputed from cohort medians, duplicates removed, out-of-range values flagged

External IDs are matched to canonical student records through a resolution step that handles whitespace and case variations

Every cleaning action is logged and shown on the Data Quality tab, including a before/after example for one real row

Speaker note: The data-quality tab is the demo hero for this slide. It shows the raw value, the cleaned value, and the count of records that were deduped, matched, or imputed. A judge who asks "did they actually do integration or just mock it?" gets an immediate, verifiable answer.

Slide 3 — The Student Success Score
One number per student. Fifteen indicators. Weights that sum to 1.0.

text
Success Score = Σ (weightᵢ × normalized_indicatorᵢ) × 100
The four categories

Category	Weight	What's in it
Academic	44%	CGPA, marks, attendance, backlogs
Placement readiness	36%	Coding, aptitude, mock interview, technical skills, soft skills
Digital activity	10%	LMS logins, assignment completion
Engagement	10%	Events, clubs, hackathons, certifications
Two independent risk flags — academic risk and placement risk — computed from the same indicators, inverted, then thresholded:

Low: risk score < 35

Medium: 35 to 59.99

High: ≥ 60

Every score explains itself. Each student gets top-3 positive and top-3 negative drivers, computed as the student's deviation from the cohort average on each indicator.

Speaker note: The point of this slide is not the numbers. It's that the numbers are inspectable. Weights are stated. Thresholds are stated. The formula is stated. A judge who wants to argue with our choices can argue with specific numbers, not with a black box.

Slide 4 — The dashboard
Three roles. Each sees what they need, and nothing they don't.

Faculty

Assigned courses, rosters, at-risk students, alerts

Submissions view with tab-switch counts per student

Student 360 — one page per student: journey, risk, attendance, marks, doubts, submissions

Doubts summary — what their class is confused about, anonymously

Placements — record and track placement outcomes for their students

Administrators (dean, principal)

Success Score distribution and risk counts

High-risk students by department

Student segments with a suggested action per segment

Explainable drivers — click any student to see what's pulling their score up or down

Institution trends — academic and placement trajectories, with an AI-written briefing

Students

Their own success score and category breakdown

Journey timeline: enrolments, attendance, assessments, feedback

Assignments with integrity checks

Ask a doubt — an AI helper that explains the logic and refuses to give the answer

Speaker note: The point is that the same underlying data serves three different needs. A student sees themselves. A teacher sees their class. A principal sees the institution. Same sources, three lenses.

Slide 5 — Live demo
What we'll show, in order

Student view — open an assignment. Paste is blocked. Tab switches are counted server-side. On the 4th switch, the attempt is voided and a fresh one starts.

Student view — ask a doubt. Watch the AI explain the logic, refuse code, offer multiple approaches.

Faculty view — open Student 360 for one student. See journey, risk, attendance, marks, doubts, submissions.

Faculty view — open the Doubts tab. See topics grouped across the class, anonymous.

Faculty view — record a placement.

Principal view — open the Institution Trends tab. See the AI briefing, the academic trajectory by department, and the placement trend.

Speaker note: Do not narrate every click. Say one sentence per screen: what it is, why it matters. Judges remember the flow, not the details. If something breaks live, say "we have a test for that" and move on — don't debug in front of them.

Slide 6 — Bonus, and why this is different
Two bonus items, both shipped

Student segmentation
Five meaningful groups, each with a suggested action:

Placement-ready

Strong academics, placement gap

Highly engaged, academic support needed

Disengaged, elevated risk

Balanced development

Deterministic rules, not a black box. Faculty can see exactly why a student landed in a segment.

Explainable score
Every score and every risk flag comes with its top positive and negative drivers. A student with a score of 62 sees "attendance is your biggest strength; coding assessment is your biggest drag — you're 18 points below the cohort average."

The one-sentence pitch
Colleges already have the data. What they don't have is a way to turn it into action. This platform does — with a score, a risk flag, and a next step for every student.

Speaker note: Close on the one-sentence pitch, then stop talking. Let the demo speak. Answer questions but do not add new features in the answer — say "that's a natural next step" if someone asks for something you haven't built.

Appendix — Rubric mapping
Optional. Include if a judge asks "which criterion does this address?"

Criterion	Where in the demo
Data Integration & Analysis (30%)	Slide 2, Data Quality tab in the demo
Success Score & Risk Identification (25%)	Slide 3, Student 360 page, at-risk lists
Dashboard & Visualization (25%)	Slide 4, Student 360, Institution Trends tab
Problem Understanding (10%)	Slide 1, and the AI doubts agent's "no answer" rule
Presentation & Demo (10%)	The demo itself, this deck
Bonus: Segmentation	Slide 6, the Segments tab
Bonus: Explainable Score	Slide 6, the driver charts in Student 360
Rehearsal checklist
□ Both servers running (backend on :8000, frontend on :5173)
□ Logged in as student, faculty, and principal ahead of time
□ One assignment pre-opened so the paste-block demo starts instantly
□ One doubt already asked so the answer shows without waiting on Gemini
□ Student 360 preloaded with a real student who has data
□ Institution Trends tab opens with a populated AI summary
□ Browser zoom set so text is readable on a projector
□ Total rehearsal time under 5 minutes
End of deck.

