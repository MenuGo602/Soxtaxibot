import sqlite3
from aiogram import F, types
from config import bot, dp, DB_NAME

@dp.callback_query(F.data.startswith("cancel_search_"))
async def cancel_client_search(call: types.CallbackQuery):
    await call.answer()
    client_id = int(call.data.split("_")[2])
    
    # Qidiruvni bekor qilish matni
    await call.message.edit_text("❌ **Taksi qidirish arizangiz muvaffaqiyatli bekor qilindi.**")

def start_anon_chat(driver_id, client_id):
    """Safar boshlanganda anonim chatni yoqish (Ushbu funksiya chatni faollashtiradi)"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO active_chats (driver_id, client_id) VALUES (?, ?)", (driver_id, client_id))
        conn.commit()

def stop_anon_chat(driver_id):
    """Safar tugaganda yoki bekor bo'lganda chatni o'chirish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_chats WHERE driver_id = ?", (driver_id,))
        conn.commit()
