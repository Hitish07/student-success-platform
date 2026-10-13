import argparse
import csv
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.models import User

ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0OIl1")


def make_password(length: int = 12) -> str:
    while True:
        pw = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw


parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true", help="actually change passwords (default is a dry run)")
parser.add_argument("--roles", nargs="+", default=["student", "faculty"])
parser.add_argument("--skip", nargs="*", default=[], help="emails to leave untouched")
args = parser.parse_args()

skip = {e.lower() for e in args.skip}
engine = create_engine(settings.database_url)

with Session(engine) as db:
    users = db.scalars(
        select(User).where(User.role.in_(args.roles), User.is_active.is_(True)).order_by(User.role, User.full_name)
    ).all()
    users = [u for u in users if u.email.lower() not in skip]
    print(f"{len(users)} accounts selected (roles: {', '.join(args.roles)})")
    if not args.apply:
        for u in users:
            print(f"  would reset: {u.role:8} {u.full_name} <{u.email}>")
        print("Dry run only. Nothing changed. Add --apply to proceed.")
        raise SystemExit(0)

    out = Path(f"credentials-{datetime.now():%Y%m%d-%H%M%S}.csv")
    rows = []
    for u in users:
        pw = make_password()
        u.password_hash = hash_password(pw)
        rows.append([u.full_name, u.role, u.email, pw])
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "role", "login (email)", "password"])
        writer.writerows(rows)
    try:
        db.commit()
    except Exception:
        db.rollback()
        out.unlink(missing_ok=True)
        raise
    print(f"Updated {len(rows)} accounts. Passwords saved to {out}")
