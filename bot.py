from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.helpers import escape_markdown
import os
from dotenv import load_dotenv
from config.db import init_db
from services.UserService import UserService
from services.WishesService import WishesService

init_db()
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ── Conversation states ──────────────────────────────────────────────────────
WAITING_FOR_NAME = 1
WAITING_FOR_WISH = 2
WAITING_FOR_PRIORITY = 3

# ── Keyboards ────────────────────────────────────────────────────────────────
def main_menu(isAdmin=False):
    rows = [
        ["🎁 My Wishes", "➕ Add Wish"],
        ["🔗 Share My List"],
    ]
    if isAdmin:
        rows.append(["🛠️ Admin Panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, input_field_placeholder="Choose an option...")

def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["👥 View All Users", "🎁 View All Wishes"],
            ["🗑️ Delete User"],
            ["⬅️ Back to Main Menu"],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin options...",
    )

def priority_keyboard():
    rows = []
    nums = list(range(1, 11))
    for i in range(0, 10, 5):
        rows.append([str(n) for n in nums[i:i+5]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def wishes_inline(wishes):
    buttons = []
    for w in wishes:
        label = f"[{w.priority}] {w.text}" if len(w.text) <= 30 else f"[{w.priority}] {w.text[:27]}…"
        buttons.append([
            InlineKeyboardButton(f"📝 {label}", callback_data=f"noop_{w.id}"),
            InlineKeyboardButton("❌", callback_data=f"delete_{w.id}"),
        ])
    return InlineKeyboardMarkup(buttons)

def confirm_delete_inline(wish_id: int):
    return InlineKeyboardMarkup([[ 
        InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_{wish_id}"),
        InlineKeyboardButton("🚫 Cancel", callback_data="cancel_delete"),
    ]])

def admin_delete_user_inline(telegram_id: int):
    return InlineKeyboardMarkup([[ 
        InlineKeyboardButton("✅ Yes, delete user", callback_data=f"admin_delete_{telegram_id}"),
        InlineKeyboardButton("🚫 Cancel", callback_data="admin_cancel_delete"),
    ]])

# ── Helpers ──────────────────────────────────────────────────────────────────
def _get_user(telegram_id: int):
    return UserService.get_user_by_telegram_id(telegram_id)

def _require_admin(user) -> bool:
    return user and user.isAdmin

# ── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if user:
        await update.message.reply_text(
            f"Welcome back, {user.name}! 👋\nWhat would you like to do?",
            reply_markup=main_menu(isAdmin=user.isAdmin),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Hi there! 🎁 I'm your personal wishlist bot.\n\nWhat's your name?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOR_NAME

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Please enter a valid name.")
        return WAITING_FOR_NAME

    tg = update.effective_user
    user = UserService.get_or_create_user(tg.id, name, tg.username)
    await update.message.reply_text(
        f"Nice to meet you, {user.name}! ✅\n\nUse the menu below to manage your wishlist.",
        reply_markup=main_menu(isAdmin=user.isAdmin),
    )
    return ConversationHandler.END

# ── Menu routers ─────────────────────────────────────────────────────────────
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🎁 My Wishes":
        await show_wishes(update, context)
    elif text == "🔗 Share My List":
        await share_list(update, context)
    elif text == "🛠️ Admin Panel":
        await admin_panel(update, context)

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "👥 View All Users":
        await admin_view_users(update, context)
    elif text == "🎁 View All Wishes":
        await admin_view_wishes(update, context)
    elif text == "🗑️ Delete User":
        await admin_delete_user_start(update, context)
    elif text == "⬅️ Back to Main Menu":
        user = _get_user(update.effective_user.id)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu(isAdmin=user.isAdmin if user else False),
        )

# ── Show wishes (user) ───────────────────────────────────────────────────────
async def show_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /start first.")
        return

    wishes = WishesService.get_wishes_by_user_id(user.id)
    if not wishes:
        await update.message.reply_text(
            "Your wishlist is empty! Tap ➕ Add Wish to get started.",
            reply_markup=main_menu(isAdmin=user.isAdmin),
        )
        return

    # Sort by priority descending
    wishes.sort(key=lambda x: x.priority, reverse=True)

    await update.message.reply_text(
        f"🎁 *Your Wishlist* ({len(wishes)} item{'s' if len(wishes) != 1 else ''})\n\nTap ❌ next to any wish to delete it:",
        parse_mode="Markdown",
        reply_markup=wishes_inline(wishes),
    )

# ── Add wish flow ────────────────────────────────────────────────────────────
async def add_wish_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /start first.")
        return ConversationHandler.END

    context.user_data["user_id"] = user.id
    context.user_data["user_is_admin"] = user.isAdmin

    await update.message.reply_text(
        "✍️ Send your wish text (with links if avalaible):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOR_WISH

async def add_wish_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wish_text = update.message.text.strip()
    if not wish_text:
        await update.message.reply_text("Please enter a valid wish.")
        return WAITING_FOR_WISH

    context.user_data["wish_text"] = wish_text

    await update.message.reply_text(
        "⭐ Choose priority (1–10):",
        reply_markup=priority_keyboard(),
    )
    return WAITING_FOR_PRIORITY

async def add_wish_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Send a number 1–10.")
        return WAITING_FOR_PRIORITY

    priority = int(text)
    if not 1 <= priority <= 10:
        await update.message.reply_text("Priority must be 1–10.")
        return WAITING_FOR_PRIORITY

    user_id = context.user_data["user_id"]
    is_admin = context.user_data["user_is_admin"]
    wish_text = context.user_data["wish_text"]

    WishesService.create_wish(user_id, wish_text, priority)

    await update.message.reply_text(
        f"✅ Added:\n*{wish_text}*\nPriority: {priority}",
        parse_mode="Markdown",
        reply_markup=main_menu(isAdmin=is_admin),
    )
    return ConversationHandler.END

# ── Share list ───────────────────────────────────────────────────────────────
async def share_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /start first.")
        return

    wishes = WishesService.get_wishes_by_user_id(user.id)
    if not wishes:
        await update.message.reply_text("Your wishlist is empty — nothing to share yet!")
        return

    wishes.sort(key=lambda x: x.priority, reverse=True)
    lines = "\n".join(f"• [{w.priority}] {w.text}" for w in wishes)
    await update.message.reply_text(
        f"Here's your shareable list — just forward this message!\n\n🎁 *{user.name}'s Wishlist*\n\n{lines}",
        parse_mode="Markdown",
        reply_markup=main_menu(isAdmin=user.isAdmin),
    )

# ── Inline button callbacks ──────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── User wish deletion ───────────────────────────────────────────────────
    if data.startswith("delete_"):
        wish_id = int(data.split("_")[1])
        await query.edit_message_reply_markup(reply_markup=confirm_delete_inline(wish_id))

    elif data.startswith("confirm_"):
        wish_id = int(data.split("_")[1])
        user = _get_user(query.from_user.id)
        success = WishesService.delete_wish(wish_id, user.id)
        if success:
            wishes = WishesService.get_wishes_by_user_id(user.id)
            wishes.sort(key=lambda x: x.priority, reverse=True)
            if wishes:
                await query.edit_message_text(
                    f"✅ Wish deleted!\n\n🎁 *Your Wishlist* ({len(wishes)} item{'s' if len(wishes) != 1 else ''})\n\nTap ❌ next to any wish to delete it:",
                    parse_mode="Markdown",
                    reply_markup=wishes_inline(wishes),
                )
            else:
                await query.edit_message_text("✅ Wish deleted!\n\nYour wishlist is now empty.")
        else:
            await query.edit_message_text("❌ Couldn't delete that wish.")

    elif data == "cancel_delete":
        user = _get_user(query.from_user.id)
        wishes = WishesService.get_wishes_by_user_id(user.id)
        wishes.sort(key=lambda x: x.priority, reverse=True)
        await query.edit_message_reply_markup(reply_markup=wishes_inline(wishes))

    # ── Admin user deletion ──────────────────────────────────────────────────
    elif data.startswith("admin_delete_"):
        telegram_id = int(data.split("_")[2])
        actor = _get_user(query.from_user.id)
        if not _require_admin(actor):
            await query.answer("⛔ Access denied.", show_alert=True)
            return

        target = _get_user(telegram_id)
        target_name = target.name if target else str(telegram_id)
        success = UserService.delete_user(telegram_id)
        if success:
            await query.edit_message_text(
                f"✅ User *{target_name}* and all their wishes have been deleted.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("❌ User not found.")

    elif data == "admin_cancel_delete":
        await query.edit_message_text("Deletion cancelled.")

    elif data.startswith("noop_"):
        pass

# ── Admin panel ──────────────────────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not _require_admin(user):
        await update.message.reply_text("⛔ You don't have access to the admin panel.")
        return

    await update.message.reply_text(
        "🛠️ *Admin Panel*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=admin_menu(),
    )

# ── /cancel ──────────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    await update.message.reply_text(
        "Cancelled. 👍",
        reply_markup=main_menu(isAdmin=user.isAdmin if user else False),
    )
    return ConversationHandler.END

async def admin_view_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not _require_admin(user):
        await update.message.reply_text("⛔ Access denied.")
        return

    users = UserService.list_users()
    if not users:
        await update.message.reply_text("No users found.", reply_markup=admin_menu())
        return

    lines = []
    for u in users:
        wishes = WishesService.get_wishes_by_user_id(u.id)
        admin_badge = " 👑" if u.isAdmin else ""
        username_str = f"@{u.username}" if u.username else "no username"

        name_safe = escape_markdown(u.name, version=2)
        username_safe = escape_markdown(username_str, version=2)

        lines.append(
            f"• *{name_safe}*{admin_badge} \\({username_safe}\\)\n"
            f"  📋 {len(wishes)} wish{'es' if len(wishes) != 1 else ''} \\| ID: `{u.telegram_id}`"
        )

    message_text = f"👥 *All Users* \\({len(users)} total\\)\n\n" + "\n\n".join(lines)

    await update.message.reply_text(
        message_text,
        parse_mode="MarkdownV2",
        reply_markup=admin_menu(),
    )

async def admin_view_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not _require_admin(user):
        await update.message.reply_text("⛔ Access denied.")
        return

    all_wishes = WishesService.list_all_wishes()
    if not all_wishes:
        await update.message.reply_text("No wishes found.", reply_markup=admin_menu())
        return

    # Group wishes by user_id
    users = {u.id: u for u in UserService.list_users()}
    grouped: dict = {}
    for w in all_wishes:
        grouped.setdefault(w.user_id, []).append(w)

    lines = []
    for uid, wishes in grouped.items():
        u = users.get(uid)
        owner = u.name if u else f"User {uid}"
        lines.append(f"👤 {owner}")
        for w in wishes:
            lines.append(f"  • {w.text} (Priority: {w.priority})")

    full_message = f"🎁 All Wishes ({len(all_wishes)} total)\n\n" + "\n".join(lines)

    await update.message.reply_text(full_message, reply_markup=admin_menu())

async def admin_delete_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_user(update.effective_user.id)
    if not _require_admin(user):
        await update.message.reply_text("⛔ Access denied.")
        return

    users = UserService.list_users()
    # Prevent admin from deleting themselves
    deletable = [u for u in users if u.telegram_id != update.effective_user.id]

    if not deletable:
        await update.message.reply_text("No other users to delete.", reply_markup=admin_menu())
        return

    buttons = []
    for u in deletable:
        label = f"{'👑 ' if u.isAdmin else ''}{u.name}"
        if u.username:
            label += f" (@{u.username})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admin_delete_{u.telegram_id}")])

    await update.message.reply_text(
        "🗑️ *Delete User*\n\nSelect a user to delete.\n⚠️ This will also delete all their wishes.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ── App setup ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    add_wish_handler = ConversationHandler(
        entry_points=[
            CommandHandler("addwish", add_wish_start),
            MessageHandler(filters.Regex("^➕ Add Wish$"), add_wish_start),
        ],
        states={
            WAITING_FOR_WISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wish_text)],
            WAITING_FOR_PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wish_priority)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(registration_handler)
    app.add_handler(add_wish_handler)

    app.add_handler(MessageHandler(
        filters.Regex("^(👥 View All Users|🎁 View All Wishes|🗑️ Delete User|⬅️ Back to Main Menu)$"),
        handle_admin_menu,
    ))

    app.add_handler(MessageHandler(
        filters.Regex("^(🎁 My Wishes|🔗 Share My List|🛠️ Admin Panel)$"),
        handle_menu,
    ))

    app.add_handler(CallbackQueryHandler(handle_callback))

    # Convenience commands
    app.add_handler(CommandHandler("mywishes", show_wishes))
    app.add_handler(CommandHandler("share", share_list))
    app.add_handler(CommandHandler("admin", admin_panel))

    print("Bot is running...")
    app.run_polling()