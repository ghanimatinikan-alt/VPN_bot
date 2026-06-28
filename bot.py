import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "")
CARD_OWNER = os.environ.get("CARD_OWNER", "")

PLANS = {
    "plan_10": {"name": "۱۰ گیگ", "price": "۳۵,۰۰۰ تومان", "config": "PLAN_10"},
    "plan_20": {"name": "۲۰ گیگ", "price": "۶۰,۰۰۰ تومان", "config": "PLAN_20"},
    "plan_50": {"name": "۵۰ گیگ", "price": "۱۲۰,۰۰۰ تومان", "config": "PLAN_50"},
    "plan_100": {"name": "۱۰۰ گیگ", "price": "۲۰۰,۰۰۰ تومان", "config": "PLAN_100"},
    "plan_unlimited": {"name": "نامحدود ۳۰ روزه", "price": "۲۸۰,۰۰۰ تومان", "config": "PLAN_UNL"},
}

CONFIGS = {
    "PLAN_10": "کانفیگ ۱۰ گیگ رو اینجا بذار",
    "PLAN_20": "کانفیگ ۲۰ گیگ رو اینجا بذار",
    "PLAN_50": "کانفیگ ۵۰ گیگ رو اینجا بذار",
    "PLAN_100": "کانفیگ ۱۰۰ گیگ رو اینجا بذار",
    "PLAN_UNL": "کانفیگ نامحدود رو اینجا بذار",
}

WAIT_RECEIPT = 1

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🛒 خرید VPN", callback_data="buy")],
          [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]]
    await update.message.reply_text("🔒 *فروشگاه VPN*\n\nاز منوی زیر انتخاب کن:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def show_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[InlineKeyboardButton(f"📦 {p['name']} — {p['price']}", callback_data=f"select_{pid}")] for pid, p in PLANS.items()]
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    await query.edit_message_text("📦 *پلن‌های موجود:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def select_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = query.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        return ConversationHandler.END
    ctx.user_data["selected_plan"] = plan_id
    kb = [[InlineKeyboardButton("✅ پرداخت کردم", callback_data="paid")],
          [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")]]
    await query.edit_message_text(
        f"✅ *{plan['name']}*\n\n💰 *مبلغ:* `{plan['price']}`\n\n💳 *شماره کارت:*\n`{CARD_NUMBER}`\n👤 *به نام:* {CARD_OWNER}\n\nبعد از واریز دکمه زیر رو بزن:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return WAIT_RECEIPT

async def ask_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📸 *رسید پرداختت رو بفرست:*", parse_mode="Markdown")
    return WAIT_RECEIPT

async def receive_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    plan_id = ctx.user_data.get("selected_plan", "")
    plan = PLANS.get(plan_id, {})
    await update.message.reply_text("⏳ رسیدت دریافت شد! بعد از تایید ادمین کانفیگ برات ارسال میشه 🙏")
    caption = f"🔔 *سفارش جدید*\n👤 {user.full_name}\n🆔 `{user.id}`\n📦 {plan.get('name','')}\n💰 {plan.get('price','')}"
    kb = [[InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user.id}_{plan_id}"),
           InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")]]
    if update.message.photo:
        await
