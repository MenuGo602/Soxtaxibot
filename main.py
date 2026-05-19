import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
import handlers  # Asosiy taksi va navbat tizimi logikasi

# 1. Render kutayotgan veb-server (Portni eshitish uchun)
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

# 2. Botni ishga tushirish qismi
async def main():
    # Render uchun fona veb-sahifani yurgizish
    asyncio.create_task(start_webhook())

    # Bot va Dispatcher sozlamalari
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Handlerlarni ulash
    dp.include_router(handlers.router)
    
    # Telegram xabarlarini tozalab, yangidan polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")
        
