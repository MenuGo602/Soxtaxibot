import sqlite3
import time
from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import bot, dp, DB_NAME

# Pochta uchun yangi holatlar (states)
class PostOrder(StatesGroup):
    choosing_dir = State()
    entering_details = State()
    entering_phone = State()

# Bosh sahifaga Pochta tugmasini ulash uchun handler
@dp.callback_query(F.data == "client_post_order")
async def start_post_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    builder = InlineKeyboardBuilder()
    directions = ["Sox-Fer", "Fer-Sox", "Sox-Kok", "Kok-Sox", "Sox-Rish", "Rish-Sox"]
    for d in directions:
        builder.button(text=f"📦 {d.replace('-', ' -> ')}", callback_data=f"pdir_{d}")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_start")
    builder.adjust(1)
    await call.message.edit_text("📦 Pochta (yuk) qaysi yo'nalish bo'yicha yuboriladi?", reply_markup=builder.as_markup())
    await state.set_state(PostOrder.choosing_dir)

# MANA SHU QATOR TO'G'RILANDI: PostOrder.choosing_dir qilindi
@dp.callback_query(PostOrder.choosing_dir, F.data.startswith("pdir_"))
async def post_dir_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    direction = call.data.split("_")[1]
    await state.update_data(p_dir=direction)
    await call.message.answer("📦 Yuk haqida qisqacha ma'lumot bering (Masalan: 'Bitta korobka kiyim' yoki 'Muhim hujjatlar'):")
    await state.set_state(PostOrder.entering_details)

@dp.message(PostOrder.entering_details)
async def post_details_entered(message: types.Message, state: FSMContext):
    await state.update_data(p_details=message.text)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True))
    await message.answer("📞 Bog'lanish uchun telefon raqamingizni kiriting yoki tugmani bosing:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(PostOrder.entering_phone)

@dp.message(PostOrder.entering_phone, F.contact | F.text)
async def post_phone_entered(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    direction = data['p_dir']
    details = data['p_details']
    client_name = message.from_user.full_name
    
    await message.answer("🎉 Pochta buyurtmangiz qabul qilindi. Haydovchilarga yuborilmoqda...", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT driver_id FROM taxi_queue WHERE direction = ? AND status = 'waiting'", (direction,))
        drivers = cursor.fetchall()
        
    for drv in drivers:
        drv_id = drv[0]
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Yukni olish (Bog'lanish)", callback_data=f"take_post_{message.from_user.id}_{phone[:9]}")
        
        text = (
            f"📦 **YANGI POCHTA / YUK BOR!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Yo'nalish:** {direction.replace('-', ' -> ')}\n"
            f"ℹ️ **Yuk tavsifi:** {details}\n"
            f"🧑‍💼 **Yuboruvchi:** {client_name}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Agar bagajingizda joy bo'lsa, yukni olib qo'shimcha pul ishlashingiz mumkin!*"
        )
        try:
            await bot.send_message(chat_id=drv_id, text=text, reply_markup=builder.as_markup())
        except:
            pass

@dp.callback_query(F.data.startswith("take_post_"))
async def driver_take_post(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    client_id = int(parts[2])
    
    await call.message.edit_text(
        f"{call.message.text}\n\n✅ **Siz ushbu yukni qabul qildingiz!**\n"
        f"📞 Mijoz bilan bog'lanish tugmasi orqali lichkaga o'ting."
    )
    
    try:
        await bot.send_message(
            chat_id=client_id, 
            text=f"🎉 **Pochtangizni haydovchi olib ketishga rozi bo'ldi!**\n\n🧑‍✈️ Haydovchi: [{call.from_user.full_name}](tg://user?id={call.from_user.id}) siz bilan hozir bog'lanadi.",
            parse_mode="Markdown"
        )
    except:
        pass
