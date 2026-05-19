import os
import asyncio
from aiohttp import web
from aiogram import Bot
from config import TOKEN, dp  # config.py ichidagi dp ni olamiz

# Botni yaratamiz
bot = Bot(token=TOKEN)

# 1. Render uchun oddiy veb-server (port 10000)
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

# 2. Asosiy funksiya
async def main():
    # Render veb-serverini yurgizamiz
    asyncio.create_task(start_webhook())
    
    # handlers.py import qilinishi shart (u ichidagi dekoratorlarni dp ga ulaydi)
    import handlers  
    
    # Botni ishga tushiramiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
