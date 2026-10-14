"""Interactive one-time first-admin bootstrap; never echoes or stores plaintext password."""
from getpass import getpass
from sqlalchemy import select
from pwdlib import PasswordHash
from app.db import SessionLocal
from app.models import User

username=input("Admin username: ").strip()
name=input("Admin full name: ").strip()
password=getpass("Admin password (12+ chars): ")
if len(password)<12:raise SystemExit("Password must be at least 12 characters")
with SessionLocal() as db:
 if db.scalar(select(User).where(User.username==username)):raise SystemExit("Username already exists")
 db.add(User(username=username,full_name=name,password_hash=PasswordHash.recommended().hash(password),role="Admin",active=True))
 db.commit()
print("Admin created. Keep this command private; remove bootstrap script after use.")