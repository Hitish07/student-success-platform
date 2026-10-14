"""Gemini client for the student doubts agent.

Returns plain-English logic explanations and multiple approaches.
Never returns final code or a complete answer: the system instruction
forbids it, and the caller (doubts service) also rejects code blocks.
"""

import socket

# Force IPv4 for outbound connections in this process. On some networks the
# IPv6 route to Google's API is unreachable but resolution still prefers AAAA
# records, which makes the client hang until timeout. Pruning AAAA answers
# makes httpx fall through to the working IPv4 addresses immediately.
_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_only_getaddrinfo

import httpx

from app.core.config import settings


MODEL_FALLBACKS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash")
ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
REQUEST_TIMEOUT_SECONDS = 30.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS_PER_MODEL = 2

SYSTEM_INSTRUCTION = (
    "You are a study helper for students. Your job is to explain the LOGIC of a "
    "problem in plain English and to suggest two or three different approaches "
    "to think about it.\n\n"
    "Hard rules, no exceptions:\n"
    "1. Never output final code, code snippets, or a complete worked solution.\n"
    "2. Never output anything inside triple-backtick fences.\n"
    "3. Never write pseudo-code that could be pasted into an editor.\n"
    "4. Never give the final numeric answer to a homework question.\n"
    "5. Explain concepts, give analogies, and outline the steps the student "
    "should take themselves.\n"
    "6. Offer two or three alternative ways to attack the problem, and say when "
    "each one is a good fit.\n\n"
    "Keep the reply under about 250 words. Write in clear, friendly English."
)

RETRY_SUFFIX = (
    "\n\nYour previous reply contained code or a full solution, which is not "
    "allowed. Reply again with plain-English logic and approaches only. Do not "
    "include any code fences, function definitions, class definitions, or any "
    "block that looks like source code."
)


class GeminiError(RuntimeError):
    """Raised when the Gemini API call fails or returns nothing usable."""


def _build_payload(
    question: str,
    subject_label: str,
    extra_instruction: str,
    system_override: str | None = None,
) -> dict:
    if system_override is not None:
        system = system_override
        if subject_label:
            system += f"\nContext: {subject_label}."
        if extra_instruction:
            system += extra_instruction
    else:
        system = SYSTEM_INSTRUCTION
        if subject_label:
            system += f"\nThe student is asking in the context of: {subject_label}."
        if extra_instruction:
            system += extra_instruction

    return {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800,
        },
    }


def _post_once(model: str, payload: dict, key: str) -> tuple[int, str]:
    """Single call to one model. Returns (status, body_text)."""
    try:
        response = httpx.post(
            ENDPOINT_TEMPLATE.format(model=model),
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return 0, f"network error: {exc}"
    return response.status_code, response.text


def _post(
    question: str,
    subject_label: str,
    extra_instruction: str = "",
    system_override: str | None = None,
) -> str:
    key = settings.gemini_api_key
    if not key:
        raise GeminiError("GEMINI_API_KEY is not configured.")

    payload = _build_payload(question, subject_label, extra_instruction, system_override)
    last_error = "unknown error"

    for model in MODEL_FALLBACKS:
        for attempt in range(MAX_ATTEMPTS_PER_MODEL):
            status, body = _post_once(model, payload, key)

            if status == 200:
                try:
                    data = __import__("json").loads(body)
                except ValueError as exc:
                    last_error = f"invalid JSON from Gemini: {exc}"
                    continue
                candidates = data.get("candidates") or []
                if not candidates:
                    last_error = "Gemini returned no candidates."
                    continue
                parts = candidates[0].get("content", {}).get("parts") or []
                text = (parts[0].get("text") or "").strip() if parts else ""
                if not text:
                    last_error = "Gemini returned an empty reply."
                    continue
                return text

            last_error = f"{model} -> {status}: {body[:160]}"
            if status not in RETRYABLE_STATUS:
                # A non-retryable error (e.g. 400 bad request, 403 bad key)
                # means trying another model will not help.
                raise GeminiError(f"Gemini returned {status}: {body[:200]}")

    raise GeminiError(f"Gemini unavailable after retries. Last error: {last_error}")


def explain_logic(question: str, subject_label: str = "") -> str:
    """Ask Gemini for a plain-English logic explanation.

    Does not enforce the code-block rule itself; the caller does that so it
    can decide whether to retry or fall back.
    """
    return _post(question, subject_label)


def explain_logic_strict(question: str, subject_label: str = "") -> str:
    """Retry with an extra instruction that forbids code."""
    return _post(question, subject_label, extra_instruction=RETRY_SUFFIX)


DASHBOARD_SYSTEM_INSTRUCTION = (
    "You are a data analyst writing a briefing for a college principal. "
    "The user will give you a set of numbers. Your ONLY job is to write a single "
    "paragraph of 3 to 5 sentences that summarises those specific numbers. "
    "Do NOT explain how to write a briefing. Do NOT offer approaches or options. "
    "Do NOT use bullet points, headings, or numbered lists. "
    "Just the summary paragraph itself. "
    "Cover: the academic trajectory, the strongest department, the weakest "
    "department, and one thing worth attention. Use only the numbers provided. "
    "Under 120 words."
)


def _format_dashboard_stats(stats: dict) -> str:
    lines: list[str] = []
    lines.append(f"Total students: {stats.get('total_students', 0)}")
    lines.append(f"Average attendance: {stats.get('average_attendance', 0)}%")
    lines.append(f"Average marks: {stats.get('average_marks', 0)}%")
    lines.append(
        f"Placement readiness average: {stats.get('placement_readiness_average', 0)}"
    )
    lines.append(f"Placement rate: {stats.get('placement_rate', 0)}")
    lines.append(f"Total students placed: {stats.get('placement_total', 0)}")
    placement_points = stats.get('placement_trend') or []
    if placement_points:
        lines.append("Placements per month:")
        for point in placement_points:
            lines.append(f"  {point.get('month')}: {point.get('placed')}")

    institution = stats.get("academic_institution") or []
    if institution:
        lines.append("Institution academic average by month:")
        for point in institution:
            lines.append(f"  {point.get('month')}: {point.get('avg')}%")

    departments = stats.get("departments") or []
    for department in departments:
        lines.append(f"Department {department.get('name')}:")
        for month in department.get("months", []):
            lines.append(f"  {month.get('month')}: {month.get('avg')}%")

    return "\n".join(lines)


def summarize_dashboard(stats: dict) -> str:
    """Ask Gemini for a one-paragraph institutional summary.

    Raises GeminiError on any failure. The caller is expected to catch it
    and render the dashboard without a summary.
    """
    body = _format_dashboard_stats(stats)
    prompt = (
        "Here are the latest institution numbers. Write the briefing.\n\n"
        + body
    )
    return _post(
        prompt,
        subject_label="",
        extra_instruction="",
        system_override=DASHBOARD_SYSTEM_INSTRUCTION,
    )
