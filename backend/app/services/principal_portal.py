"""Principal portal service: institution-wide trends and an AI summary.

Reads only. No student PII is returned.
"""

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    Attendance,
    Course,
    Department,
    Mark,
    PlacementSourceRecord,
    StudentProfile,
    User,
)
from app.schemas.principal_portal import (
    AcademicTrend,
    PlacementReadinessTrend,
    PlacementTrendView,
    PrincipalDashboard,
    SeriesLine,
    TrendPoint,
)
from app.services.gemini import GeminiError, summarize_dashboard
from app.services.placements import get_placement_trend


MONTHS = 6
PLACEMENT_NOTE = (
    "Average of aptitude, coding, and mock interview scores from placement "
    "readiness records."
)


def _month_keys(count: int) -> list[str]:
    today = date.today()
    keys: list[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(keys))


def _month_start(months_ago: int) -> datetime:
    today = date.today().replace(day=1)
    year, month = today.year, today.month
    for _ in range(months_ago):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _academic_trend(db: Session, months: int) -> AcademicTrend:
    since = _month_start(months - 1)

    rows = db.execute(
        select(
            Department.name.label("department"),
            Mark.submitted_at,
            Mark.score,
            Assessment.max_score,
        )
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .join(Course, Course.id == Assessment.course_id)
        .join(Department, Department.id == Course.department_id)
        .where(Mark.submitted_at.is_not(None))
        .where(Mark.is_submitted.is_(True))
        .where(Mark.submitted_at >= since)
    ).all()

    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for department, submitted_at, score, max_score in rows:
        if not submitted_at or max_score is None or float(max_score) == 0:
            continue
        month_key = submitted_at.strftime("%Y-%m")
        percentage = float(score) / float(max_score) * 100.0
        buckets[department][month_key].append(percentage)

    keys = _month_keys(months)

    by_department: list[SeriesLine] = []
    for department_name in sorted(buckets):
        points = [
            TrendPoint(label=key, value=_average(buckets[department_name].get(key, [])))
            for key in keys
        ]
        by_department.append(SeriesLine(name=department_name, points=points))

    institution_buckets: dict[str, list[float]] = defaultdict(list)
    for department_buckets in buckets.values():
        for month_key, values in department_buckets.items():
            institution_buckets[month_key].extend(values)

    institution_points = [
        TrendPoint(label=key, value=_average(institution_buckets.get(key, [])))
        for key in keys
    ]

    all_values = [v for month_values in institution_buckets.values() for v in month_values]
    overall = _average(all_values)

    return AcademicTrend(
        institution=institution_points,
        by_department=by_department,
        overall_average=overall,
    )


def _placement_readiness_trend(db: Session, months: int) -> PlacementReadinessTrend:
    rows = db.execute(
        select(
            PlacementSourceRecord.aptitude_score,
            PlacementSourceRecord.coding_score,
            PlacementSourceRecord.mock_interview_score,
        )
    ).all()

    scores: list[float] = []
    for aptitude, coding, mock in rows:
        parts = [float(v) for v in (aptitude, coding, mock) if v is not None]
        if parts:
            scores.append(sum(parts) / len(parts))

    overall = round(sum(scores) / len(scores), 2) if scores else 0.0

    keys = _month_keys(months)
    points = [
        TrendPoint(label=key, value=overall if index == len(keys) - 1 else 0.0)
        for index, key in enumerate(keys)
    ]

    return PlacementReadinessTrend(
        points=points,
        overall_average=overall,
        note=PLACEMENT_NOTE,
    )


def _headline_numbers(db: Session) -> tuple[int, float, float]:
    total_students = db.scalar(select(func.count()).select_from(StudentProfile)) or 0

    attendance_statuses = db.execute(select(Attendance.status)).scalars().all()
    if attendance_statuses:
        present = sum(1 for s in attendance_statuses if s in ("present", "late"))
        average_attendance = round(present / len(attendance_statuses) * 100.0, 2)
    else:
        average_attendance = 0.0

    marks_rows = db.execute(
        select(Mark.score, Assessment.max_score)
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .where(Mark.is_submitted.is_(True))
    ).all()
    percentages = [
        float(score) / float(max_score) * 100.0
        for score, max_score in marks_rows
        if max_score is not None and float(max_score) > 0
    ]
    average_marks = round(sum(percentages) / len(percentages), 2) if percentages else 0.0

    return int(total_students), average_attendance, average_marks


def _build_summary_payload(dashboard: PrincipalDashboard) -> dict:
    return {
        "total_students": dashboard.total_students,
        "average_attendance": dashboard.average_attendance,
        "average_marks": dashboard.average_marks,
        "academic_institution": [
            {"month": p.label, "avg": p.value} for p in dashboard.academic_trend.institution
        ],
        "departments": [
            {
                "name": line.name,
                "months": [{"month": p.label, "avg": p.value} for p in line.points],
            }
            for line in dashboard.academic_trend.by_department
        ],
        "placement_readiness_average": dashboard.placement_readiness.overall_average,
        "placement_rate": dashboard.placement_trend.placement_rate,
        "placement_total": dashboard.placement_trend.total_placed,
        "placement_trend": [
            {"month": point.label, "placed": point.value}
            for point in dashboard.placement_trend.points
        ],
    }


def _safe_ai_summary(dashboard: PrincipalDashboard) -> str | None:
    try:
        return summarize_dashboard(_build_summary_payload(dashboard))
    except GeminiError:
        return None


def get_principal_dashboard(db: Session, principal: User) -> PrincipalDashboard:
    total_students, average_attendance, average_marks = _headline_numbers(db)
    academic_trend = _academic_trend(db, MONTHS)
    placement_readiness = _placement_readiness_trend(db, MONTHS)
    placement_trend_raw = get_placement_trend(db)
    placement_trend = PlacementTrendView(
        points=[TrendPoint(label=p.label, value=p.value) for p in placement_trend_raw.points],
        total_placed=placement_trend_raw.total_placed,
        placement_rate=placement_trend_raw.placement_rate,
        note=placement_trend_raw.note,
    )

    dashboard = PrincipalDashboard(
        total_students=total_students,
        average_attendance=average_attendance,
        average_marks=average_marks,
        academic_trend=academic_trend,
        placement_readiness=placement_readiness,
        placement_trend=placement_trend,
        ai_summary=None,
    )
    dashboard.ai_summary = _safe_ai_summary(dashboard)
    return dashboard
