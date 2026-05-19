import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
import handlers  # handlers ichida dp bor deb hisoblaymiz

# Bot va Dispatcher yaratish
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Render uchun oddiy veb-server
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webhook():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# Asosiy funksiya
async def main():
    # Render portini ochish
    asyncio.create_task(start_webhook())

    # Agar handlers ichida 'dp' bo'lsa, pollingni o'sha bilan boshlaymiz
    if hasattr(handlers, 'dp'):
        dp = handlers.dp
    else:
        # Agar yo'q bo'lsa, yangi yaratamiz
        dp = Dispatcher()
        # Bu yerda o'z handlerlaringizni ulashingiz kerak bo'lishi mumkin
        
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
