import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Department, FacultySubject, Subject, User


def assign_faculty_to_subjects(session: Session) -> dict[str, int]:
    counts = {
        "departments": 0,
        "subjects_already_assigned": 0,
        "links_created": 0,
        "subjects_without_faculty_available": 0,
    }

    assigned_subject_ids = set(session.scalars(select(FacultySubject.subject_id)).all())
    departments = session.scalars(select(Department).order_by(Department.id)).all()

    for department in departments:
        counts["departments"] += 1
        faculty = session.scalars(
            select(User)
            .where(User.role == "faculty", User.department_id == department.id)
            .order_by(User.id)
        ).all()
        subjects = session.scalars(
            select(Subject)
            .where(Subject.department_id == department.id)
            .order_by(Subject.year, Subject.semester, Subject.code)
        ).all()

        next_index = 0
        for subject in subjects:
            if subject.id in assigned_subject_ids:
                counts["subjects_already_assigned"] += 1
                continue
            if not faculty:
                counts["subjects_without_faculty_available"] += 1
                continue
            member = faculty[next_index % len(faculty)]
            next_index += 1
            session.add(FacultySubject(faculty_id=member.id, subject_id=subject.id))
            assigned_subject_ids.add(subject.id)
            counts["links_created"] += 1

    session.flush()
    return counts


def main() -> None:
    apply_changes = "--apply" in sys.argv
    with SessionLocal() as session:
        counts = assign_faculty_to_subjects(session)
        if apply_changes:
            session.commit()
            print("APPLIED. Faculty assignment counts:")
        else:
            session.rollback()
            print("DRY RUN (nothing written). Would apply:")
        for name, count in counts.items():
            print(f"{name}: {count}")


if __name__ == "__main__":
    main()
