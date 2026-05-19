from aiogram.fsm.state import State, StatesGroup

class OrderTaxi(StatesGroup):
    choosing_direction = State()
    asking_women = State()
    entering_phone = State()
    entering_location = State() # <-- Yangi qo'shildi
    entering_seats = State()

class DriverReg(StatesGroup):
    entering_name = State()
    entering_phone = State()
    entering_car = State()
