import sqlite3
import time
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import bot, DB_NAME

async def find_next_driver(direction, seats, women_status, client_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Mijoz ma'lumotlarini tekshirib olamiz
            cursor.execute("SELECT phone, name FROM users WHERE user_id = ?", (client_id,))
            c_data = cursor.fetchone()
            client_phone = c_data[0] if (c_data and c_data[0]) else "Telegram lichka orqali"
            client_name = c_data[1] if (c_data and c_data[1]) else "Yo'lovchi"

            if women_status == 'ha':
                cursor.execute("""
                    SELECT id, driver_id, current_passengers, max_passengers 
                    FROM taxi_queue 
                    WHERE direction = ? 
                      AND has_women = 'ha' 
                      AND status = 'waiting' 
                      AND (max_passengers - current_passengers) >= ? 
                    ORDER BY joined_at ASC LIMIT 1
                """, (direction, seats))
            else:
                cursor.execute("""
                    SELECT id, driver_id, current_passengers, max_passengers 
                    FROM taxi_queue 
                    WHERE direction = ? 
                      AND status = 'waiting' 
                      AND (max_passengers - current_passengers) >= ? 
                    ORDER BY joined_at ASC LIMIT 1
                """, (direction, seats))
                
            driver = cursor.fetchone()
            
        if not driver:
            await bot.send_message(chat_id=client_id, text="😔 Mos bo'sh taksi topilmadi. Birozdan so'ng qayta urunib ko'ring.")
            return
            
        queue_id, driver_id, current_p, max_p = driver
        
        # Tugmalar zanjiri
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Qabul qilish", callback_data=f"ac_{queue_id}_{client_id}_{seats}_{women_status}")
        builder.button(text="❌ Rad etish", callback_data=f"rj_{queue_id}_{client_id}_{seats}_{direction}")
        builder.button(text="💬 Mijozga yozish (Lichka)", url=f"tg://user?id={client_id}")
        builder.adjust(2, 1)
        
        dir_fmt = direction.replace('-', ' -> ')
        await bot.send_message(
            chat_id=driver_id, 
            text=(
                f"🚖 **Yangi buyurtma!**\n\n"
                f"📍 Yo'nalish: {dir_fmt}\n"
                f"👥 Odam: {seats} ta\n"
                f"🙋‍♀️ Ayol bor mashina: {'HA' if women_status == 'ha' else 'FARQI YO`Q'}\n"
                f"👤 Mijoz: {client_name}\n"
                f"📞 Tel: {client_phone}\n\n"
                f"💡 *Agar raqam eski bo'lsa, pastdagi 'Mijozga yozish' tugmasini bosing!*"
            ), 
            reply_markup=builder.as_markup()
        )
    except Exception as e: 
        print(f"Error find_driver in search.py: {e}")

async def notify_queue_shift(direction):
    """Yo'nalishda navbat o'zgarganda orqadagi haydovchilarni avtomat ogohlantirish"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT driver_id FROM taxi_queue 
                WHERE direction = ? AND status = 'waiting' 
                ORDER BY joined_at ASC
            """, (direction,))
            drivers = cursor.fetchall()
            
        total_drivers = len(drivers)
        for idx, drv in enumerate(drivers, start=1):
            driver_id = drv[0]
            try:
                await bot.send_message(
                    chat_id=driver_id,
                    text=(
                        f"🔔 **Navbat o'zgardi!**\n\n"
                        f"📍 Yo'nalish: {direction.replace('-', ' -> ')}\n"
                        f"🔄 Oldindagi haydovchi navbatdan chiqdi.\n\n"
                        f"🔢 Sizning yangi o'rningiz: **{idx}-o'rin** (Jami: {total_drivers} ta)"
                    )
                )
            except Exception as e:
                print(f"Notification error for {driver_id}: {e}")
                
    except Exception as e:
        print(f"Error notify_queue_shift: {e}")
