import sqlite3
from aiogram import F, types
from config import bot, dp, DB_NAME

def init_chat_db():
    """Chat tizimi uchun ma'lumotlar bazasida jadval yaratish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_chats (
                driver_id INTEGER PRIMARY KEY,
                client_id INTEGER
            )
        """)
        conn.commit()

# Jadvalni avtomat ishga tushiramiz
init_chat_db()

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_driver_or_client_chat(message: types.Message):
    """Haydovchi va mijoz o'rtasidagi xabarlarni bot orqali bir-biriga uzatish"""
    user_id = message.from_user.id
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Tekshiramiz: Xabar yozgan odam faol haydovchimisiz?
        cursor.execute("SELECT client_id FROM active_chats WHERE driver_id = ?", (user_id,))
        chat_as_driver = cursor.fetchone()
        
        if chat_as_driver:
            client_id = chat_as_driver[0]
            try:
                await bot.send_message(
                    chat_id=client_id,
                    text=f"💬 **Haydovchidan xabar:**\n\n{message.text}"
                )
            except Exception:
                await message.answer("⚠️ Xabar mijozga yetkazilmadi (Mijoz botni bloklagan bo'lishi mumkin).")
            return

        # 2. Tekshiramiz: Xabar yozgan odam faol mijozmisiz?
        cursor.execute("SELECT driver_id FROM active_chats WHERE client_id = ?", (user_id,))
        chat_as_client = cursor.fetchone()
        
        if chat_as_client:
            driver_id = chat_as_client[0]
            try:
                await bot.send_message(
                    chat_id=driver_id,
                    text=f"💬 **Mijozdan xabar:**\n\n{message.text}"
                )
            except Exception:
                await message.answer("⚠️ Xabar haydovchiga yetkazilmadi.")
            return

    # Agar hech qanday faol chatda bo'lmasa, xabarga tegmaydi (boshqa handlerlar ishlayveradi)
