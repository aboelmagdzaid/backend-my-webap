from database import sync_engine
from sqlalchemy import text
with sync_engine.connect() as conn:
    result = conn.execute(text("SELECT user_number, password_hash FROM users WHERE password_hash IS NOT NULL AND password_hash != ''"))
    for row in result:
        print(f'User: {row[0]}, Hash: {row[1][:50]}...')