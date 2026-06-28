import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "")
CARD_OWNER = os.environ.get("CARD_OWNER", "")
SUPPORT_USERNAME = "@n8ikan"

PLANS = {
    "p30":  {"name": "30 گیگ",  "label": "30 گیگ (کاربر و زمان نامحدود) 🟢", "price": 180000},
    "p50":  {"name": "50 گیگ",  "label": "50 گیگ (کاربر و زمان نامحدود) 🟢", "price": 250000},
    "p70":  {"name": "70 گیگ",  "label": "70 گیگ (کاربر و زمان نامحدود) 🟢", "price": 385000},
    "p100": {"name": "100 گیگ", "label": "100 گیگ (کاربر و زمان نامحدود) 🟢", "price": 400000},
    "p150": {"name": "150 گیگ", "label": "150 گیگ (کاربر و زمان نامحدود) 🟢", "price": 600000},
}

DISCOUNT_CODES = {
    "094405": "free",
    "Ahnp": {
        "p30": 120000,
        "p50": 200000,
        "p70": 280000,
        "p100": 400000,
        "p150": 600000,
    }
}

ORDERS_FILE = "orders.json"
WAIT_RECEIPT = 1
WAIT_DISCOUNT = 2

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_orders(orders):
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def format_price(amount):
    return f"{amount:,} تومان".replace(",", "،")

async def start(update, ctx):
    kb = [
        [InlineKeyboardButton("🛒 خرید بسته", callback_data="buy")],
        [InlineKeyboardButton("📦 بسته های من", callback_data="myorders")],
        [InlineKeyboardButton("🎫 کد تخفیف", callback_data="discount")],
        [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")],
    ]
    text = (
        "🔒 *به فروشگاه VPN خوش اومدی!*\n\n"
        "اینترنت آزاد، سریع و بدون محدودیت 🚀\n"
        "از منوی زیر گزینه مورد نظرت رو انتخاب کن 👇"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def show_plans(update, ctx):
    q = update.callback_query
    await q.answer()
    discount = ctx.user_data.get("discount", None)
    kb = []
    for pid, p in PLANS.items():
        if discount == "free":
            label = p["label"] + " - 🎁 رایگان"
        elif isinstance(discount, dict) and pid in discount:
            label = p["label"] + f" - {format_price(discount[pid])}"
        else:
            label = p["label"] + f" - {format_price(p['price'])}"
        kb.append([InlineKeyboardButton(label, callback_data=f"select_{pid}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    await q.edit_message_text(
        "📦 *بسته های موجود:*\n\nیه بسته انتخاب کن 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def select_plan(update, ctx):
    q = update.callback_query
    await q.answer()
    plan_id = q.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        return ConversationHandler.END
    ctx.user_data["plan_id"] = plan_id
    discount = ctx.user_data.get("discount", None)

    if discount == "free":
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="buy")]]
        await q.edit_message_text(
            f"🎁 *بسته {plan['name']} برای شما رایگانه!*\n\n"
            f"✅ سفارش شما ثبت شد.\n"
            f"به زودی کانفیگ توسط ادمین برات ارسال میشه 🙏\n\n"
            f"⏱ زمان تحویل: معمولاً کمتر از ۳۰ دقیقه",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        user = update.effective_user
        kb_admin = [[
            InlineKeyboardButton("✅ ارسال کانفیگ", callback_data=f"approve_{user.id}_{plan_id}"),
            InlineKeyboardButton("❌ رد کردن", callback_data=f"reject_{user.id}"),
        ]]
        await q.get_bot().send_message(
            ADMIN_ID,
            f"🔔 *سفارش رایگان جدید!*\n\n"
            f"👤 نام: {user.full_name}\n"
            f"🆔 آیدی: `{user.id}`\n"
            f"📦 بسته: {plan['name']}\n"
            f"🎫 کد تخفیف: رایگان (094405)\n\n"
            f"برای ارسال کانفیگ دکمه زیر رو بزن 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb_admin)
        )
        return ConversationHandler.END

    if isinstance(discount, dict) and plan_id in discount:
        price_text = format_price(discount[plan_id])
        discount_note = f"🎫 *قیمت با کد تخفیف:* `{price_text}`"
    else:
        price_text = format_price(plan["price"])
        discount_note = f"💰 *مبلغ قابل پرداخت:* `{price_text}`"

    kb = [
        [InlineKeyboardButton("✅ پرداخت کردم، رسید میفرستم", callback_data="paid")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")],
    ]
    await q.edit_message_text(
        f"🌟 *بسته انتخابی: {plan['name']}*\n\n"
        f"{discount_note}\n\n"
        f"💳 *شماره کارت جهت واریز:*\n`{CARD_NUMBER}`\n"
        f"👤 *به نام:* {CARD_OWNER}\n\n"
        f"─────────────────\n"
        f"📌 *مراحل خرید:*\n"
        f"۱. مبلغ رو به کارت بالا واریز کن\n"
        f"۲. دکمه زیر رو بزن\n"
        f"۳. عکس رسید پرداخت رو بفرست\n"
        f"۴. بعد از تایید ادمین، کانفیگ ارسال میشه ✅\n\n"
        f"⏱ زمان تحویل: معمولاً کمتر از ۳۰ دقیقه",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return WAIT_RECEIPT

async def ask_discount(update, ctx):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎫 *کد تخفیف*\n\n"
        "کد تخفیف خودت رو وارد کن 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
    )
    return WAIT_DISCOUNT

async def receive_discount(update, ctx):
    code = update.message.text.strip()
    kb = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back")]]
    if code in DISCOUNT_CODES:
        ctx.user_data["discount"] = DISCOUNT_CODES[code]
        if DISCOUNT_CODES[code] == "free":
            msg = "🎁 *کد تخفیف معتبره!*\n\nتمام بسته‌ها برای شما *رایگان* شدن!\nبرو خرید بسته و حجمت رو انتخاب کن 🚀"
        else:
            msg = "✅ *کد تخفیف اعمال شد!*\n\nقیمت‌های تخفیف‌دار برات فعال شد.\nبرو خرید بسته رو انتخاب کن 🛒"
    else:
        msg = "❌ *کد تخفیف نامعتبره!*\n\nکد وارد شده صحیح نیست. دوباره امتحان کن."
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def ask_receipt(update, ctx):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📸 *ارسال رسید پرداخت*\n\n"
        "لطفاً عکس رسید پرداختت رو همین الان بفرست 👇",
        parse_mode="Markdown"
    )
    return WAIT_RECEIPT

async def receive_receipt(update, ctx):
    user = update.effective_user
    plan_id = ctx.user_data.get("plan_id", "")
    plan = PLANS.get(plan_id, {})
    discount = ctx.user_data.get("discount", None)

    await update.message.reply_text(
        "✅ *رسیدت دریافت شد!*\n\n"
        "در حال بررسی توسط ادمین...\n"
        "به زودی کانفیگ VPN برات ارسال میشه 🙏",
        parse_mode="Markdown"
    )

    discount_note = ""
    if discount == "free":
        discount_note = "\n🎫 کد تخفیف: رایگان"
    elif isinstance(discount, dict):
        discount_note = "\n🎫 کد تخفیف: Ahnp"

    caption = (
        f"🔔 *سفارش جدید!*\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 آیدی: `{user.id}`\n"
        f"📦 بسته: {plan.get('name', plan_id)}\n"
        f"💰 مبلغ: {format_price(plan.get('price', 0))}"
        f"{discount_note}\n\n"
        f"برای تایید روی دکمه بزن 👇"
    )
    kb = [[
        InlineKeyboardButton("✅ تایید و ارسال کانفیگ", callback_data=f"approve_{user.id}_{plan_id}"),
        InlineKeyboardButton("❌ رد کردن", callback_data=f"reject_{user.id}"),
    ]]
    if update.message.photo:
        await ctx.bot.send_photo(ADMIN_ID, photo=update.message.photo[-1].file_id,
                                  caption=caption, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))
    else:
        await ctx.bot.send_message(ADMIN_ID,
                                    text=caption + f"\n\n📝 متن: {update.message.text or ''}",
                                    parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def approve_order(update, ctx):
    q = update.callback_query
    await q.answer()
    if update.effective_user.id != ADMIN_ID:
        return
    parts = q.data.split("_")
    user_id = int(parts[1])
    plan_id = parts[2]
    plan = PLANS.get(plan_id, {})
    await q.edit_message_reply_markup(reply_markup=None)
    await ctx.bot.send_message(
        ADMIN_ID,
        f"📤 *ارسال کانفیگ*\n\nکاربر: {user_id}\nبسته: {plan.get('name','')}\n\nکانفیگ رو همین الان بفرست:",
        parse_mode="Markdown"
    )
    ctx.bot_data[f"waiting_config_{ADMIN_ID}"] = {"user_id": user_id, "plan_id": plan_id, "plan_name": plan.get("name", "")}

async def handle_admin_config(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        return
    waiting_key = f"waiting_config_{ADMIN_ID}"
    if waiting_key not in ctx.bot_data:
        return
    info = ctx.bot_data.pop(waiting_key)
    target_user_id = info["user_id"]
    plan_name = info["plan_name"]
    plan_id = info["plan_id"]
    config_text = update.message.text or ""

    orders = load_orders()
    user_key = str(target_user_id)
    if user_key not in orders:
        orders[user_key] = []
    orders[user_key].append({"plan_id": plan_id, "plan_name": plan_name, "config": config_text, "active": True})
    save_orders(orders)

    await ctx.bot.send_message(
        target_user_id,
        f"🎉 *سفارش شما تایید شد!*\n\n"
        f"📦 بسته: *{plan_name}*\n\n"
        f"🔑 *کانفیگ VPN شما:*\n`{config_text}`\n\n"
        f"📲 این لینک رو کپی کن و توی اپ *V2rayNG* یا *Hiddify* وارد کن.\n\n"
        f"🌐 اینترنت آزاد رو لذت ببر! 🚀",
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ کانفیگ با موفقیت برای کاربر ارسال شد!")

async def reject_order(update, ctx):
    q = update.callback_query
    await q.answer()
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = int(q.data.split("_")[1])
    await ctx.bot.send_message(
        user_id,
        f"❌ *رسید شما تایید نشد.*\n\nلطفاً دوباره رسید معتبر ارسال کنید یا با پشتیبانی تماس بگیرید.\nپشتیبانی: {SUPPORT_USERNAME}",
        parse_mode="Markdown"
    )
    await q.edit_message_reply_markup(reply_markup=None)

async def my_orders(update, ctx):
    q = update.callback_query
    await q.answer()
    user_id = str(update.effective_user.id)
    orders = load_orders()
    user_orders = orders.get(user_id, [])
    if not user_orders:
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await q.edit_message_text(
            "📦 *بسته های من*\n\nهنوز هیچ بسته ای خریداری نکردی!\nبرو یه بسته بخر 🚀",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    kb = []
    for i, order in enumerate(user_orders):
        status = "🟢 فعال" if order.get("active") else "🔴 غیرفعال"
        kb.append([InlineKeyboardButton(f"{order.get('plan_name','بسته')} - {status}", callback_data=f"vieworder_{i}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
    await q.edit_message_text("📦 *بسته های من:*\n\nروی هر بسته بزن 👇", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def view_order(update, ctx):
    q = update.callback_query
    await q.answer()
    user_id = str(update.effective_user.id)
    idx = int(q.data.replace("vieworder_", ""))
    orders = load_orders()
    user_orders = orders.get(user_id, [])
    if idx >= len(user_orders):
        await q.edit_message_text("❌ بسته پیدا نشد.")
        return
    order = user_orders[idx]
    status = "🟢 فعال" if order.get("active") else "🔴 غیرفعال"
    kb = [[InlineKeyboardButton("🔙 بازگشت به بسته ها", callback_data="myorders")]]
    await q.edit_message_text(
        f"📦 *مشخصات بسته:*\n\nنام: *{order.get('plan_name','')}*\nوضعیت: {status}\n\n🔑 *کانفیگ:*\n`{order.get('config','')}`\n\n📲 این کانفیگ رو توی V2rayNG یا Hiddify وارد کن.",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )

async def support(update, ctx):
    q = update.callback_query
    await q.answer()
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await q.edit_message_text(
        f"🎧 *پشتیبانی*\n\nبرای ارتباط با پشتیبانی به آیدی زیر پیام بده:\n\n👤 {SUPPORT_USERNAME}\n\n⏰ ساعت پاسخگویی: ۹ صبح تا ۱۲ شب",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )

async def back(update, ctx):
    q = update.callback_query
    await q.answer()
    await start(update, ctx)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    discount_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_discount, pattern="^discount$")],
        states={
            WAIT_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_discount)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    buy_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_plan, pattern="^select_")],
        states={
            WAIT_RECEIPT: [
                CallbackQueryHandler(ask_receipt, pattern="^paid$"),
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), receive_receipt),
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^myorders$"))
    app.add_handler(CallbackQueryHandler(view_order, pattern="^vieworder_"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(approve_order, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_order, pattern="^reject_"))
    app.add_handler(discount_conv)
    app.add_handler(buy_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_config))
    app.run_polling()

if __name__ == "__main__":
    main()
