import telebot
from telebot import types
import sqlite3
import time
import os
from datetime import datetime, timedelta
import pytz
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
TOKEN = '8194183081:AAGvkKKqA6v9QdHpbXVqeSuKIvOPnmWxO0g'
MANAGER_ID = 6901028675
CHANNEL_ID = -1003457348514
CHANNEL_LINK = 'kwizikmetroroyale'
CARD_NUMBER = '4441111161701234'
TON_WALLET = 'UQBvDTcVqQZ82t7EQQeaO0KTuESE6hmNML128PuR4kU61XQD'
KYIV_TZ = pytz.timezone('Europe/Kiev')

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (KEEP-ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQLite) ---
DB_PATH = 'shop_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

init_db()

# --- ЛОГИКА ВРЕМЕНИ ---
def get_detailed_status():
    now = datetime.now(KYIV_TZ)
    day = now.weekday() 
    hour = now.hour
    
    if day == 6:
        return "🔴 *ВЫХОДНОЙ*\n⏳ Откроемся в Пн 09:00", False
    if 9 <= hour < 21:
        until_close = 21 - hour
        return f"🟢 *МАГАЗИН РАБОТАЕТ*\n⏳ До закрытия: {until_close} ч.", True
    else:
        wait = 9 - hour if hour < 9 else (24 - hour) + 9
        return f"🔴 *СЕЙЧАС ЗАКРЫТО*\n⏳ Открытие через {wait} ч.", False

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True 

# --- МЕНЮ ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("😈 СОПРОВОЖДЕНИЕ", callback_data="cat_escort"),
        types.InlineKeyboardButton("🪖 ВЕЩИ / СЕТЫ", callback_data="cat_items"),
        types.InlineKeyboardButton("🔥 БУСТ БАЛИКА", callback_data="cat_boost"),
        types.InlineKeyboardButton("🛡️ ГАРАНТИИ / FUNPAY", callback_data="guarantees"),
        types.InlineKeyboardButton("👨‍💼 МЕНЕДЖЕР", url="https://t.me/NoxDFT")
    )
    return markup

# --- КОМАНДЫ (ТОЛЬКО ДЛЯ ТЕБЯ) ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    add_user(message.chat.id)
    if not is_subscribed(message.from_user.id):
        sub_kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL_LINK}"),
            types.InlineKeyboardButton("🔄 Я подписался", callback_data="sub_check")
        )
        bot.send_message(message.chat.id, "🛑 *ДОСТУП ЗАКРЫТ*\n\nПодпишись на канал!", reply_markup=sub_kb)
        return

    status_msg, _ = get_detailed_status()
    bot.send_message(message.chat.id, f"⚔️ *𝙆𝙒𝙄𝙕𝙄𝙆 𝙈𝙀𝙏𝙍𝙊 𝙎𝙃𝙊𝙋* ⚔️\n━━━━━━━━━━━━━\n{status_msg}\n━━━━━━━━━━━━━", reply_markup=main_menu())

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if message.from_user.id == MANAGER_ID:
        bot.send_message(MANAGER_ID, f"📊 Клиентов в базе: `{len(get_all_users())}`")

@bot.message_handler(commands=['send'])
def send_all(message):
    if message.from_user.id != MANAGER_ID: return
    text = message.text.replace('/send', '').strip()
    if not text: return
    sent, dead = 0, 0
    for u in get_all_users():
        try:
            bot.send_message(u, f"📢 **ОБЪЯВЛЕНИЕ:**\n\n{text}")
            sent += 1
            time.sleep(0.1)
        except: dead += 1
    bot.send_message(MANAGER_ID, f"✅ Доставлено: {sent}\n❌ Мертвых: {dead}")

@bot.message_handler(commands=['sendc'])
def send_channel(message):
    if message.from_user.id != MANAGER_ID: return
    text = message.text.replace('/sendc', '').strip()
    if not text: return
    try:
        bot.send_message(CHANNEL_ID, f"📢 **НОВОСТИ**\n\n{text}")
        bot.send_message(MANAGER_ID, "✅ Отправлено в канал.")
    except Exception as e:
        bot.send_message(MANAGER_ID, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['backup'])
def backup_cmd(message):
    if message.from_user.id == MANAGER_ID:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as f:
                bot.send_document(MANAGER_ID, f, caption="📦 Бэкап базы данных")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    if call.data == "sub_check":
        if is_subscribed(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else: bot.answer_callback_query(call.id, "❌ Нет подписки!", show_alert=True)
    
    elif call.data == "back":
        bot.edit_message_text("Выберите категорию:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data in ["cat_escort", "cat_items", "cat_boost"]:
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("💳 КУПИТЬ", callback_data="pay_action"),
            types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")
        )
        if call.data == "cat_escort":
            txt = "😈 *СОПРОВОЖДЕНИЕ*\n━━━━━━━━━━━━━\n🔥 *7 КАРТА (5М)* — 250₴ / 480₽\n🔥 *7 КАРТА (10М)* — 300₴ / 575₽\n🔥 *8 КАРТА (5М)* — 600₴ / 1150₽\n🏆 *VIP 8 КАРТА* — 800₴ / 1499₽"
        elif call.data == "cat_items":
            txt = "🪖 *СЕТЫ ВЕЩЕЙ*\n━━━━━━━━━━━━━\n🟧 *6 FULL (ST)* — 50₴ / 100₽\n🟦 *6 FULL (SF)* — 60₴ / 120₽\n🟨 *6 FULL (COBRA)* — 70₴ / 140₽"
        else:
            txt = "💎 *БУСТ ВАЛЮТЫ*\n━━━━━━━━━━━━━\n💠 *2.000.000* — 50₴ / 95₽\n💠 *5.000.000* — 60₴ / 115₽\n💠 *7.000.000* — 70₴ / 135₽"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "guarantees":
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👨‍💼 МЕНЕДЖЕР", url="https://t.me/NoxDFT"), types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back"))
        bot.edit_message_text("🛡 *ГАРАНТИИ*\n━━━━━━━━━━━━━\n✅ Возврат при невыполнении.\n💎 Работа через FunPay.", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "pay_action":
        bot.send_message(call.message.chat.id, f"💰 *РЕКВИЗИТЫ*\n\n🇺🇦 *UAH:* `{CARD_NUMBER}`\n🇷🇺 *TON:* `{TON_WALLET}`\n\n📸 Жду скриншот чека!")
    
    bot.answer_callback_query(call.id)

# --- ЧЕКИ ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    _, is_open = get_detailed_status()
    order_num = int(time.time() % 10000)
    msg = f"✅ **Чек принят (Заказ №{order_num})**"
    if not is_open: msg += "\n\n⚠️ Менеджер ответит вам после 09:00."
    bot.reply_to(message, msg)
    
    u_link = f"tg://user?id={message.from_user.id}"
    cap = f"💰 **НОВЫЙ ЗАКАЗ #{order_num}**\n👤 Клиент: @{message.from_user.username or 'Скрыт'}\n🆔 ID: `{message.from_user.id}`\n\n🔗 [НАПИСАТЬ]({u_link})"
    bot.send_photo(MANAGER_ID, message.photo[-1].file_id, caption=cap)

# --- ЗАПУСК ---
if __name__ == "__main__":
    init_db()
    keep_alive() # Запуск веб-сервера
    print("--- БОТ ВКЛЮЧЕН (Render Mode) ---")
    while True:
        try:
            bot.polling(none_stop=True, timeout=120)
        except Exception as e:
            print(f"Reconnect: {e}")
            time.sleep(10)

