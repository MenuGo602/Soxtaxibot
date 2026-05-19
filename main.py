import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import TOKEN, dp  # config.py dan dp ni import qilyapmiz

bot = Bot(token=TOKEN)

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

async def main():
    # 1. Eski webhook'larni tozalash (ConflictError ni yo'qotadi)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 2. Veb-serverni yurgizish
    asyncio.create_task(start_webhook())
    
    # 3. Handlerlarni import qilish
    import handlers
    
    # 4. Pollingni boshlash
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
