import re
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Department, FacultyProfile, FacultySubject, StudentProfile, Subject, User

SUBJECTS_BY_TRACK: dict[str, Sequence[Sequence[str]]] = {
    "computer": (
        ("Programming Fundamentals", "Discrete Mathematics", "Digital Logic Design", "Technical Communication"),
        ("Object-Oriented Programming", "Data Structures", "Computer Organization", "Engineering Mathematics II"),
        ("Database Systems", "Design and Analysis of Algorithms", "Operating Systems", "Computer Networks"),
        ("Software Engineering", "Theory of Computation", "Microprocessors", "Probability and Statistics"),
        ("Artificial Intelligence", "Compiler Design", "Web Technologies", "Computer Architecture"),
        ("Machine Learning", "Distributed Systems", "Information Security", "Cloud Computing"),
        ("Data Mining", "Mobile Application Development", "Software Testing", "Elective I"),
        ("Project Management", "Big Data Analytics", "Professional Elective", "Capstone Project"),
    ),
    "electronics": (
        ("Basic Electrical Engineering", "Engineering Physics", "Engineering Mathematics I", "Technical Communication"),
        ("Circuit Theory", "Electronic Devices", "Digital Logic Design", "Engineering Mathematics II"),
        ("Analog Electronics", "Signals and Systems", "Network Analysis", "Electromagnetic Fields"),
        ("Digital Electronics", "Control Systems", "Electronic Measurements", "Probability and Statistics"),
        ("Microprocessors", "Communication Systems", "Linear Integrated Circuits", "VLSI Design"),
        ("Digital Signal Processing", "Antenna and Wave Propagation", "Embedded Systems", "Elective I"),
        ("Wireless Communication", "Optical Communication", "Microwave Engineering", "Professional Elective"),
        ("Internet of Things", "Advanced Communication Systems", "Project Management", "Capstone Project"),
    ),
    "mechanical": (
        ("Engineering Mechanics", "Engineering Graphics", "Engineering Mathematics I", "Technical Communication"),
        ("Engineering Thermodynamics", "Material Science", "Manufacturing Processes", "Engineering Mathematics II"),
        ("Fluid Mechanics", "Strength of Materials", "Theory of Machines", "Engineering Materials"),
        ("Heat Transfer", "Machine Design I", "Applied Thermodynamics", "Probability and Statistics"),
        ("Machine Design II", "Dynamics of Machinery", "Metrology and Measurements", "Production Engineering"),
        ("Refrigeration and Air Conditioning", "Finite Element Methods", "Automobile Engineering", "Elective I"),
        ("Computer-Aided Manufacturing", "Robotics and Automation", "Industrial Engineering", "Professional Elective"),
        ("Renewable Energy Systems", "Advanced Manufacturing", "Project Management", "Capstone Project"),
    ),
    "civil": (
        ("Building Materials", "Surveying I", "Engineering Mathematics I", "Technical Communication"),
        ("Engineering Mechanics", "Surveying II", "Building Construction", "Engineering Mathematics II"),
        ("Strength of Materials", "Fluid Mechanics", "Structural Analysis I", "Geotechnical Engineering I"),
        ("Concrete Technology", "Structural Analysis II", "Transportation Engineering I", "Probability and Statistics"),
        ("Design of Concrete Structures", "Foundation Engineering", "Water Supply Engineering", "Construction Planning"),
        ("Design of Steel Structures", "Transportation Engineering II", "Environmental Engineering", "Elective I"),
        ("Earthquake Engineering", "Irrigation Engineering", "Quantity Surveying", "Professional Elective"),
        ("Sustainable Construction", "Advanced Structural Design", "Project Management", "Capstone Project"),
    ),
    "business": (
        ("Principles of Management", "Business Mathematics", "Financial Accounting", "Business Communication"),
        ("Marketing Management", "Microeconomics", "Organizational Behaviour", "Business Statistics"),
        ("Human Resource Management", "Cost Accounting", "Business Research Methods", "Macroeconomics"),
        ("Financial Management", "Operations Management", "Business Law", "Management Information Systems"),
        ("Consumer Behaviour", "Corporate Finance", "Strategic Management", "Entrepreneurship"),
        ("Digital Marketing", "Supply Chain Management", "Business Analytics", "Elective I"),
        ("International Business", "Investment Analysis", "Project Management", "Professional Elective"),
        ("Corporate Governance", "Innovation Management", "Business Strategy", "Capstone Project"),
    ),
    "arts": (
        ("Academic Writing", "Introduction to Humanities", "Critical Thinking", "Communication Skills"),
        ("Research Methods", "World Literature", "Ethics and Society", "History of Ideas"),
        ("Cultural Studies", "Media and Society", "Public Speaking", "Creative Practice"),
        ("Contemporary Philosophy", "Literary Analysis", "Social Research", "Digital Humanities"),
        ("Global Perspectives", "Language and Culture", "Arts Management", "Elective I"),
        ("Applied Research", "Public Policy", "Community Engagement", "Professional Elective"),
        ("Advanced Writing", "Cultural Heritage", "Independent Study", "Project Management"),
        ("Research Seminar", "Contemporary Issues", "Professional Practice", "Capstone Project"),
    ),
}


def _track_for_department(department: Department) -> str | None:
    identity = f"{department.code} {department.name}".lower()
    if any(term in identity for term in ("computer", "cse", "software", " cs ")):
        return "computer"
    if any(term in identity for term in ("electronic", "electrical", "ece")):
        return "electronics"
    if any(term in identity for term in ("mechanical", "mech")):
        return "mechanical"
    if any(term in identity for term in ("civil", "construction")):
        return "civil"
    if any(term in identity for term in ("business", "commerce", "management")):
        return "business"
    if any(term in identity for term in ("arts", "humanities", "literature")):
        return "arts"
    return None


def _subject_names(department: Department, year: int, semester: int) -> Sequence[str]:
    track = _track_for_department(department)
    if track is not None:
        return SUBJECTS_BY_TRACK[track][(year - 1) * 2 + semester - 1]

    return (
        f"Foundations of {department.name}",
        f"Applied {department.name} Methods",
        f"{department.name} Systems and Practice",
        "Technical Communication",
    )


def _subject_code_prefix(department: Department) -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", department.code).upper()
    return code[:2] or f"D{department.id}"


def seed_academic_structure(session: Session) -> dict[str, int]:
    counts = {
        "subjects_created": 0,
        "subjects_skipped": 0,
        "student_profiles_created": 0,
        "student_profiles_skipped": 0,
        "faculty_profiles_created": 0,
        "faculty_profiles_skipped": 0,
        "faculty_subjects_created": 0,
        "faculty_subjects_skipped": 0,
    }

    try:
        with session.begin():
            departments = session.scalars(select(Department).order_by(Department.id)).all()
            for department in departments:
                prefix = _subject_code_prefix(department)
                existing_codes = set(
                    session.scalars(
                        select(Subject.code).where(Subject.department_id == department.id)
                    ).all()
                )
                for year in range(1, 5):
                    for semester in range(1, 3):
                        for subject_number, name in enumerate(
                            _subject_names(department, year, semester), start=1
                        ):
                            code = f"{prefix}{year}{(semester - 1) * 10 + subject_number:02}"
                            if code in existing_codes:
                                counts["subjects_skipped"] += 1
                                continue
                            session.add(
                                Subject(
                                    name=name,
                                    code=code,
                                    department_id=department.id,
                                    year=year,
                                    semester=semester,
                                )
                            )
                            existing_codes.add(code)
                            counts["subjects_created"] += 1
            session.flush()

            students = session.scalars(
                select(User).where(User.role == "student").order_by(User.id)
            ).all()
            student_profile_ids = set(
                session.scalars(select(StudentProfile.user_id)).all()
            )
            for index, student in enumerate(students):
                if student.id in student_profile_ids:
                    counts["student_profiles_skipped"] += 1
                    continue
                if student.department_id is None:
                    raise ValueError(f"Student user {student.id} has no department.")

                student_year = index % 4 + 1
                student_semester = index // 4 % 2 + 1
                session.add(
                    StudentProfile(
                        user_id=student.id,
                        department_id=student.department_id,
                        year=student_year,
                        semester=student_semester,
                    )
                )
                counts["student_profiles_created"] += 1
            session.flush()

            faculty_members = session.scalars(
                select(User).where(User.role == "faculty").order_by(User.id)
            ).all()
            faculty_profile_ids = set(
                session.scalars(select(FacultyProfile.user_id)).all()
            )
            for faculty in faculty_members:
                if faculty.department_id is None:
                    raise ValueError(f"Faculty user {faculty.id} has no department.")

                if faculty.id in faculty_profile_ids:
                    counts["faculty_profiles_skipped"] += 1
                else:
                    session.add(
                        FacultyProfile(
                            user_id=faculty.id,
                            department_id=faculty.department_id,
                        )
                    )
                    counts["faculty_profiles_created"] += 1
                session.flush()

                department_subjects = session.scalars(
                    select(Subject)
                    .where(Subject.department_id == faculty.department_id)
                    .order_by(Subject.year, Subject.semester, Subject.code)
                    .limit(3)
                ).all()
                existing_subject_ids = set(
                    session.scalars(
                        select(FacultySubject.subject_id).where(
                            FacultySubject.faculty_id == faculty.id
                        )
                    ).all()
                )
                for subject in department_subjects:
                    if subject.id in existing_subject_ids:
                        counts["faculty_subjects_skipped"] += 1
                        continue
                    session.add(
                        FacultySubject(
                            faculty_id=faculty.id,
                            subject_id=subject.id,
                        )
                    )
                    existing_subject_ids.add(subject.id)
                    counts["faculty_subjects_created"] += 1
                if len(department_subjects) < 2:
                    raise ValueError(
                        f"Department {faculty.department_id} has fewer than two subjects."
                    )
            session.flush()
    except Exception:
        session.rollback()
        raise

    return counts


def main() -> None:
    with SessionLocal() as session:
        counts = seed_academic_structure(session)

    print("Academic structure seed counts:")
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
