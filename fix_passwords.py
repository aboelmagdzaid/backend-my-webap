from database import sync_engine, init_database
from security import hash_password
from sqlalchemy import text

# Initialize database
init_database()

with sync_engine.connect() as conn:
    # Get users with non-empty password_hash
    result = conn.execute(text("SELECT id, user_number, password_hash FROM users WHERE password_hash IS NOT NULL AND password_hash != ''"))
    users = result.fetchall()

    for user in users:
        user_id, user_number, plain_password = user
        # Assume password_hash is plain text, hash it
        hashed = hash_password(plain_password)
        print(f"Updating user {user_number}: {plain_password[:10]}... -> {hashed[:20]}...")
        conn.execute(text("UPDATE users SET password_hash = :hash WHERE id = :id"), {"hash": hashed, "id": user_id})
        conn.commit()

print("Password hashes updated.")