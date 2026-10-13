import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import bcrypt
from faker import Faker
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import (
    AcademicSourceRecord,
    Alert,
    Assessment,
    Attendance,
    AttendanceSourceRecord,
    Course,
    Department,
    EngagementSourceRecord,
    Enrollment,
    FacultyFeedback,
    FeedbackSourceRecord,
    Intervention,
    InterventionOutcome,
    LmsSourceRecord,
    Mark,
    PlacementSourceRecord,
    RiskScore,
    SkillsSourceRecord,
    StudentFeedback,
    StudentNote,
    User,
)

SEED = 20261012
SEMESTER = "Fall 2026"
DEPARTMENTS = [
    ("Computer Science", "CS"),
    ("Business Administration", "BUS"),
    ("Engineering", "ENG"),
    ("Arts and Humanities", "ARTS"),
]
COURSES = [
    ("Foundations", "Foundations of {subject}"),
    ("Methods", "Research Methods in {subject}"),
    ("Analytics", "Applied {subject} Analytics"),
    ("Communication", "Professional Communication"),
    ("Ethics", "Ethics and Society"),
    ("Project", "Collaborative {subject} Project"),
]
INTERVENTION_TYPES = ["mentoring", "remedial_class", "counseling_referral"]
ENGAGEMENT_TYPES = ("events", "clubs", "hackathons", "certifications")
SUBJECT_CODES = ("SUBJ-01", "SUBJ-02", "SUBJ-03", "SUBJ-04", "SUBJ-05")


def _password_hash() -> str:
    return bcrypt.hashpw(b"DemoPass123!", bcrypt.gensalt()).decode("utf-8")


def _external_student_id(student_id: int, source_number: int) -> str:
    canonical = f"STU-{student_id:06d}"
    variants = (
        canonical,
        f" {canonical.lower()} ",
        f"STU_{student_id:06d}",
        f"student-{student_id}",
        str(student_id),
    )
    return variants[source_number % len(variants)]


def _seed_integration_sources(session, students: list[User], randomizer: random.Random) -> None:
    academic_rows = []
    attendance_rows = []
    lms_rows = []
    engagement_rows = []
    placement_rows = []
    skills_rows = []
    feedback_rows = []

    for index, student in enumerate(students):
        student_id = student.id
        academic_rows.append(
            AcademicSourceRecord(
                external_student_id=_external_student_id(student_id, 0),
                cgpa=None if index % 11 == 0 else Decimal(str(round(randomizer.uniform(4.8, 9.7), 2))),
                marks_percentage=(
                    Decimal("135") if index % 67 == 0
                    else None if index % 13 == 0
                    else Decimal(str(round(randomizer.uniform(38, 98), 2)))
                ),
                backlog_count=(
                    -2 if index % 83 == 0
                    else None if index % 17 == 0
                    else randomizer.randint(0, 4)
                ),
                term=SEMESTER,
            )
        )
        attendance_values = [
            (None, Decimal("145") if index % 71 == 0 else Decimal(str(randomizer.randint(42, 100))))
        ]
        attendance_values.extend(
            (
                subject,
                None if (index + subject_index) % 19 == 0
                else Decimal("-5") if index % 89 == 0 and subject_index == 0
                else Decimal(str(randomizer.randint(35, 100))),
            )
            for subject_index, subject in enumerate(SUBJECT_CODES)
        )
        for item_index, (subject, percentage) in enumerate(attendance_values):
            attendance_rows.append(
                AttendanceSourceRecord(
                    external_student_id=_external_student_id(student_id, item_index),
                    subject_code=subject,
                    attendance_percentage=percentage,
                )
            )
        lms_rows.append(
            LmsSourceRecord(
                external_student_id=_external_student_id(student_id, 1),
                login_count=-4 if index % 97 == 0 else None if index % 23 == 0 else randomizer.randint(0, 80),
                assignment_completion_percentage=(
                    Decimal("125") if index % 79 == 0
                    else None if index % 14 == 0
                    else Decimal(str(randomizer.randint(20, 100)))
                ),
            )
        )
        for activity_index, activity_type in enumerate(ENGAGEMENT_TYPES):
            engagement_rows.append(
                EngagementSourceRecord(
                    external_student_id=_external_student_id(student_id, activity_index + 2),
                    activity_type=activity_type,
                    activity_count=(
                        -1 if index % 101 == 0 and activity_index == 0
                        else None if (index + activity_index) % 29 == 0
                        else randomizer.randint(0, 8)
                    ),
                )
            )
        placement_rows.append(
            PlacementSourceRecord(
                external_student_id=_external_student_id(student_id, 2),
                aptitude_score=Decimal("110") if index % 73 == 0 else Decimal(str(randomizer.randint(25, 100))),
                coding_score=None if index % 16 == 0 else Decimal(str(randomizer.randint(15, 100))),
                mock_interview_score=Decimal("-8") if index % 91 == 0 else Decimal(str(randomizer.randint(20, 100))),
            )
        )
        skills_rows.append(
            SkillsSourceRecord(
                external_student_id=_external_student_id(student_id, 3),
                technical_score=Decimal("140") if index % 61 == 0 else Decimal(str(randomizer.randint(25, 100))),
                soft_skill_score=None if index % 18 == 0 else Decimal(str(randomizer.randint(30, 100))),
            )
        )
        feedback_rows.append(
            FeedbackSourceRecord(
                external_student_id=_external_student_id(student_id, 4),
                rating=Decimal("8") if index % 107 == 0 else None if index % 21 == 0 else Decimal(str(randomizer.randint(2, 5))),
                category=randomizer.choice(("teaching", "campus", "support")),
            )
        )

    for rows in (
        academic_rows,
        attendance_rows,
        lms_rows,
        engagement_rows,
        placement_rows,
        skills_rows,
        feedback_rows,
    ):
        for index in range(0, len(rows), 47):
            duplicate = rows[index]
            duplicate_values = {
                column.name: getattr(duplicate, column.name)
                for column in duplicate.__table__.columns
                if column.name != "id"
            }
            rows.append(type(duplicate)(**duplicate_values))

    academic_rows.append(
        AcademicSourceRecord(external_student_id="STU-999999", cgpa=Decimal("7.50"))
    )
    session.add_all(
        academic_rows
        + attendance_rows
        + lms_rows
        + engagement_rows
        + placement_rows
        + skills_rows
        + feedback_rows
    )


def seed() -> None:
    faker = Faker()
    faker.seed_instance(SEED)
    randomizer = random.Random(SEED)
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(User)):
            raise RuntimeError("The database is not empty; refusing to modify existing records.")

        departments = [
            Department(name=name, code=code) for name, code in DEPARTMENTS
        ]
        session.add_all(departments)
        session.flush()

        password_hash = _password_hash()
        students_by_department: dict[int, list[User]] = {}
        faculty_by_department: dict[int, list[User]] = {}
        for department in departments:
            faculty = [
                User(
                    email=f"faculty.{department.code.lower()}.{number}@demo.invalid",
                    full_name=faker.name(),
                    role="faculty",
                    department_id=department.id,
                    password_hash=password_hash,
                )
                for number in range(1, 6)
            ]
            students = [
                User(
                    email=f"student.{department.code.lower()}.{number:03}@demo.invalid",
                    full_name=faker.name(),
                    role="student",
                    department_id=department.id,
                    password_hash=password_hash,
                )
                for number in range(1, 76)
            ]
            session.add_all(faculty + students)
            faculty_by_department[department.id] = faculty
            students_by_department[department.id] = students

        session.add_all(
            [
                User(
                    email=f"dean.{department.code.lower()}@demo.invalid",
                    full_name=faker.name(),
                    role="dean",
                    department_id=department.id,
                    password_hash=password_hash,
                )
                for department in departments
            ]
            + [
                User(
                    email="principal@demo.invalid",
                    full_name=faker.name(),
                    role="principal",
                    department_id=None,
                    password_hash=password_hash,
                )
            ]
        )
        session.flush()

        courses: dict[int, list[Course]] = {}
        assessments_by_course: dict[int, list[Assessment]] = {}
        for department in departments:
            department_courses = []
            for number, (suffix, title) in enumerate(COURSES, start=1):
                faculty = faculty_by_department[department.id][(number - 1) % 5]
                course = Course(
                    department_id=department.id,
                    faculty_id=faculty.id,
                    code=f"{department.code}{number:03}",
                    name=title.format(subject=department.name),
                    credits=randomizer.choice([3, 4]),
                )
                department_courses.append(course)
            session.add_all(department_courses)
            session.flush()
            courses[department.id] = department_courses

            for course in department_courses:
                assessments = [
                    Assessment(
                        course_id=course.id,
                        title="Midterm examination",
                        assessment_type="exam",
                        max_score=Decimal("100"),
                        due_date=date(2026, 10, 15),
                    ),
                    Assessment(
                        course_id=course.id,
                        title="Course project",
                        assessment_type="project",
                        max_score=Decimal("100"),
                        due_date=date(2026, 11, 20),
                    ),
                ]
                session.add_all(assessments)
                assessments_by_course[course.id] = assessments

        class_dates = [date(2026, 9, 1) + timedelta(days=7 * week) for week in range(8)]
        risk_cutoff = 0.25
        student_courses: dict[int, list[Course]] = {}
        for department in departments:
            department_courses = courses[department.id]
            for student in students_by_department[department.id]:
                selected_courses = randomizer.sample(department_courses, 5)
                student_courses[student.id] = selected_courses
                attendance_misses = 0
                enrollment_rows = []
                attendance_rows = []
                mark_rows = []
                for course in selected_courses:
                    enrollment_rows.append(
                        Enrollment(student_id=student.id, course_id=course.id, semester=SEMESTER)
                    )
                    for meeting_date in class_dates:
                        draw = randomizer.random()
                        if draw < 0.07:
                            status = "absent"
                            attendance_misses += 1
                        elif draw < 0.10:
                            status = "late"
                        else:
                            status = "present"
                        attendance_rows.append(
                            Attendance(
                                student_id=student.id,
                                course_id=course.id,
                                class_date=meeting_date,
                                status=status,
                            )
                        )
                    for assessment in assessments_by_course[course.id]:
                        submitted = randomizer.random() >= 0.06
                        mark_rows.append(
                            Mark(
                                student_id=student.id,
                                assessment_id=assessment.id,
                                score=Decimal(str(randomizer.randint(35, 100) if submitted else 0)),
                                submitted_at=(
                                    datetime.combine(assessment.due_date, time(12), timezone.utc)
                                    if submitted
                                    else None
                                ),
                                is_submitted=submitted,
                            )
                        )
                session.add_all(enrollment_rows + attendance_rows + mark_rows)

                attendance_rate = 1 - attendance_misses / (len(selected_courses) * len(class_dates))
                grade_score = sum(float(mark.score) for mark in mark_rows) / (
                    len(mark_rows) * 100
                )
                missed_submissions = sum(not mark.is_submitted for mark in mark_rows)
                missed_submission_rate = missed_submissions / len(mark_rows)
                score = round(
                    0.45 * (1 - attendance_rate)
                    + 0.40 * (1 - grade_score)
                    + 0.15 * missed_submission_rate,
                    4,
                )
                if score >= 0.30:
                    level = "high"
                elif score >= 0.18:
                    level = "medium"
                else:
                    level = "low"
                factors = {
                    "attendance_rate": round(attendance_rate, 3),
                    "average_mark_rate": round(grade_score, 3),
                    "missed_submissions": missed_submissions,
                    "total_submissions": len(mark_rows),
                }
                session.add(
                    RiskScore(
                        student_id=student.id,
                        score=Decimal(str(score)),
                        risk_level=level,
                        contributing_factors=factors,
                    )
                )

                if score >= risk_cutoff:
                    session.add(
                        Alert(
                            student_id=student.id,
                            alert_type="elevated_risk",
                            severity="high" if level == "high" else "medium",
                        )
                    )
                    session.add(
                        StudentNote(
                            student_id=student.id,
                            author_id=faculty_by_department[department.id][0].id,
                            content="Demo note: schedule a supportive progress check-in.",
                        )
                    )
                    if randomizer.random() < 0.55:
                        intervention = Intervention(
                            student_id=student.id,
                            assigned_by=faculty_by_department[department.id][0].id,
                            intervention_type=randomizer.choice(INTERVENTION_TYPES),
                            description="Demo plan: agree on a short weekly progress check-in.",
                            start_date=date(2026, 10, 1),
                            status=randomizer.choice(["assigned", "in_progress", "completed"]),
                        )
                        session.add(intervention)
                        session.flush()
                        session.add(
                            InterventionOutcome(
                                intervention_id=intervention.id,
                                before_metrics={"attendance_rate": round(attendance_rate, 3)},
                                after_metrics=None,
                                comparison_metrics=None,
                                caveats="Demo baseline only; not a causal estimate.",
                            )
                        )

        session.flush()
        all_students = [
            student
            for department_students in students_by_department.values()
            for student in department_students
        ]
        _seed_integration_sources(session, all_students, randomizer)

        for department in departments:
            faculty = faculty_by_department[department.id]
            for student in randomizer.sample(students_by_department[department.id], 20):
                course = randomizer.choice(student_courses[student.id])
                session.add(
                    FacultyFeedback(
                        student_id=student.id,
                        faculty_id=course.faculty_id,
                        course_id=course.id,
                        rating=randomizer.randint(3, 5),
                        comments="Demo feedback: clear explanations and helpful office hours.",
                    )
                )

            feedback_students = [
                students_by_department[department.id][0],
                *randomizer.sample(students_by_department[department.id][1:], 7),
            ]
            for student in feedback_students:
                course = randomizer.choice(student_courses[student.id])
                session.add(
                    StudentFeedback(
                        student_id=student.id,
                        faculty_id=course.faculty_id,
                        course_id=course.id,
                        message="Demo feedback: your steady participation is appreciated. "
                        "Keep asking questions and sharing your ideas.",
                    )
                )

        session.commit()
        print("Seeded fictional demo data: 4 departments, 300 students, 20 faculty, 4 deans, 1 principal.")
        print("Demo login password for every seeded user: DemoPass123!")
        print("All seeded email addresses use the reserved .invalid domain.")


if __name__ == "__main__":
    seed()
