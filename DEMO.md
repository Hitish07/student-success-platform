Smart Campus Analytics — Live Demo Script
A click-through runbook for a 5-minute live demo. Follow it top to bottom.
Target total time: 4 minutes 30 seconds.

Pre-flight (do this 10 minutes before)
Both servers running

Terminal 1:

powershell
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload
Terminal 2:

powershell
cd frontend
npm run dev
Open two browser windows, side by side

Window A: student session

Window B: faculty session

Third tab for principal, ready to switch.

Pre-open three things in a spare tab so nothing waits on a slow load:

One assignment page (student)

One doubts page (student)

Student 360 for a student who has data (faculty)

Zoom in one level (Ctrl and + in the browser) so the projector sees everything.

0:00 — Opening line (30 seconds)
Say this before you click anything:

"Colleges already generate enormous amounts of student data — attendance, marks, LMS activity, placement scores, feedback. What they don't have is a way to turn that data into action. By the time a student fails, the signals were visible six weeks earlier. Our platform closes that gap: one Success Score, two risk flags, and a recommended next step for every student. We'll show you five things in the next five minutes."

Do not touch the keyboard during this. Talk to the room, not the screen.

0:30 — Student view: assignment integrity (60 seconds)
Window A, logged in as a student, on the Assignments page.

Click: Open on any open assignment.

Say: "Students write answers here. Notice two things — paste is disabled, and above the box it says 'Tab switches: 0 of 3 allowed.'"

Do: Try to paste into the textarea. It refuses with a message.

Do: Switch to another browser tab for a second, come back. The counter increments.

Say: "Every switch is counted on the server, not in the browser. If a student switches tabs four times, the attempt is voided — the answer is cleared and they have to write it again. This catches casual copy-paste and tab-hopping, and it gives faculty visibility into who is trying to cheat."

Skip actually voiding the attempt live — it takes too long. Just describe it.

1:30 — Student view: AI doubts agent (60 seconds)
Window A — switch to the Doubts tab.

Say: "This is our AI doubts agent. Students ask a question about a technical problem, and the assistant explains the logic — never the answer."

Do: Pick a subject from the dropdown.

Do: Type a real question, for example:

How do I think about reversing a linked list?

Click: Ask.

Wait 3–5 seconds.

Say: "Behind the scenes, this calls Gemini. Two rules are enforced — the system prompt tells it not to give code or a final answer, and the server also scans the reply and retries if it detects any code block. Every question is stored with the subject, so faculty can see what the class is confused about."

Point at the answer as it appears. Let the judge read the first line — it's usually a plain-English analogy, which sells the concept in one glance.

Point at the line beneath the box: "Your faculty can see the topics you ask about, not your name."

2:30 — Faculty view: Student 360 (60 seconds)
Window B, logged in as faculty. Click Student support or Submissions, then click any student's name.

Say: "This is Student 360. One page per student — a faculty member sees their journey, their risk, their attendance, marks, recent doubts, and recent submissions. The faculty member only sees students in subjects they teach; anyone outside their roster returns a 404, not a 403, so the record itself isn't confirmed to exist."

Point at, in order:

The header (name, department, year)

The four headline cards — Risk level, Attendance, Marks, Pending assignments

The journey timeline — recent events

Recent doubts — subjects and dates, no question text

Recent submissions — with tab-switch counts

Say: "Everything on this page comes from data the faculty member could already see in three different screens. Student 360 just puts it in one place."

3:30 — Faculty view: doubts summary (30 seconds)
Window B — click the Doubts tab in the faculty nav.

Say: "Faculty also see a summary of every topic students are asking about. Subjects are grouped, counts are shown, and the recent questions appear underneath — but no student name is ever attached. The promise we made to the student on the previous screen is kept."

Point at: the topic cards, the counts, the anonymous question list.

4:00 — Principal view: trends and AI briefing (60 seconds)
Switch to the principal tab. Click Institution trends in the nav (it's the fifth tab and only visible to the principal role).

Say: "Finally, the principal's view. This is the only role that sees the whole institution. Same underlying data, different lens."

Point at, in order:

The AI briefing paragraph at the top — "This is written live by Gemini from the current numbers. It reads the trends and summarises the institution in ten seconds."

The four headline cards

Academic improvement over time — "One line per department, six months of average marks."

Placements over time — "Real placement data recorded by faculty, aggregated institution-wide."

Say: "The formula behind every score and flag is documented in a method note in the repo — weights, thresholds, and how drivers are computed. Nothing here is a black box."

5:00 — Close (20 seconds)
Stop clicking. Turn to the room.

Say:

"Five features. One platform. Every score has a driver, every risk has a next step, and every claim is covered by a test. 105 tests, all passing. The Student Success Score is documented in one file, and the deck is in the repo. Happy to take questions."

Stop talking. Let them ask.

Recovery paths if something breaks live
Symptom	What to say	What to do
Gemini is slow	"The free tier is busy right now — the retry loop tries three models."	Wait 5 more seconds, then move on. Don't apologise twice.
Backend 500	"That endpoint is one we changed recently."	Switch to the next screen. Don't debug.
Page won't load	"While that loads, let me show you the next view."	Open a pre-loaded tab.
Login fails	"Session expired — give me one second."	Re-login. If it fails twice, move to the next role.
Nothing works	"Let me show you the architecture slide instead."	Switch to SLIDES.md slide 4. Talk through the screenshots.
The one rule if something breaks: never debug in front of a judge. Say one sentence, move on.

Post-demo — questions you should expect
"How is the Success Score computed?"
→ "Fifteen indicators, four categories, weights that sum to 1.0. Academic is 44%, placement 36%, engagement and digital activity 10% each. Full details in SUCCESS_SCORE.md."

"Is the AI actually AI, or is it faked?"
→ "Real Gemini calls. Same client handles retries and model fallback. The doubts feature works against the live API."

"What about privacy?"
→ "Three role-scoped routers. Faculty see only their own students. The doubts summary is anonymous. Secrets live in .env, never in the browser."

"What's the biggest thing you'd add next?"
→ "Intervention effectiveness — snapshot a student's metrics at the moment of an intervention, then compare 30 days later. That turns 'we intervened' into 'here's whether it worked.'"

"What didn't you build that you wanted to?"
→ "A code editor with execution for technical subjects. The editor is straightforward; the sandboxing is not. We scoped it out to keep the security surface small."

Timing checklist
□ 0:00 opening — 30s
□ 0:30 student assignment — 60s
□ 1:30 student doubts — 60s
□ 2:30 faculty Student 360 — 60s
□ 3:30 faculty doubts — 30s
□ 4:00 principal trends — 60s
□ 5:00 close — 20s
Total: 5 minutes 20 seconds. If you run over, cut the faculty doubts section (30s) and shorten the principal trends to just the AI briefing paragraph (30s saved).

End of demo script.

