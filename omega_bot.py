import asyncio
import logging
import re
import os
import time
import random
import hashlib
import base64
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events, functions, types
from telethon.tl.types import SendMessageTypingAction, SendMessageRecordVideoAction, SendMessageRecordAudioAction, SendMessageGamePlayAction
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.contacts import BlockRequest
from telethon.tl.functions.channels import LeaveChannelRequest

API_ID = 33684592
API_HASH = "4ca8a596e43a3309f3f4cd04d427d3a1"
PHONE_NUMBER = "+989123456789"  # اینجا شماره خودت را با کد کشور وارد کن، مثلاً +989123456789

# دیتابیس
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('omega_self.db')
        self.cursor = self.conn.cursor()
        self._create_tables()
    def _create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS auto_replies (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT UNIQUE, response TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS enemies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS autosave_log (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, file_type TEXT, sender_id INTEGER, saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()
    def add_auto_reply(self, keyword, response):
        self.cursor.execute("INSERT OR REPLACE INTO auto_replies (keyword, response) VALUES (?, ?)", (keyword, response))
        self.conn.commit()
    def delete_auto_reply(self, keyword):
        self.cursor.execute("DELETE FROM auto_replies WHERE keyword = ?", (keyword,))
        self.conn.commit()
    def get_auto_replies(self):
        self.cursor.execute("SELECT keyword, response FROM auto_replies")
        return self.cursor.fetchall()
    def add_enemy(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO enemies (user_id) VALUES (?)", (user_id,))
        self.conn.commit()
    def delete_enemy(self, user_id):
        self.cursor.execute("DELETE FROM enemies WHERE user_id = ?", (user_id,))
        self.conn.commit()
    def get_enemies(self):
        self.cursor.execute("SELECT user_id FROM enemies")
        return [row[0] for row in self.cursor.fetchall()]
    def reset_enemies(self):
        self.cursor.execute("DELETE FROM enemies")
        self.conn.commit()
    def log_autosave(self, file_name, file_type, sender_id):
        self.cursor.execute("INSERT INTO autosave_log (file_name, file_type, sender_id) VALUES (?, ?, ?)", (file_name, file_type, sender_id))
        self.conn.commit()
    def get_autosave_log(self, limit=10):
        self.cursor.execute("SELECT file_name, file_type, sender_id, saved_at FROM autosave_log ORDER BY id DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
db = Database()

client = TelegramClient('omega_session', API_ID, API_HASH)

status = {
    'bot_on': True, 'autosave_on': True, 'lockpv_on': False, 'autochat_on': False,
    'locklink_on': False, 'locktag_on': False, 'mention_on': False,
    'typing_on': False, 'videoaction_on': False, 'audioaction_on': False,
    'gameplay_on': False, 'markread_on': False, 'poker_on': False,
    'timename_on': False, 'timebio_on': False
}

ANIMATIONS = {
    "آدم فضایی": "👽\n🛸\n👾\n🛸\n👽",
    "موشک": "🚀\n🔥\n💥\n🌌\n🚀",
    "پول": "💰\n🔥\n💸\n🔥\n💰",
    "روح": "👻\n💀\n☠️\n👻",
    "عقاب": "🦅\n🎯\n🐇\n🦅",
    "بارون": "☁️\n🌧️\n⚡\n🌊",
    "فوتبال": "⚽\n🥅\n😅",
    "ماشین": "🏎️\n💨\n💥\n🔥\n🏎️",
}

def get_iran_time():
    return datetime.now().astimezone().strftime("%H:%M:%S")

PANEL_BUTTONS = [
    [types.KeyboardButtonCallback("📊 وضعیت", b"status")],
    [types.KeyboardButtonCallback("🎮 سرگرمی", b"fun"), types.KeyboardButtonCallback("⚙️ حالت‌ها", b"actions")],
    [types.KeyboardButtonCallback("🛡️ امنیت", b"security"), types.KeyboardButtonCallback("💾 ذخیره‌سازی", b"autosave")],
    [types.KeyboardButtonCallback("⏰ زمان", b"time"), types.KeyboardButtonCallback("❌ بستن پنل", b"close")],
]

async def update_profile_with_time():
    if status['timename_on'] or status['timebio_on']:
        me = await client.get_me()
        current_time = get_iran_time()
        if status['timename_on']:
            try:
                new_name = f"{me.first_name.split('🕐')[0].strip()} 🕐 {current_time}"
                await client(UpdateProfileRequest(first_name=new_name))
            except:
                pass
        if status['timebio_on']:
            try:
                await client(UpdateProfileRequest(about=f"🕐 {current_time} - OMEGA Self-Bot"))
            except:
                pass

async def time_updater():
    while True:
        await asyncio.sleep(60)
        try:
            await update_profile_with_time()
        except:
            pass

@client.on(events.NewMessage(incoming=True))
async def handle_all_messages(event):
    global status
    if not status['bot_on']:
        return
    msg = event.message
    sender = await event.get_sender()
    if status['lockpv_on'] and event.is_private and not sender.bot:
        if sender.id != (await client.get_me()).id:
            try:
                await client(BlockRequest(id=sender.id))
                await event.reply("🚫 کاربر بلاک شد")
                db.log_autosave(f"blocked_{sender.id}", "block", sender.id)
            except:
                pass
            return
    enemies = db.get_enemies()
    if sender and sender.id in enemies:
        try:
            await event.reply("⚠️ شما در لیست دشمنان هستید!")
        except:
            pass
        return
    if status['locklink_on'] and event.is_group and msg.text:
        if 'http' in msg.text or 'www.' in msg.text or '.com' in msg.text or '.ir' in msg.text:
            try:
                await client.delete_messages(event.chat_id, [msg.id])
                await event.reply("🔗 لینک حذف شد")
            except:
                pass
    if status['locktag_on'] and event.is_group and msg.mentioned:
        try:
            await client.delete_messages(event.chat_id, [msg.id])
            await event.reply("🏷️ تگ حذف شد")
        except:
            pass
    if status['mention_on'] and event.is_group and msg.text and not msg.mentioned and not msg.fwd_from:
        try:
            me = await client.get_me()
            await client.send_message(event.chat_id, f"@{me.username} {msg.text}")
        except:
            pass
    if status['autochat_on'] and msg.text and not msg.mentioned:
        replies = db.get_auto_replies()
        for keyword, response in replies:
            if keyword.lower() in msg.text.lower():
                try:
                    await event.reply(response)
                except:
                    pass
                break
    if status['autosave_on'] and msg.media:
        is_ttl = bool(msg.ttl_seconds)
        no_share = False
        if msg.media and hasattr(msg.media, 'document') and msg.media.document:
            for attr in msg.media.document.attributes:
                if hasattr(attr, 'has_no_share') and attr.has_no_share:
                    no_share = True
                    break
        if is_ttl or no_share:
            try:
                file_path = await client.download_media(msg)
                if file_path:
                    await client.send_file("me", file_path)
                    file_name = os.path.basename(file_path)
                    file_type = "unknown"
                    if msg.photo:
                        file_type = "photo"
                    elif msg.video:
                        file_type = "video"
                    elif msg.voice:
                        file_type = "voice"
                    elif msg.audio:
                        file_type = "audio"
                    elif msg.document:
                        file_type = "document"
                    elif msg.sticker:
                        file_type = "sticker"
                    elif getattr(msg, 'gif', False):
                        file_type = "gif"
                    db.log_autosave(file_name, file_type, sender.id if sender else 0)
                    await event.reply(f"💾 فایل {file_name} ذخیره شد.")
                    try:
                        os.remove(file_path)
                    except:
                        pass
            except Exception as e:
                logging.error(f"خطا: {e}")
    if event.is_private or event.is_group:
        action = None
        if status['typing_on']:
            action = SendMessageTypingAction()
        elif status['videoaction_on']:
            action = SendMessageRecordVideoAction()
        elif status['audioaction_on']:
            action = SendMessageRecordAudioAction()
        elif status['gameplay_on']:
            action = SendMessageGamePlayAction()
        if action:
            try:
                await client(SetTypingRequest(peer=await event.get_input_chat(), action=action))
            except:
                pass
        if status['poker_on'] and msg.text and '😐' in msg.text:
            try:
                await event.reply("😐 پوکر! 😐")
            except:
                pass
    if msg.text and msg.text.startswith('/'):
        cmd_parts = msg.text.split()
        cmd = cmd_parts[0].lower()
        args = ' '.join(cmd_parts[1:]) if len(cmd_parts) > 1 else ''
        if cmd == '/panel':
            await event.reply(
                "🤖 **پنل مدیریت سلف‌بیس OMEGA**\n"
                f"📊 وضعیت: {'✅ روشن' if status['bot_on'] else '❌ خاموش'}\n"
                f"👤 حساب: @{(await client.get_me()).username or 'ندارد'}",
                buttons=PANEL_BUTTONS
            )
        elif cmd == '/start' or cmd == '/help':
            await event.reply("🤖 **راهنما:**\n/panel - پنل مدیریت\n/ping - پینگ\n/bot on/off - روشن/خاموش\n/status - وضعیت\n/timehelp - راهنمای زمان\n/actionshelp - راهنمای حالت‌ها\n/spamhelp - راهنمای اسپم\n/answerhelp - راهنمای پاسخ خودکار\n/enemyhelp - راهنمای دشمن")
        elif cmd == '/timehelp':
            await event.reply("/timename on/off - ساعت در اسم\n/timebio on/off - ساعت در بیو")
        elif cmd == '/actionshelp':
            await event.reply("/typing on/off - تایپ\n/videoaction on/off - ضبط ویدیو\n/audioaction on/off - ضبط صدا\n/gameplay on/off - بازی\n/poker on/off - پوکر\n/lockpv on/off - بلاک پیوی\n/autochat on/off - پاسخ خودکار\n/autosave on/off - ذخیره‌سازی خودکار")
        elif cmd == '/spamhelp':
            await event.reply("/spam تعداد متن - ارسال مکرر\n/flood تعداد متن - اسپم در یک پیام")
        elif cmd == '/answerhelp':
            await event.reply("/setanswer کلمه|پاسخ - تنظیم پاسخ خودکار\n/delanswer کلمه - حذف\n/answerlist - لیست پاسخ‌ها")
        elif cmd == '/enemyhelp':
            await event.reply("/setenemy [ریپلی] - افزودن دشمن\n/delenemy [ریپلی] - حذف\n/reset enemylist - پاکسازی")
        elif cmd == '/bot':
            if args == 'on':
                status['bot_on'] = True
                await event.reply("✅ ربات روشن شد")
            elif args == 'off':
                status['bot_on'] = False
                await event.reply("⛔ ربات خاموش شد")
            else:
                await event.reply("❌ استفاده: /bot on یا /bot off")
        elif cmd == '/restart':
            await event.reply("🔄 در حال ریستارت...")
            os._exit(0)
        elif cmd == '/ping':
            start = time.time()
            await client.send_message(event.chat_id, "🏓 پینگ...")
            end = time.time()
            await event.reply(f"🏓 پینگ: {(end-start)*1000:.2f} ms")
        elif cmd == '/status':
            await event.reply(f"📊 **وضعیت:**\nربات: {'روشن' if status['bot_on'] else 'خاموش'}\nautosave: {'فعال' if status['autosave_on'] else 'غیرفعال'}\nlockpv: {'فعال' if status['lockpv_on'] else 'غیرفعال'}\nautochat: {'فعال' if status['autochat_on'] else 'غیرفعال'}\nlocklink: {'فعال' if status['locklink_on'] else 'غیرفعال'}\nlocktag: {'فعال' if status['locktag_on'] else 'غیرفعال'}\nmention: {'فعال' if status['mention_on'] else 'غیرفعال'}")
        elif cmd == '/timename':
            status['timename_on'] = args == 'on'
            await event.reply(f"✅ ساعت در اسم {'فعال' if status['timename_on'] else 'غیرفعال'} شد")
            await update_profile_with_time()
        elif cmd == '/timebio':
            status['timebio_on'] = args == 'on'
            await event.reply(f"✅ ساعت در بیو {'فعال' if status['timebio_on'] else 'غیرفعال'} شد")
            await update_profile_with_time()
        elif cmd == '/typing':
            status['typing_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['typing_on'] else 'غیرفعال'} شد")
        elif cmd == '/videoaction':
            status['videoaction_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['videoaction_on'] else 'غیرفعال'} شد")
        elif cmd == '/audioaction':
            status['audioaction_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['audioaction_on'] else 'غیرفعال'} شد")
        elif cmd == '/gameplay':
            status['gameplay_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['gameplay_on'] else 'غیرفعال'} شد")
        elif cmd == '/poker':
            status['poker_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['poker_on'] else 'غیرفعال'} شد")
        elif cmd == '/lockpv':
            status['lockpv_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['lockpv_on'] else 'غیرفعال'} شد")
        elif cmd == '/autochat':
            status['autochat_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['autochat_on'] else 'غیرفعال'} شد")
        elif cmd == '/autosave':
            status['autosave_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['autosave_on'] else 'غیرفعال'} شد")
        elif cmd == '/locklink':
            status['locklink_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['locklink_on'] else 'غیرفعال'} شد")
        elif cmd == '/locktag':
            status['locktag_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['locktag_on'] else 'غیرفعال'} شد")
        elif cmd == '/mention':
            status['mention_on'] = args == 'on'
            await event.reply(f"✅ {'فعال' if status['mention_on'] else 'غیرفعال'} شد")
        elif cmd == '/setanswer':
            if '|' in args:
                k, r = args.split('|', 1)
                db.add_auto_reply(k.strip(), r.strip())
                await event.reply(f"✅ پاسخ برای '{k.strip()}' تنظیم شد")
            else:
                await event.reply("❌ استفاده: /setanswer کلمه|پاسخ")
        elif cmd == '/delanswer':
            if args:
                db.delete_auto_reply(args)
                await event.reply(f"✅ پاسخ برای '{args}' حذف شد")
            else:
                await event.reply("❌ استفاده: /delanswer کلمه")
        elif cmd == '/answerlist':
            replies = db.get_auto_replies()
            if replies:
                text = "📋 لیست پاسخ‌ها:\n" + "\n".join([f"🔹 {k} → {r}" for k, r in replies])
                await event.reply(text)
            else:
                await event.reply("❌ هیچ پاسخی تنظیم نشده")
        elif cmd == '/setenemy':
            if msg.reply_to_msg_id:
                reply = await client.get_messages(event.chat_id, ids=msg.reply_to_msg_id)
                if reply and reply.sender_id:
                    db.add_enemy(reply.sender_id)
                    await event.reply(f"✅ کاربر {reply.sender_id} اضافه شد")
            elif args.isdigit():
                db.add_enemy(int(args))
                await event.reply(f"✅ کاربر {args} اضافه شد")
            else:
                await event.reply("❌ یک پیام را ریپلی کنید")
        elif cmd == '/delenemy':
            if msg.reply_to_msg_id:
                reply = await client.get_messages(event.chat_id, ids=msg.reply_to_msg_id)
                if reply and reply.sender_id:
                    db.delete_enemy(reply.sender_id)
                    await event.reply(f"✅ کاربر {reply.sender_id} حذف شد")
            elif args.isdigit():
                db.delete_enemy(int(args))
                await event.reply(f"✅ کاربر {args} حذف شد")
            else:
                await event.reply("❌ یک پیام را ریپلی کنید")
        elif cmd == '/reset' and args == 'enemylist':
            db.reset_enemies()
            await event.reply("✅ لیست دشمنان پاکسازی شد")
        elif cmd == '/spam':
            parts = args.split(' ', 1)
            if len(parts) == 2 and parts[0].isdigit():
                for _ in range(min(int(parts[0]), 20)):
                    await client.send_message(event.chat_id, parts[1])
                    await asyncio.sleep(0.5)
                await event.reply(f"✅ {parts[0]} پیام ارسال شد")
            else:
                await event.reply("❌ استفاده: /spam تعداد متن")
        elif cmd == '/flood':
            parts = args.split(' ', 1)
            if len(parts) == 2 and parts[0].isdigit():
                text = (parts[1] + ' ') * int(parts[0])
                await event.reply(text[:4000])
            else:
                await event.reply("❌ استفاده: /flood تعداد متن")
    elif msg.text and msg.text in ANIMATIONS:
        await event.reply(ANIMATIONS[msg.text])

@client.on(events.CallbackQuery)
async def handle_panel_callbacks(event):
    data = event.data.decode()
    if data == "status":
        await event.answer(f"ربات: {'روشن' if status['bot_on'] else 'خاموش'}\nautosave: {'فعال' if status['autosave_on'] else 'غیرفعال'}", alert=True)
    elif data == "fun":
        await event.edit("🎮 منوی سرگرمی", buttons=[[types.KeyboardButtonCallback("🔙 بازگشت", b"panel")]])
    elif data == "actions":
        await event.edit("⚙️ حالت‌ها", buttons=[
            [types.KeyboardButtonCallback(f"⌨️ تایپ: {'✅' if status['typing_on'] else '❌'}", b"toggle_typing")],
            [types.KeyboardButtonCallback(f"🎥 ویدیو: {'✅' if status['videoaction_on'] else '❌'}", b"toggle_videoaction")],
            [types.KeyboardButtonCallback(f"🎤 صدا: {'✅' if status['audioaction_on'] else '❌'}", b"toggle_audioaction")],
            [types.KeyboardButtonCallback(f"🎮 بازی: {'✅' if status['gameplay_on'] else '❌'}", b"toggle_gameplay")],
            [types.KeyboardButtonCallback(f"😐 پوکر: {'✅' if status['poker_on'] else '❌'}", b"toggle_poker")],
            [types.KeyboardButtonCallback("🔙 بازگشت", b"panel")],
        ])
    elif data == "security":
        await event.edit("🛡️ امنیت", buttons=[
            [types.KeyboardButtonCallback(f"🔒 lockpv: {'✅' if status['lockpv_on'] else '❌'}", b"toggle_lockpv")],
            [types.KeyboardButtonCallback(f"🔗 locklink: {'✅' if status['locklink_on'] else '❌'}", b"toggle_locklink")],
            [types.KeyboardButtonCallback(f"🏷️ locktag: {'✅' if status['locktag_on'] else '❌'}", b"toggle_locktag")],
            [types.KeyboardButtonCallback(f"📢 mention: {'✅' if status['mention_on'] else '❌'}", b"toggle_mention")],
            [types.KeyboardButtonCallback(f"💬 autochat: {'✅' if status['autochat_on'] else '❌'}", b"toggle_autochat")],
            [types.KeyboardButtonCallback("🔙 بازگشت", b"panel")],
        ])
    elif data == "autosave":
        logs = db.get_autosave_log(5)
        log_text = "\n".join([f"{l[3]}: {l[0]} ({l[1]})" for l in logs]) if logs else "هیچ"
        await event.edit(f"💾 autosave: {'✅' if status['autosave_on'] else '❌'}\n\n{log_text}", buttons=[
            [types.KeyboardButtonCallback(f"🔄 تغییر", b"toggle_autosave")],
            [types.KeyboardButtonCallback("🔙 بازگشت", b"panel")],
        ])
    elif data == "time":
        await event.edit("⏰ زمان", buttons=[
            [types.KeyboardButtonCallback(f"🕐 اسم: {'✅' if status['timename_on'] else '❌'}", b"toggle_timename")],
            [types.KeyboardButtonCallback(f"🕐 بیو: {'✅' if status['timebio_on'] else '❌'}", b"toggle_timebio")],
            [types.KeyboardButtonCallback("🔙 بازگشت", b"panel")],
        ])
    elif data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        if key in status:
            status[key] = not status[key]
            await event.answer(f"✅ {key} {'فعال' if status[key] else 'غیرفعال'} شد")
            await handle_panel_callbacks(event)
    elif data == "panel":
        await event.edit(
            "🤖 **پنل مدیریت**\n"
            f"وضعیت: {'✅ روشن' if status['bot_on'] else '❌ خاموش'}",
            buttons=PANEL_BUTTONS
        )
    elif data == "close":
        await event.delete()
        await client.send_message(event.chat_id, "❌ پنل بسته شد.")

async def main():
    await client.start(phone=PHONE_NUMBER)
    me = await client.get_me()
    print(f"✅ وارد شدید: {me.first_name}")
    await client.send_message("me", "🤖 سلف‌بیس OMEGA راه‌اندازی شد!")
    asyncio.create_task(time_updater())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
