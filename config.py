import sqlite3
import logging
import os  # <-- Muhit o'zgaruvchilari bilan ishlash uchun qo'shildi
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Tokenni server muhitidan olamiz, agar u yerda bo'lmasa, test tokenini ishlatadi
TOKEN = os.getenv("BOT_TOKEN", "8883038818:AAHqRC2MRWQmJrhqS2l6yCbzyKvy524jVz0")
DB_NAME = "taxi.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Asosiy jadvallarni yaratish
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                phone TEXT, 
                role TEXT DEFAULT 'client',
                name TEXT, 
                car_info TEXT, 
                balance REAL DEFAULT 0.0,
                rating REAL DEFAULT 5.0,
                trips_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS taxi_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                driver_id INTEGER, 
                direction TEXT,
                has_women TEXT DEFAULT 'yoq', 
                current_passengers INTEGER DEFAULT 0,
                max_passengers INTEGER DEFAULT 4, 
                joined_at REAL, 
                status TEXT DEFAULT 'waiting'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ride_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                driver_id INTEGER, 
                client_id INTEGER,
                direction TEXT, 
                seats INTEGER, 
                has_women TEXT, 
                timestamp REAL, 
                status TEXT
            )
        """)
        conn.commit()

        # 2. MIGRATSIYA
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'balance' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0.0")
        if 'rating' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN rating REAL DEFAULT 5.0")
        if 'trips_count' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN trips_count INTEGER DEFAULT 0")
            
        conn.commit()
