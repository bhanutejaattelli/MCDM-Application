import os, sys
sys.path.insert(0, os.path.abspath('backend'))
from database import get_all_users

try:
    users = get_all_users()
    print(f"Total users found: {len(users)}")
    admin_count = 0
    for u in users:
        role = u.get("role", "user")
        if role == "admin":
            admin_count += 1
        print(f"UID: {u.get('uid')} | Email: {u.get('email')} | Role: {role}")
    print(f"Total admins: {admin_count}")
except Exception as e:
    print(f"Error: {e}")
