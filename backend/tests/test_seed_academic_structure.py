import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Department,
    FacultyProfile,
    FacultySubject,
    StudentProfile,
    Subject,
    User,
)
from app.seed_academic_structure import seed_academic_structure


def test_seed_academic_structure_is_idempotent(database, demo_users):
    with database() as session:
        first_run = seed_academic_structure(session)

    assert first_run["subjects_created"] == 32
    assert first_run["student_profiles_created"] == 1
    assert first_run["faculty_profiles_created"] == 1
    assert first_run["faculty_subjects_created"] == 3

    with database() as session:
        second_run = seed_academic_structure(session)
        first_student_profile = session.query(StudentProfile).one()
        initial_student_placement = (first_student_profile.year, first_student_profile.semester)

    assert second_run["subjects_created"] == 0
    assert second_run["student_profiles_created"] == 0
    assert second_run["faculty_profiles_created"] == 0
    assert second_run["faculty_subjects_created"] == 0
    assert second_run["subjects_skipped"] == 32
    assert second_run["student_profiles_skipped"] == 1
    assert second_run["faculty_profiles_skipped"] == 1
    assert second_run["faculty_subjects_skipped"] == 3

    with database() as session:
        student_profile = session.query(StudentProfile).one()
        assert (student_profile.year, student_profile.semester) == initial_student_placement


def test_seed_creates_four_subjects_for_each_year_and_semester(database, demo_users):
    with database() as session:
        seed_academic_structure(session)
        subjects = session.query(Subject).order_by(Subject.year, Subject.semester).all()

    assert len(subjects) == 32
    assert all(
        len([subject for subject in subjects if subject.year == year and subject.semester == semester])
        == 4
        for year in range(1, 5)
        for semester in range(1, 3)
    )


def test_academic_unique_constraints_are_enforced(database, demo_users):
    with database() as session:
        department = session.query(Department).one()
        subject = Subject(
            department_id=department.id,
            code="CS301",
            name="Data Structures",
            year=3,
            semester=1,
        )
        session.add(subject)
        session.flush()

        session.add(
            Subject(
                department_id=department.id,
                code="CS301",
                name="Algorithms",
                year=3,
                semester=1,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    with database() as session:
        department = session.query(Department).one()
        student = session.query(User).filter_by(role="student").one()
        session.add_all(
            [
                StudentProfile(
                    user_id=student.id,
                    department_id=department.id,
                    year=1,
                    semester=1,
                ),
            ]
        )
        session.flush()
        session.add(
            StudentProfile(
                user_id=student.id,
                department_id=department.id,
                year=2,
                semester=1,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_subject_name_year_semester_unique_constraint_is_enforced(database, demo_users):
    with database() as session:
        department = session.query(Department).one()
        session.add(
            Subject(
                department_id=department.id,
                code="CS301",
                name="Data Structures",
                year=3,
                semester=1,
            )
        )
        session.flush()
        session.add(
            Subject(
                department_id=department.id,
                code="CS302",
                name="Data Structures",
                year=3,
                semester=1,
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()


def test_faculty_profile_unique_constraint_is_enforced(database, demo_users):
    with database() as session:
        department = session.query(Department).one()
        faculty = session.query(User).filter_by(role="faculty").one()
        session.add(FacultyProfile(user_id=faculty.id, department_id=department.id))
        session.flush()
        session.add(FacultyProfile(user_id=faculty.id, department_id=department.id))

        with pytest.raises(IntegrityError):
            session.flush()


def test_faculty_subject_link_unique_constraint_is_enforced(database, demo_users):
    with database() as session:
        department = session.query(Department).one()
        faculty = session.query(User).filter_by(role="faculty").one()
        subject = Subject(
            department_id=department.id,
            code="CS301",
            name="Data Structures",
            year=3,
            semester=1,
        )
        session.add(subject)
        session.flush()
        session.add(FacultySubject(faculty_id=faculty.id, subject_id=subject.id))
        session.flush()
        session.add(FacultySubject(faculty_id=faculty.id, subject_id=subject.id))

        with pytest.raises(IntegrityError):
            session.flush()
