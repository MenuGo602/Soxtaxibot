import sqlite3
import time
from aiogram import F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import bot, dp, DB_NAME
from states import OrderTaxi, DriverReg
from search import find_next_driver, notify_queue_shift

def init_rating_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                client_id INTEGER,
                stars INTEGER
            )
        """)
        # Users jadvaliga lokatsiya ustunlarini qo'shish (agar yo'q bo'lsa)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN latitude REAL")
            cursor.execute("ALTER TABLE users ADD COLUMN longitude REAL")
        except:
            pass # Agar ustunlar allaqachon bo'lsa, xatoni o'tkazib yuboradi
        conn.commit()

init_rating_db()

async def get_queue_panel_text_and_keyboard(driver_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, direction, has_women, current_passengers, joined_at FROM taxi_queue WHERE driver_id = ? AND status = 'waiting'", (driver_id,))
        active_q = cursor.fetchone()
        
        if not active_q:
            return None, None
            
        q_id, direction, has_women, current_p, joined_at = active_q
        cursor.execute("SELECT driver_id FROM taxi_queue WHERE direction = ? AND status = 'waiting' ORDER BY joined_at ASC", (direction,))
        all_queue = cursor.fetchall()
        
        queue_position = 1
        for idx, drv in enumerate(all_queue, start=1):
            if drv[0] == driver_id:
                queue_position = idx
                break
                
        total_drivers = len(all_queue)
        drivers_ahead = queue_position - 1
        drivers_behind = total_drivers - queue_position

    dir_text = direction.replace('-', ' -> ')
    text = (
        f"📋 **FAOL NAVBATINGIZ PANELI**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 **Yo'nalish:** {dir_text}\n"
        f"🔢 **Sizning navbatingiz:** {queue_position}-o'rin (Jami: {total_drivers} ta)\n"
        f"👥 **Mashinada yo'lovchilar:** {current_p}/4 ta joy band\n"
        f"👩‍🧕 **Ayollar filtri:** {'YONIK (HA)' if has_women == 'ha' else 'O`CHIK (YO`Q)'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Oldingizda: {drivers_ahead} ta haydovchi bor\n"
        f"⏱ Orqangizda: {drivers_behind} ta haydovchi kutmoqda\n\n"
        f"💡 *Ko'chadan odam olsangiz, quyidagi tugmalar orqali joyni yangilang!*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Yangilash", callback_data="refresh_queue_panel")
    builder.button(text="➕ Ko'chadan yo'lovchi", callback_data="add_street_passenger")
    builder.button(text="➖ Yo'lovchi kamaytirish", callback_data="rem_street_passenger")
    builder.button(text="❌ Navbatdan chiqish", callback_data="leave_queue")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_driver_main")
    builder.adjust(1, 2, 1, 1)
    
    return text, builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute("INSERT INTO users (user_id, role) VALUES (?, 'client')", (user_id,))
            conn.commit()
            role = 'client'
        else:
            role = user[0]

    builder = InlineKeyboardBuilder()
    if role == 'driver':
        builder.button(text="🚖 Navbat panelini ochish", callback_data="open_queue_main")
        builder.button(text="📊 Shaxsiy kabinet", callback_data="driver_cabin")
    else:
        builder.button(text="🚖 Taksi buyurtma qilish", callback_data="client_order")
        builder.button(text="🧑‍✈️ Haydovchi sifatida ro'yxatdan o'tish", callback_data="reg_driver")
    builder.adjust(1)
    
    await message.answer("🚖 **So'xTaxi interaktiv viloyatlararo taksi botiga xush kelibsiz!**\n\nO'zingizga kerakli bo'limni tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_street_passenger")
async def add_street_passenger(call: types.CallbackQuery):
    driver_id = call.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, direction, current_passengers FROM taxi_queue WHERE driver_id = ? AND status = 'waiting'", (driver_id,))
        q_data = cursor.fetchone()
        
        if not q_data:
            await call.answer("⚠️ Siz faol navbatda emassiz!", show_alert=True)
            return
            
        q_id, direction, current_p = q_data
        if current_p >= 4:
            await call.answer("🚗 Mashinangizda joy qolmadi (Maksimum 4)!", show_alert=True)
            return
            
        new_p = current_p + 1
        status = 'completed' if new_p >= 4 else 'waiting'
        
        cursor.execute("UPDATE taxi_queue SET current_passengers = ?, status = ? WHERE id = ?", (new_p, status, q_id))
        conn.commit()
        
    await call.answer("➕ Ko'chadan 1 ta yo'lovchi qo'shildi!")
    
    if status == 'completed':
        await call.message.edit_text("🎉 Mashinangiz to'ldi va navbatdan muvaffaqiyatli chiqdingiz. Oq yo'l!")
        await notify_queue_shift(direction)
    else:
        text, reply_markup = await get_queue_panel_text_and_keyboard(driver_id)
        if text: 
            await call.message.edit_text(text, reply_markup=reply_markup)

@dp.callback_query(F.data == "rem_street_passenger")
async def rem_street_passenger(call: types.CallbackQuery):
    driver_id = call.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_passengers FROM taxi_queue WHERE driver_id = ? AND (status = 'waiting' OR status = 'completed')", (driver_id,))
        q_data = cursor.fetchone()
        
        if not q_data:
            await call.answer("⚠️ Siz faol navbatda emassiz!", show_alert=True)
            return
            
        q_id, current_p = q_data
        if current_p <= 0:
            await call.answer("⚠️ Mashinangiz allaqachon bo'sh!", show_alert=True)
            return
            
        new_p = current_p - 1
        cursor.execute("UPDATE taxi_queue SET current_passengers = ?, status = 'waiting' WHERE id = ?", (new_p, q_id))
        conn.commit()
        
    await call.answer("➖ 1 ta yo'lovchi kamaytirildi!")
    text, reply_markup = await get_queue_panel_text_and_keyboard(driver_id)
    if text: 
        await call.message.edit_text(text, reply_markup=reply_markup)

@dp.callback_query(F.data == "reg_driver")
async def start_driver_reg(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.answer("🧑‍✈️ Profil yaratish uchun to'liq ism-familiyangizni kiriting:")
    await state.set_state(DriverReg.entering_name)

@dp.message(DriverReg.entering_name)
async def process_driver_name(message: types.Message, state: FSMContext):
    await state.update_data(drv_name=message.text)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True))
    await message.answer("📞 Kontaktni ulashing yoki qo'lda kiriting (+998901234567):", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(DriverReg.entering_phone)

@dp.message(DriverReg.entering_phone, F.contact | F.text)
async def process_driver_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(drv_phone=phone)
    await message.answer("🚗 Mashinangiz rusumi va raqami (Masalan: Cobalt, 40 A 777 AA):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(DriverReg.entering_car)

@dp.message(DriverReg.entering_car)
async def process_driver_car(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ?, phone = ?, car_info = ?, role = 'driver' WHERE user_id = ?", (data['drv_name'], data['drv_phone'], message.text, user_id))
        conn.commit()
    await message.answer("🎉 Ro'yxatdan o'tdingiz. /start bosing.")
    await state.clear()

@dp.callback_query(F.data == "client_order")
async def start_client_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    builder = InlineKeyboardBuilder()
    directions = ["Sox-Fer", "Fer-Sox", "Sox-Kok", "Kok-Sox", "Sox-Rish", "Rish-Sox"]
    for d in directions:
        builder.button(text=f"📍 {d.replace('-', ' -> ')}", callback_data=f"dir_{d}")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_start")
    builder.adjust(1)
    await call.message.edit_text("🚖 Qaysi yo'nalish bo'yicha taksi buyurtma qilasiz?", reply_markup=builder.as_markup())
    await state.set_state(OrderTaxi.choosing_direction)

@dp.callback_query(OrderTaxi.choosing_direction, F.data.startswith("dir_"))
async def client_direction_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    direction = call.data.split("_")[1]
    await state.update_data(chosen_direction=direction)
    builder = InlineKeyboardBuilder()
    builder.button(text="👩‍🧕 Ha, ichida ayol bor taksi kerak", callback_data="women_ha")
    builder.button(text="❌ Yo'q, farqi yo'q", callback_data="women_yoq")
    builder.adjust(1)
    
    await call.message.edit_text("🙋‍♀️ **Sizga ichida ayol kishi (yo'lovchi) bor taksi kerakmi?**", reply_markup=builder.as_markup())
    await state.set_state(OrderTaxi.asking_women)

@dp.callback_query(OrderTaxi.asking_women, F.data.startswith("women_"))
async def client_women_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    women_status = call.data.split("_")[1]
    await state.update_data(has_women=women_status)
    
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True))
    builder.row(types.KeyboardButton(text="💬 Telegram lichka orqali bog'lanish (Eski raqam)"))
    
    await call.message.answer(
        "📞 **Bog'lanish usulini tanlang:**\n\n*Agarda Telegram raqamingiz eski bo'lsa yoki yashirilgan bo'lsa, ikkinchi tugmani bosing!*", 
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(OrderTaxi.entering_phone)

@dp.message(OrderTaxi.entering_phone, F.contact | F.text)
async def client_phone_entered(message: types.Message, state: FSMContext):
    client_id = message.from_user.id
    client_name = message.from_user.full_name
    
    if message.contact:
        phone = message.contact.phone_number
    elif "Telegram lichka orqali" in message.text:
        phone = "Telegram lichka orqali"
    else:
        phone = message.text
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ?, name = ? WHERE user_id = ?", (phone, client_name, client_id))
        conn.commit()
        
    # --- YANGI LOKATSIYA SO'RASH QISMI ---
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📍 Lokatsiyamni yuborish", request_location=True))
    await message.answer("📍 **Hozir turgan joyingiz lokatsiyasini yuboring:**\n\n*(Pastdagi 'Lokatsiyamni yuborish' tugmasini bosing)*", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderTaxi.entering_location)

# --- YANGI LOKATSIYANI QABUL QILISH HANDLERI ---
@dp.message(OrderTaxi.entering_location, F.location)
async def client_location_entered(message: types.Message, state: FSMContext):
    client_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?", (lat, lon, client_id))
        conn.commit()
        
    await message.answer("🔢 Nechta joy kerak? (1 dan 4 gacha kiriting):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderTaxi.entering_seats)

@dp.message(OrderTaxi.entering_seats)
async def client_seats_entered(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): 
        await message.answer("⚠️ Faqat raqam kiriting:")
        return
    seats = int(message.text)
    if seats < 1 or seats > 4: 
        await message.answer("⚠️ 1 dan 4 gacha kiriting:")
        return
        
    data = await state.get_data()
    direction = data['chosen_direction']
    women_status = data['has_women']
    client_id = message.from_user.id
    
        # 292-qatordan boshlab quyidagicha almashtiring:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Qidiruvni bekor qilish", callback_data=f"cancel_search_{client_id}")
    
    await message.answer(
        "⏳ **Arizangiz qabul qilindi. Mos haydovchi qidirilmoqda...**\n\n*Agarda rejangiz o'zgarsa, pastdagi tugma orqali arizani qaytarib olishingiz mumkin.*", 
        reply_markup=builder.as_markup()
    )
    await state.clear()
    
    await find_next_driver(direction, seats, women_status, client_id)


@dp.callback_query(F.data == "open_queue_main")
async def open_queue_main(call: types.CallbackQuery):
    await call.answer()
    driver_id = call.from_user.id
    text, reply_markup = await get_queue_panel_text_and_keyboard(driver_id)
    
    if text:
        await call.message.edit_text(text, reply_markup=reply_markup)
    else:
        builder = InlineKeyboardBuilder()
        directions = ["Sox-Fer", "Fer-Sox", "Sox-Kok", "Kok-Sox", "Sox-Rish", "Rish-Sox"]
        for d in directions:
            builder.button(text=d.replace('-', ' -> '), callback_data=f"qdir_{d}")
        builder.button(text="⬅️ Orqaga", callback_data="back_to_driver_main")
        builder.adjust(1)
        await call.message.edit_text("🚖 Siz faol navbatda emassiz. Navbatga turish uchun yo'nalish tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "refresh_queue_panel")
async def refresh_queue_panel(call: types.CallbackQuery):
    driver_id = call.from_user.id
    text, reply_markup = await get_queue_panel_text_and_keyboard(driver_id)
    if text:
        try:
            await call.message.edit_text(text, reply_markup=reply_markup)
            await call.answer("🔄 Yangilandi!")
        except:
            await call.answer("ℹ️ O'zgarish yo'q.")
    else:
        await call.answer("Navbat topilmadi.")
        await open_queue_main(call)

@dp.callback_query(F.data.startswith("qdir_"))
async def driver_queue_direction_chosen(call: types.CallbackQuery):
    await call.answer()
    direction = call.data.split("_")[1]
    builder = InlineKeyboardBuilder()
    builder.button(text="👩‍🧕 Ha, bor", callback_data=f"dw_ha_{direction}")
    builder.button(text="❌ Yo'q", callback_data=f"dw_yoq_{direction}")
    builder.adjust(2)
    await call.message.edit_text("🚗 Mashinangizda hozir ayol yo'lovchilar bormi?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("dw_"))
async def driver_women_status_chosen(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    women_status, direction = parts[1], parts[2]
    driver_id = call.from_user.id
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM taxi_queue WHERE driver_id = ? AND status = 'waiting'", (driver_id,))
        if cursor.fetchone(): 
            await call.message.edit_text("⚠️ Siz allaqachon navbatdasiz!")
            return
        cursor.execute("INSERT INTO taxi_queue (driver_id, direction, has_women, current_passengers, joined_at, status) VALUES (?, ?, ?, 0, ?, 'waiting')", (driver_id, direction, women_status, time.time()))
        conn.commit()
    
    text, reply_markup = await get_queue_panel_text_and_keyboard(driver_id)
    await call.message.edit_text(text, reply_markup=reply_markup)

@dp.callback_query(F.data == "driver_cabin")
async def driver_cabin(call: types.CallbackQuery):
    await call.answer()
    driver_id = call.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, phone, car_info, balance, rating, trips_count FROM users WHERE user_id = ?", (driver_id,))
        drv = cursor.fetchone()
    
    if not drv:
        await call.message.edit_text("Profil topilmadi.")
        return
        
    name, phone, car_info, balance, rating, trips_count = drv
    rating_val = f"{rating:.1f}" if rating else "5.0"
    text = (
        f"📊 **HAYDOVCHINING SHAXSIY KABINETI**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧑‍✈️ **Haydovchi:** {name}\n"
        f"📞 **Tel:** {phone}\n"
        f"🚗 **Mashina:** {car_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Balans:** {balance:,} so'm\n"
        f"⭐️ **Reyting:** {rating_val} / 5.0\n"
        f"📦 **Safarlar soni:** {trips_count} ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"ℹ️ Ma'lumotlarni yangilash uchun adminga yozing."
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Orqaga", callback_data="back_to_driver_main")
    await call.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "leave_queue")
async def leave_queue(call: types.CallbackQuery):
    await call.answer()
    driver_id = call.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT direction FROM taxi_queue WHERE driver_id = ? AND status = 'waiting'", (driver_id,))
        q_data = cursor.fetchone()
        if q_data:
            direction = q_data[0]
            cursor.execute("DELETE FROM taxi_queue WHERE driver_id = ? AND status = 'waiting'", (driver_id,))
            conn.commit()
            await notify_queue_shift(direction)
            
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Bosh sahifa", callback_data="back_to_driver_main")
    await call.message.edit_text("❌ Navbatdan chiqdingiz.", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back_to_driver_main")
async def back_to_driver_main(call: types.CallbackQuery):
    await call.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🚖 Navbat panelini ochish", callback_data="open_queue_main")
    builder.button(text="📊 Shaxsiy kabinet", callback_data="driver_cabin")
    builder.adjust(1)
    await call.message.edit_text("🚖 **Haydovchi boshqaruv paneli**\n\nO'zingizga kerakli bo'limni tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await cmd_start(call.message, state)

# --- LOKATSIYA BILAN YANGILANGAN BOSHING ---
@dp.callback_query(F.data.startswith("ac_"))
async def driver_accept(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    queue_id, client_id, seats, women_status = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
    
    try: 
        await call.message.edit_reply_markup(reply_markup=None)
    except: 
        pass

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT direction, current_passengers, max_passengers, driver_id FROM taxi_queue WHERE id = ?", (queue_id,))
        q_data = cursor.fetchone()
        cursor.execute("SELECT phone, name, latitude, longitude FROM users WHERE user_id = ?", (client_id,))
        c_data = cursor.fetchone()
        
    if not q_data: 
        await call.message.edit_text("⚠️ Buyurtma allaqachon bekor qilingan.")
        return
        
    direction, current_p, max_p, driver_id = q_data
    
    client_phone = c_data[0] if (c_data and c_data[0]) else "Telegram lichka orqali"
    client_name = c_data[1] if (c_data and c_data[1]) else "Yo'lovchi"
    clat = c_data[2] if (c_data and c_data[2]) else None
    clon = c_data[3] if (c_data and c_data[3]) else None
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone, car_info, name FROM users WHERE user_id = ?", (driver_id,))
        d_data = cursor.fetchone()
        
    driver_phone = d_data[0] if d_data else "Noma'lum"
    driver_car = d_data[1] if d_data else "Taksi mashinasi"
    driver_name = d_data[2] if d_data else "Haydovchi"
    
    new_passengers = current_p + seats
    status = 'completed' if new_passengers >= max_p else 'waiting'
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE taxi_queue SET status = ?, current_passengers = ? WHERE id = ?", (status, new_passengers, queue_id))
        cursor.execute("UPDATE users SET trips_count = trips_count + 1 WHERE user_id = ?", (driver_id,))
        cursor.execute("INSERT INTO ride_history (driver_id, client_id, direction, seats, has_women, timestamp, status) VALUES (?, ?, ?, ?, ?, ?, 'accepted')", (driver_id, client_id, direction, seats, women_status, time.time()))
        conn.commit()
        
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Safarni yakunlash", callback_data=f"comp_{queue_id}_{client_id}_{driver_id}")
    builder.button(text="❌ Safarni bekor qilish", callback_data=f"dc_{queue_id}_{client_id}_{seats}")
    builder.button(text="💬 Mijozga yozish (Lichka)", url=f"tg://user?id={client_id}")
    
    # Agar lokatsiya mavjud bo'lsa, xarita tugmasini qo'shamiz
    if clat and clon:
        builder.button(text="📍 Xaritadan yo'lni ko'rish", url=f"https://www.google.com/maps?q={clat},{clon}")
        builder.adjust(1, 1, 1, 1)
    else:
        builder.adjust(1, 1, 1)
    
    await call.message.edit_text(
        text=(
            f"✅ **Buyurtma muvaffaqiyatli qabul qilindi!**\n\n"
            f"🧑‍💼 **Mijoz:** {client_name}\n"
            f"📞 **Tel:** {client_phone}\n"
            f"🔢 **Mashinangizdagi band joylar:** {new_passengers}/{max_p}\n\n"
            f"💬 *Safar tugagach, 'Safarni yakunlash' tugmasini bosing!*"
        ), 
        reply_markup=builder.as_markup()
    )
    
    client_text = (
        f"🎉 **Xushxabar! Buyurtmangiz qabul qilindi!**\n\n"
        f"🧑‍✈️ **Haydovchi:** {driver_name}\n"
        f"🚗 **Mashina:** {driver_car}\n"
        f"📞 **Haydovchi telefoni:** {driver_phone}\n\n"
        f"☝️ *Haydovchi siz bilan tez orada aloqaga chiqadi. Safaringiz bexatar bo'lsin!*"
    )
    
    try: 
        await bot.send_message(chat_id=client_id, text=client_text)
    except Exception as e: 
        print(f"Error client notification: {e}")
    
    if status == 'completed':
        await notify_queue_shift(direction)

@dp.callback_query(F.data.startswith("comp_"))
async def complete_ride(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    queue_id, client_id, driver_id = int(parts[1]), int(parts[2]), int(parts[3])
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM taxi_queue WHERE id = ?", (queue_id,))
        conn.commit()
        
    await call.message.edit_text("🏁 **Safar yakunlandi!** Mijozga yulduzchali baholash paneli yuborildi. Rahmat!")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐", callback_data=f"rate_{driver_id}_1")
    builder.button(text="⭐⭐", callback_data=f"rate_{driver_id}_2")
    builder.button(text="⭐⭐⭐", callback_data=f"rate_{driver_id}_3")
    builder.button(text="⭐⭐⭐⭐", callback_data=f"rate_{driver_id}_4")
    builder.button(text="⭐⭐⭐⭐⭐", callback_data=f"rate_{driver_id}_5")
    builder.adjust(1)
    
    try:
        await bot.send_message(
            chat_id=client_id, 
            text="🏁 **Safarimiz yakunlandi.**\n\nIltimos, haydovchiga xizmatiga qarab quyidagi yulduzchalar orqali baho bering:", 
            reply_markup=builder.as_markup()
        )
    except: 
        pass

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split("_")
    driver_id, stars = int(parts[1]), int(parts[2])
    client_id = call.from_user.id
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ratings_history (driver_id, client_id, stars) VALUES (?, ?, ?)", (driver_id, client_id, stars))
        cursor.execute("SELECT AVG(stars) FROM ratings_history WHERE driver_id = ?", (driver_id,))
        avg_rating = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET rating = ? WHERE user_id = ?", (round(avg_rating, 1), driver_id))
        conn.commit()
        
    await call.message.edit_text(f"❤️ **Bahoingiz uchun rahmat!** Haydovchiga {stars} ta ⭐ qo'ydingiz.")

@dp.callback_query(F.data.startswith("rj_"))
async def driver_reject(call: types.CallbackQuery):
    await call.answer()
    try: 
        await call.message.edit_reply_markup(reply_markup=None)
    except: 
        pass
    parts = call.data.split("_")
    queue_id, client_id, seats, direction = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT driver_id, current_passengers, has_women FROM taxi_queue WHERE id = ?", (queue_id,))
        q_data = cursor.fetchone()
        
    if q_data:
        driver_id, current_p, women_status = q_data
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM taxi_queue WHERE id = ?", (queue_id,))
            cursor.execute("INSERT INTO taxi_queue (driver_id, direction, has_women, current_passengers, joined_at, status) VALUES (?, ?, ?, ?, ?, 'waiting')", (driver_id, direction, women_status, current_p, time.time()))
            conn.commit()
        await call.message.edit_text("❌ Rad etildi. Navbat oxiriga o'tdingiz.")
        
        await notify_queue_shift(direction)
        await find_next_driver(direction, seats, women_status, client_id)

@dp.callback_query(F.data.startswith("dc_"))
async def driver_cancel(call: types.CallbackQuery):
    await call.answer()
    try: 
        await call.message.edit_reply_markup(reply_markup=None)
    except: 
        pass
    parts = call.data.split("_")
    queue_id, client_id, seats = int(parts[1]), int(parts[2]), int(parts[3])
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT driver_id, direction, has_women, current_passengers FROM taxi_queue WHERE id = ?", (queue_id,))
        q_data = cursor.fetchone()
        
    if q_data:
        driver_id, direction, women_status, current_p = q_data
        old_p = max(0, current_p - seats)
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM taxi_queue WHERE id = ?", (queue_id,))
            cursor.execute("INSERT INTO taxi_queue (driver_id, direction, has_women, current_passengers, joined_at, status) VALUES (?, ?, ?, ?, ?, 'waiting')", (driver_id, direction, women_status, old_p, time.time()))
            conn.commit()
            
    await call.message.edit_text("❌ Safar bekor qilindi.")
    try: 
        await bot.send_message(chat_id=client_id, text="⚠️ Haydovchi safarni bekor qildi.")
    except: 
        pass