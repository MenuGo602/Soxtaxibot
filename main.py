import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
import handlers  # Faylni to'liq import qilamiz

# 1. Bot va Dispatcher obyektlarini yaratamiz
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Handlerlar ichidagi barcha dp dekoratorlarini asosiy dp ga ulab chiqamiz
# Agar handlers ichida router bo'lsa, uni qo'shadi, aks holda tekshiradi
if hasattr(handlers, 'router'):
    dp.include_router(handlers.router)
elif hasattr(handlers, 'dp'):
    dp.include_router(handlers.dp.router)

# 2. Render kutayotgan veb-server qismi
async def handle(request):
    return web.Response(text="Bot is running smoothly!")

async def start_webhook():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# 3. Asosiy ishga tushirish funksiyasi
async def main():
    # Render uchun fonda veb-sahifani yurgizish
    asyncio.create_task(start_webhook())

    # Telegram xabarlarini tozalab, yangidan polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")
        
