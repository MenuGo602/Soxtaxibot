import os
import asyncio
from aiohttp import web
from aiogram import Bot
from config import TOKEN, dp

bot = Bot(token=TOKEN)

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    # Eski webhookni butunlay o'chirib, tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Veb-serverni yurgizish
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    import handlers # Handlerlarni yuklash
    print("Bot muvaffaqiyatli ishga tushdi!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
    
