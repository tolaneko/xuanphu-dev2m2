import asyncio
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
from pathlib import Path
import logging
from keep_alive import keep_alive
keep_alive()

API_TOKEN = "7235634374:AAG9LIwQr6xPJvLF5WxaU3mqjir_S7pUhAc"
ADMIN_IDS = {7527321649}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=pytz.utc)

active_users = {}
vip_users = set()
user_game_choice = {}

# ======== Lưu & Tải dữ liệu =========
def save_activated_users():
    data = {str(uid): expiry.isoformat() for uid, expiry in active_users.items()}
    with open("activated_users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_activated_users():
    path = Path("activated_users.json")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(uid): datetime.fromisoformat(expiry) for uid, expiry in data.items()}
    return {}

def save_vip_users():
    with open("vip_users.json", "w", encoding="utf-8") as f:
        json.dump(list(vip_users), f)

def load_vip_users():
    path = Path("vip_users.json")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

active_users = load_activated_users()
vip_users = load_vip_users()

# ======== Hủy kích hoạt theo hẹn giờ ========
def schedule_deactivation(user_id: int, hours: int):
    run_time = datetime.now(pytz.utc) + timedelta(hours=hours)
    job_id = f"deactivate_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        lambda: asyncio.create_task(deactivate_user(user_id)),
        trigger="date",
        run_date=run_time,
        id=job_id,
        timezone=pytz.utc
    )

async def deactivate_user(user_id: int):
    active_users.pop(user_id, None)
    save_activated_users()
    try:
        await bot.send_message(user_id, "⏰ Thời hạn sử dụng đã hết. Bot của bạn đã bị hủy kích hoạt.")
    except Exception as e:
        logging.error(f"Lỗi khi gửi tin nhắn hủy kích hoạt: {e}")

# ======== Menu Game =========
def game_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="HitClub", callback_data="game_hit"),
         InlineKeyboardButton(text="B52", callback_data="game_b52")],
        [InlineKeyboardButton(text="Luck8", callback_data="game_luck8"),
         InlineKeyboardButton(text="Sumclub", callback_data="game_sum")],
        [InlineKeyboardButton(text="68Gb", callback_data="game_68gb"),
         InlineKeyboardButton(text="Game khác", callback_data="game_khac")]
    ])

# ======== START =========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    now = datetime.now(pytz.utc)
    expiry = active_users.get(uid)

    if uid in vip_users:
        status = "✅ Bot Vip của bạn là VĨNH VIỄN"
    elif expiry and expiry > now:
        status = f"✅ Bot Vip đã được kích hoạt đến {expiry.strftime('%Y-%m-%d %H:%M UTC')}"
    else:
        status = "❌ Bạn chưa được kích hoạt hoặc đã hết hạn. Liên hệ admin để mua thời hạn."

    text = (
        f"🌟 Chào Mừng Đến Với Bot Vip Tài Xỉu MD5 🌟\n"
        f"🆔 ID của bạn: {uid}\n\n"
        f"{status}\n\n"
        "🎲 Chọn một chức năng bên dưới:"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Menu Game", callback_data="menu_game")
    kb.button(text="📅Kiểm Tra Thời Hạn", callback_data="status")
    kb.button(text="📞Liên Hệ Admin", url="https://t.me/Cstooldudoan11")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())

# ======== Lệnh kích hoạt =========
@dp.message(Command("kickhoat"))
async def cmd_kickhoat(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Bạn không có quyền.")
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("❗ Dùng: /kickhoat <user_id> <giờ>")
    user_id, hours = int(parts[1]), int(parts[2])
    expiry = datetime.now(pytz.utc) + timedelta(hours=hours)
    active_users[user_id] = expiry
    save_activated_users()
    schedule_deactivation(user_id, hours)
    await message.reply(f"✅ Đã kích hoạt <code>{user_id}</code> đến {expiry.strftime('%Y-%m-%d %H:%M')}", parse_mode="HTML")
    await bot.send_message(user_id, f"🎉 Bạn đã được kích hoạt đến {expiry.strftime('%Y-%m-%d %H:%M')}")

@dp.message(Command("vip"))
async def cmd_vip(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Bạn không có quyền.")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("❗ Dùng: /vip <user_id>")
    user_id = int(parts[1])
    vip_users.add(user_id)
    save_vip_users()
    active_users.pop(user_id, None)
    save_activated_users()
    await message.reply(f"✅ Đã cấp VIP vĩnh viễn cho <code>{user_id}</code>", parse_mode="HTML")
    await bot.send_message(user_id, "🎉 Bạn đã được cấp quyền sử dụng bot VĨNH VIỄN!")

@dp.message(Command("danhsach"))
async def cmd_danhsach(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Bạn không có quyền.")
    now = datetime.now(pytz.utc)
    lines = ["📋 <b>Danh sách người dùng:</b>"]
    for uid in sorted(vip_users):
        lines.append(f"🔸 <code>{uid}</code> - VIP vĩnh viễn")
    for uid, expiry in active_users.items():
        if expiry > now:
            lines.append(f"🔹 <code>{uid}</code> - hết hạn lúc {expiry.strftime('%Y-%m-%d %H:%M UTC')}")
    await message.reply("\n".join(lines), parse_mode="HTML")

# ======== Callback Game & Status =========
@dp.callback_query(F.data.startswith("game_") | F.data.in_({"menu_game", "status"}))
async def cb_handler(call: CallbackQuery):
    uid = call.from_user.id
    now = datetime.now(pytz.utc)
    expiry = active_users.get(uid)

    if uid not in vip_users and (not expiry or expiry <= now):
        return await call.message.answer("❌ Bạn chưa được kích hoạt hoặc đã hết hạn.")

    if call.data == "menu_game":
        await call.message.answer("🧩 Chọn Cổng Game:", reply_markup=game_menu_keyboard())
    elif call.data == "status":
        if uid in vip_users:
            await call.message.answer("✅ Bạn đang dùng gói VIP VĨNH VIỄN.")
        else:
            await call.message.answer(f"✅ Còn hạn đến {expiry.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        user_game_choice[uid] = call.data
        game_name = {
            "game_hit": "HitClub",
            "game_b52": "B52",
            "game_sum": "Sumclub",
            "game_luck8": "Luck8",
            "game_68gb": "68Gb",
            "game_khac": "Game Khác"
        }.get(call.data, "Không rõ")
        await call.message.answer(f"✅ Bạn đã chọn: <b>{game_name}</b>\n\nGửi mã MD5 để phân tích:", parse_mode="HTML")

# ======== Phân tích MD5 =========
def analyze_md5(md5):
    md5 = md5.lower()
    number = int(md5, 16)
    rolls = [(number >> (i * 16)) & 0xFFFF for i in range(3)]
    dice = [(r % 11) + 2 for r in rolls]
    adjusted = [min(d, 6) for d in dice]
    basic = sum(adjusted)
    basic_result = "Tài" if basic >= 11 else "Xỉu"

    parity = sum(int(md5[i:i+2], 16) for i in range(0, 32, 2))
    parity_result = "Tài" if parity % 2 == 0 else "Xỉu"

    checksum = sum(int(md5[i:i+4], 16) for i in range(0, 32, 4))
    checksum_result = "Tài" if checksum % 3 == 0 else "Xỉu"

    y = number % 100
    final = "Tài" if [basic_result, parity_result, checksum_result].count("Tài") >= 2 else "Xỉu"
    return basic_result, parity_result, checksum_result, round(y, 2), 100 - round(y, 2), final

@dp.message(F.text.regexp(r"^[a-fA-F0-9]{32}$"))
async def md5_handler(message: Message):
    uid = message.from_user.id
    now = datetime.now(pytz.utc)
    if uid not in vip_users and (uid not in active_users or active_users[uid] <= now):
        return await message.reply("❌ Bạn chưa được kích hoạt hoặc đã hết hạn.")

    md5 = message.text.strip()
    basic, parity, checksum, tai_pct, xiu_pct, final = analyze_md5(md5)

    await message.reply(
        f"🏛 <b>KẾT QUẢ PHÂN TÍCH MD5 🏛</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Người dùng: <b>{message.from_user.full_name}</b>\n"
        f"🔐 MD5:<code>{md5}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"[1] TỶ LỆ TỔNG HỢP\n"
        f"📊TÀI: {tai_pct}%\n"
        f"📉XỈU: {xiu_pct}%\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"[2] CHI TIẾT THUẬT TOÁN\n"
        f"├🎲 Basic: {basic}\n"
        f"├♻️ Parity: {parity}\n"
        f"├🈲 Checksum: {checksum}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Gợi ý: NÊN CHỌN “<b>{'TÀI' if tai_pct < xiu_pct else 'XỈU'}</b>”",
        parse_mode="HTML"
    )

# ======== Khởi chạy ========
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
