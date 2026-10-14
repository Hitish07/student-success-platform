# Placement and Interview Preparation

*Audience: students preparing for internships and placement interviews.*
*Format: 6 slides. Total talk time: ~8 minutes.*

---

## Slide 1 — What companies actually test

**Interviews are not exams. They test different things.**

- **Problem-solving under uncertainty** — can you think out loud when you don't immediately know the answer?
- **Communication** — can you explain your reasoning to someone who isn't inside your head?
- **Fundamentals** — not everything you learned. The 20% that shows up again and again.
- **Fit and motivation** — do you actually want this role, and can you say why?

*Speaker note: Open by breaking the assumption that interviews are about "knowing more." They are about reasoning clearly and communicating it. That reframing is the most valuable thing in this deck.*

---

## Slide 2 — The 20% that gets asked

**Across technical subjects, the same topics repeat**

**Computer Science**
- Arrays and strings (traversal, two-pointer, sliding window)
- Hash maps (counting, deduplication)
- Sorting and searching (binary search especially)
- Time and space complexity (Big-O, at a working level)
- Trees and graphs (BFS, DFS, at least conceptually)

**Non-technical**
- **Case questions** — "How would you improve X for company Y?"
- **Guesstimates** — "How many X are sold in India each year?"
- **Behavioural** — "Tell me about a time you disagreed with someone."
- **Domain fundamentals** — a business student should be able to read a P&L statement; a marketing student should know the difference between reach and engagement.

*Speaker note: Name the specific topics. Students remember lists. Say the list slowly and tell them to write it down.*

---

## Slide 3 — A worked interview problem

**"Reverse a string without using the built-in reverse."**

**What a good answer sounds like, out loud:**
1. *"Let me restate to confirm: I get a string, I return a new string with the characters in reverse order. No built-in reverse function."*
2. *"Two approaches come to mind. The simplest is to build a new string by walking the original from the end. That's O(n) time, O(n) space."*
3. *"A second option is to swap characters in place using two pointers — one at each end. That's also O(n) time but O(1) extra space if I'm allowed to mutate."*
4. *"Let me write the second one. I'll use i from the start and j from the end, swap, move both inward, stop when they meet."*

**Why this works:** you restate, propose two approaches, name the tradeoff, then write. That's the pattern.

*Speaker note: The point is not the string reversal. The point is the shape of the answer — restate, propose, compare, code. Practise that shape with any problem and it becomes automatic.*

---

## Slide 4 — Three mistakes that cost offers

**1. Silent problem-solving**
If you're thinking, the interviewer doesn't know it. Narrate. Even "I'm considering a hash map here" is better than silence.

**2. Jumping to code**
Interviewers want to see how you think. Talk through the approach before you write a line. Ten seconds of framing beats ten minutes of debugging.

**3. Defending a wrong answer**
If you notice a bug, say so. "Actually, this breaks on an empty string — let me fix that." Catching your own error is a strength, not a weakness. Interviewers hire people who correct themselves.

*Speaker note: The third one is the hardest to internalise. Students are trained to avoid mistakes. In an interview, gracefully handling a mistake is worth more than never making one.*

---

## Slide 5 — Preparation plan

**Four weeks before placements**

- **Week 1 — Fundamentals.** Re-read the core notes from your 3 most relevant subjects. Write one-page summaries.
- **Week 2 — Practice problems.** 2 problems a day, timed. Focus on arrays, strings, hash maps.
- **Week 3 — Mock interviews.** With a friend, out loud, on camera if possible. Review the recording.
- **Week 4 — Company research.** For each company you're interviewing with: what they do, what they hire for, what their recent news is.

**The week before**
- Re-read your resume and be ready to talk about every line
- Prepare 3 stories: a challenge you overcame, a time you worked in a team, something you're proud of
- Sleep. Interview performance drops sharply with fatigue.

*Speaker note: The four-week plan is deliberately simple. Students over-plan interview prep and then don't do it. Four weeks of 30-minute sessions beats one week of all-nighters.*

---

## Slide 6 — What to remember

**Three sentences**

1. **Interviews test reasoning and communication, not trivia. Think out loud.**
2. **Prepare the 20% that gets asked — arrays, strings, hash maps, behavioural stories.**
3. **A mistake you notice and fix is worth more than a smooth answer that turns out wrong.**

**What comes next**
- After every interview, write down the questions you were asked and how you answered them.
- If you didn't get the offer, ask for feedback. Not every company gives it, but the ones that do are worth more than the ones that don't.
- Rejection from one company is not data about you. It's data about that one interview on that one day.

*Speaker note: End with the "rejection is not data about you" line. It's the sentence students carry with them into their next interview.*
