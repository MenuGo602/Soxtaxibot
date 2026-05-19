import sqlite3
from config import DB_NAME

with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    # Bazadagi barcha foydalanuvchilarni tozalab, botni "0" holatiga keltiramiz
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM taxi_queue")
    conn.commit()

print("🧹 Baza butkul tozalandi! Endi botga birinchi marta kirgan yangi mijozga aylandingiz.")
.