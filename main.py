import asyncio
import logging
import sys
from config import bot, dp

# Alohida fayllardagi barcha modullarni botga ulash
import handlers        # Asosiy taksi va navbat tizimi
import client_actions  # Arizani bekor qilish tizimi
import driver_chat     # Avtomatlashtirilgan anonim chat tizimi
import client_post     # Yangi qo'shilgan pochta va yuk yuborish tizimi

# Loglarni sozlash (Xatoliklarni terminalda aniq ko'rish uchun)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    print("🤖 So'xTaxi boti barcha modullar bilan muvaffaqiyatli ishga tushdi...")
    
    # Bot o'chiq bo'lgan paytda kelgan eski xabarlarni o'chirib yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Botni yangi xabarlarni kutish rejimida ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🤖 Bot to'xtatildi!")
