import os
import telebot
from telebot import types
import sqlite3
from threading import Thread
from flask import Flask

# خادم وهمي لتخطي نظام النوم في الاستضافات المجانية
app = Flask('')
@app.route('/')
def home(): return "Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# البيانات الأساسية
API_TOKEN = '8727769058:AAGYoFmVGWQZppXe3MnVmg5Z4tG-VhcDsZU'
ADMIN_ID = 5878987183  # تم تصحيح الفاصلة هنا
CHANNEL_ID = -1003592174466 
CHANNEL_USER = "@NOLOORD"    
START_IMG = ""

bot = telebot.TeleBot(API_TOKEN)

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER, invited_by INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, user TEXT, password TEXT, location TEXT, price INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, price INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('tut_price', '0')")
    conn.commit()
    conn.close()

init_db()

# --- وظائف المساعدة ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def get_bot_status():
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='bot_status'")
    res = c.fetchone(); conn.close()
    return res[0] if res else 'on'

def get_user(user_id):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT points FROM users WHERE id=?", (user_id,))
    res = c.fetchone(); conn.close()
    return res if res else (0,)

def add_points(user_id, amount):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("UPDATE users SET points = points + ? WHERE id=?", (amount, user_id))
    conn.commit(); conn.close()

# --- الكيبورد الرئيسي ---
def main_markup(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btns = [
        types.KeyboardButton("🚀 خادم كبير"), types.KeyboardButton("🛰️ خادم صغير"),
        types.KeyboardButton("🔗 رابط الموقع"), types.KeyboardButton("👤 حسابي"),
        types.KeyboardButton("🎁 رابط الدعوة"), types.KeyboardButton("💰 شراء نقاط"), 
        types.KeyboardButton("📖 الشرح")
    ]
    markup.add(*btns)
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("🛠️ لوحة الأدمن"))
    return markup

def send_sub_msg(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("اشترك هنا 🔗", url=f"https://t.me/{CHANNEL_USER[1:]}"))
    markup.add(types.InlineKeyboardButton("تـحـقـق ✅", callback_data="check_sub"))
    bot.send_message(chat_id, f"يجب عليك الاشتراك في القناة أولاً:\n{CHANNEL_USER}", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        send_sub_msg(message.chat.id)
        return

    args = message.text.split()
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not c.fetchone():
        invited_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        c.execute("INSERT INTO users (id, points, invited_by) VALUES (?, ?, ?)", (user_id, 0, invited_by))
        conn.commit()
        if invited_by:
            add_points(invited_by, 1)
            try: bot.send_message(invited_by, "✅ انضم مستخدم جديد عبر رابطك وحصلت على 1 نقطة!")
            except: pass
    conn.close()
    
    if START_IMG:
        try: bot.send_photo(message.chat.id, START_IMG, caption="أهلاً بك في نظام المتجر المطور 🚀", reply_markup=main_markup(user_id))
        except: bot.send_message(message.chat.id, "أهلاً بك في نظام المتجر المطور 🚀", reply_markup=main_markup(user_id))
    else:
        bot.send_message(message.chat.id, "أهلاً بك في نظام المتجر المطور 🚀", reply_markup=main_markup(user_id))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        send_sub_msg(message.chat.id)
        return

    status = get_bot_status()
    if status == 'off' and user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ البوت مغلق حالياً للإصلاح.")
        return

    if message.text == "🚀 خادم كبير": show_one_server(message.chat.id, "big", 0)
    elif message.text == "🛰️ خادم صغير": show_one_server(message.chat.id, "small", 0)
    elif message.text == "🔗 رابط الموقع": show_one_site(message.chat.id, 0)
    elif message.text == "👤 حسابي":
        res = get_user(user_id)
        bot.send_message(message.chat.id, f"🆔 أيديك: `{user_id}`\n💰 نقاطك: {res[0]}", parse_mode="Markdown")
    elif message.text == "🎁 رابط الدعوة":
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={user_id}"
        bot.send_message(message.chat.id, f"رابط دعوتك للحصول على نقاط:\n`{link}`", parse_mode="Markdown")
    elif message.text == "💰 شراء نقاط":
        bot.send_message(message.chat.id, "لشراء النقاط تواصل مع الإدارة: @O11O80")
    
    elif message.text == "📖 الشرح":
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key='tut_price'")
        price = int(c.fetchone()[0])
        c.execute("SELECT value FROM settings WHERE key='tutorial_id'")
        tut_id = c.fetchone()
        conn.close()
        
        if not tut_id:
            bot.send_message(message.chat.id, "لا يوجد شرح متوفر حالياً.")
            return
            
        if price == 0 or user_id == ADMIN_ID:
            bot.copy_message(message.chat.id, ADMIN_ID, int(tut_id[0]))
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"✅ دفع {price} نقطة للمشاهدة", callback_data="buy_tutorial"))
            bot.send_message(message.chat.id, f"📖 هذا الشرح مدفوع.\nسعر المشاهدة: {price} نقطة.", reply_markup=markup)

    elif message.text == "🛠️ لوحة الأدمن" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ سيرفر", callback_data="add_srv"), 
                   types.InlineKeyboardButton("➕ موقع (ثابت)", callback_data="add_site"))
        markup.add(types.InlineKeyboardButton("📝 وضع الشرح والأسعار", callback_data="add_tut_flow"))
        markup.add(types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast"))
        markup.add(types.InlineKeyboardButton("💎 شحن مستخدم", callback_data="gift_points"),
                   types.InlineKeyboardButton("🔒/🔓 حالة البوت", callback_data="toggle_bot"))
        bot.send_message(message.chat.id, "لوحة التحكم جاسم:", reply_markup=markup)

# --- أنظمة العرض ---
def show_one_server(chat_id, s_type, index, message_id=None):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT id, price FROM servers WHERE type=?", (s_type,))
    rows = c.fetchall(); conn.close()
    if not rows:
        bot.send_message(chat_id, "عذراً، لا توجد خوادم متاحة.")
        return
    if index >= len(rows): index = 0
    row = rows[index]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"✅ شراء ({row[1]} نقطة)", callback_data=f"buy_srv_{row[0]}"))
    if len(rows) > 1: markup.add(types.InlineKeyboardButton("➡️ التالي", callback_data=f"next_srv_{s_type}_{index+1}"))
    text = f"🌐 خادم {s_type} متاح\nالسعر: {row[1]} نقطة"
    if message_id:
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except: pass
    else: bot.send_message(chat_id, text, reply_markup=markup)

def show_one_site(chat_id, index, message_id=None):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT id, price FROM sites"); rows = c.fetchall(); conn.close()
    if not rows:
        bot.send_message(chat_id, "لا توجد مواقع متاحة حالياً."); return
    if index >= len(rows): index = 0
    row = rows[index]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"✅ شراء الرابط ({row[1]} نقطة)", callback_data=f"buy_site_{row[0]}"))
    if len(rows) > 1: markup.add(types.InlineKeyboardButton("➡️ التالي", callback_data=f"next_site_{index+1}"))
    text = f"🔗 رابط موقع متاح كمنتج ثابت\nالسعر: {row[1]} نقطة"
    if message_id:
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except: pass
    else: bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "check_sub":
        if is_subscribed(user_id):
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            if START_IMG:
                try: bot.send_photo(call.message.chat.id, START_IMG, caption="✅ تم التحقق!", reply_markup=main_markup(user_id))
                except: bot.send_message(call.message.chat.id, "✅ تم التحقق!", reply_markup=main_markup(user_id))
            else:
                bot.send_message(call.message.chat.id, "✅ تم التحقق!", reply_markup=main_markup(user_id))
        else: bot.answer_callback_query(call.id, "❌ لم تشترك بعد!", show_alert=True)
    
    elif call.data == "buy_tutorial":
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key='tut_price'")
        price = int(c.fetchone()[0])
        c.execute("SELECT value FROM settings WHERE key='tutorial_id'")
        tut_id = int(c.fetchone()[0])
        
        user_res = get_user(user_id)
        if user_res[0] < price:
            bot.answer_callback_query(call.id, "نقاطك غير كافية لشراء الشرح!", show_alert=True)
        else:
            c.execute("UPDATE users SET points = points - ? WHERE id=?", (price, user_id))
            conn.commit()
            bot.copy_message(user_id, ADMIN_ID, tut_id)
            bot.answer_callback_query(call.id, "تم شراء الشرح بنجاح ✅")
        conn.close()

    elif call.data.startswith("buy_srv_"):
        srv_id = call.data.split("_")[2]
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT user, password, location, price FROM servers WHERE id=?", (srv_id,))
        srv = c.fetchone()
        if srv:
            user_res = get_user(user_id)
            if user_res[0] < srv[3]: bot.answer_callback_query(call.id, "نقاطك غير كافية!", show_alert=True)
            else:
                c.execute("UPDATE users SET points = points - ? WHERE id=?", (srv[3], user_id))
                c.execute("DELETE FROM servers WHERE id=?", (srv_id,))
                conn.commit()
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot.send_message(user_id, f"✅ تم شراء السيرفر:\n👤 يوزر: `{srv[0]}`\n🔑 باسورد: `{srv[1]}`\n📍 الموقع: {srv[2]}", parse_mode="Markdown")
        conn.close()

    elif call.data.startswith("buy_site_"):
        site_id = call.data.split("_")[2]
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT url, price FROM sites WHERE id=?", (site_id,))
        site = c.fetchone()
        if site:
            user_res = get_user(user_id)
            if user_res[0] < site[1]: bot.answer_callback_query(call.id, "نقاطك غير كافية!", show_alert=True)
            else:
                c.execute("UPDATE users SET points = points - ? WHERE id=?", (site[1], user_id))
                conn.commit()
                bot.send_message(user_id, f"✅ تم شراء الرابط الثابت:\n\n🔗 {site[0]}")
        conn.close()

    elif call.data == "add_tut_flow" and user_id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "1️⃣ أرسل الآن محتوى الشرح (فيديو، صورة، ملف، أو نص):")
        bot.register_next_step_handler(msg, save_tut_content)

    elif call.data == "add_srv" and user_id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "أرسل بيانات السيرفر (5 أسطر):\nالنوع\nاليوزر\nالباسورد\nالرابط\nالسعر")
        bot.register_next_step_handler(msg, save_srv)

    elif call.data == "add_site" and user_id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "أرسل بيانات الموقع الثابت (سطرين):\nالرابط\nالسعر")
        bot.register_next_step_handler(msg, save_site)

    elif call.data == "broadcast" and user_id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "أرسل رسالة الإذاعة:")
        bot.register_next_step_handler(msg, start_broadcast)

    elif call.data == "gift_points" and user_id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "أرسل: الأيدي [مسافة] النقاط")
        bot.register_next_step_handler(msg, save_gift)

    elif call.data == "toggle_bot" and user_id == ADMIN_ID:
        status = 'off' if get_bot_status() == 'on' else 'on'
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("UPDATE settings SET value=? WHERE key='bot_status'", (status,)); conn.commit(); conn.close()
        bot.answer_callback_query(call.id, f"الحالة: {status}")

# --- وظائف الحفظ الخاصة بالأدمن ---
def save_tut_content(message):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('tutorial_id', ?)", (message.message_id,))
    conn.commit(); conn.close()
    msg = bot.send_message(message.chat.id, "2️⃣ تم حفظ المحتوى. الآن أرسل **سعر مشاهدة هذا الشرح** (مثلاً: 50) أو 0 ليكون مجانياً:")
    bot.register_next_step_handler(msg, save_tut_price)

def save_tut_price(message):
    try:
        price = int(''.join(filter(str.isdigit, message.text)))
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('tut_price', ?)", (str(price),))
        conn.commit(); conn.close()
        bot.send_message(message.chat.id, f"✅ تم تحديث الشرح بنجاح!\nالمحتوى محفوظ والسعر هو: {price} نقطة.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في السعر. يرجى إرسال أرقام فقط.")

def save_srv(message):
    try:
        data = message.text.split("\n")
        s_type = "big" if "كبير" in data[0] else "small"
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("INSERT INTO servers (type, user, password, location, price) VALUES (?, ?, ?, ?, ?)", 
                  (s_type, data[1], data[2], data[3], int(''.join(filter(str.isdigit, data[4])))))
        conn.commit(); conn.close(); bot.send_message(message.chat.id, "✅ تم حفظ السيرفر.")
    except: bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

def save_site(message):
    try:
        data = message.text.split("\n")
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("INSERT INTO sites (url, price) VALUES (?, ?)", (data[0], int(''.join(filter(str.isdigit, data[1])))))
        conn.commit(); conn.close(); bot.send_message(message.chat.id, "✅ تم حفظ الموقع الثابت.")
    except: bot.send_message(message.chat.id, "❌ خطأ!")

def start_broadcast(message):
    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT id FROM users"); users = c.fetchall(); conn.close()
    success_count = 0
    for user in users:
        try: 
            bot.copy_message(user[0], message.chat.id, message.message_id)
            success_count += 1
        except: 
            pass
    bot.send_message(message.chat.id, f"✅ تمت الإذاعة بنجاح!\n\n👥 تم الإرسال إلى: {success_count} مستخدم.")

def save_gift(message):
    try:
        uid, pts = message.text.split()
        add_points(int(uid), int(pts)); bot.send_message(message.chat.id, "✅ تم شحن المستخدم.")
    except: bot.send_message(message.chat.id, "❌ خطأ في الصيغة.")

if __name__ == '__main__':
    # تشغيل خادم الويب في خلفية منفصلة
    Thread(target=run_flask).start()
    # تشغيل البوت
    bot.infinity_polling()
