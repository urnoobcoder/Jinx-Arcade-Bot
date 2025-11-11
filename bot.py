# main.py
import os
import json
import random
from datetime import timedelta
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from pathlib import Path

# -------------------------
# Bot identity (display only)
# -------------------------
BOT_NAME = "Jinx"
BOT_USERNAME = "@Jinx_Arcadebot"
DEVELOPER_NAME = "Comrade"
DEVELOPER_USERNAME = "@commonyetrare"

# -------------------------
# Environment & Data files
# -------------------------
TOKEN = os.getenv("BOT_TOKEN")  # set this in Replit secrets or environment
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
WARN_FILE = DATA_DIR / "warnings.json"
QUOTE_FILE = DATA_DIR / "quotes.json"

# initialize storage files if they don't exist
if not WARN_FILE.exists():
    WARN_FILE.write_text(json.dumps({}))
if not QUOTE_FILE.exists():
    QUOTE_FILE.write_text(json.dumps([]))

# -------------------------
# Helpers
# -------------------------
def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def is_admin(chat, user_id, context: ContextTypes.DEFAULT_TYPE):
    """Return True if user_id is an admin/creator in chat"""
    try:
        member = context.bot.get_chat_member(chat.id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

def mention(user):
    if user.username:
        return f"@{user.username}"
    return user.first_name or str(user.id)

# -------------------------
# Jinx-style replies
# -------------------------
def jinx_say(text):
    # small wrapper to make Jinx-style text playful
    return f"💥 Jinx: {text}"

# -------------------------
# Moderation Data Management
# -------------------------
warnings_data = load_json(WARN_FILE)

def get_warns(chat_id_str, user_id_str):
    return warnings_data.get(chat_id_str, {}).get(user_id_str, 0)

def inc_warn(chat_id_str, user_id_str):
    warnings_data.setdefault(chat_id_str, {})
    warnings_data[chat_id_str][user_id_str] = warnings_data[chat_id_str].get(user_id_str, 0) + 1
    save_json(WARN_FILE, warnings_data)
    return warnings_data[chat_id_str][user_id_str]

def reset_warn(chat_id_str, user_id_str):
    if chat_id_str in warnings_data and user_id_str in warnings_data[chat_id_str]:
        warnings_data[chat_id_str][user_id_str] = 0
        save_json(WARN_FILE, warnings_data)

# -------------------------
# Quote System (simple)
# -------------------------
def add_quote(text, author_name, added_by):
    quotes = load_json(QUOTE_FILE)
    quotes.append({
        "id": len(quotes) + 1,
        "text": text,
        "author": author_name,
        "added_by": added_by,
    })
    save_json(QUOTE_FILE, quotes)
    return quotes[-1]

def get_random_quote():
    quotes = load_json(QUOTE_FILE)
    if not quotes:
        return None
    return random.choice(quotes)

def get_quote_by_id(qid):
    quotes = load_json(QUOTE_FILE)
    for q in quotes:
        if q.get("id") == qid:
            return q
    return None

# -------------------------
# Command Handlers
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"{jinx_say('Heh — I’m live!')}\n\n"
        f"I am *{BOT_NAME}* {BOT_USERNAME}\n"
        f"Dev: {DEVELOPER_NAME} ({DEVELOPER_USERNAME})\n\n"
        "Commands: /help — show chaos menu!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Jinx Arcade — Commands*\n\n"
        "🎮 *Moderation (admins only)*\n"
        "/warn — reply to a message to warn (3 warns → ban)\n"
        "/resetwarns — reply to a user to reset warnings\n"
        "/mute — reply to mute for 1 minute\n"
        "/unmute — reply to unmute\n"
        "/ban — reply to ban\n"
        "/unban <user_id> — unban by id\n"
        "/purge — reply to a message then send /purge to delete range\n\n"
        "✨ *Group & fun*\n"
        "/rules — show group rules\n"
        "/info — show your info or reply to get other's info\n"
        "/quote — reply to a message to save it as a quote\n"
        "/getquote — get a random quote\n"
        "/getquote <id> — get quote by id\n"
        "/quotes — list last 10 quotes\n\n"
        "/about — about the bot\n"
    )
    await update.message.reply_text(jinx_say(text), parse_mode="Markdown")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"{BOT_NAME} — Arcade mischief for gaming groups!\n"
        f"Developer: {DEVELOPER_NAME} ({DEVELOPER_USERNAME})\n"
        "Inspired by pro-moderation bots & quoting bots.\n"
        "Play nice or PowPow!"
    )
    await update.message.reply_text(jinx_say(text))

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 *Group Rules*\n"
        "1. Keep it friendly — no hate/abuse.\n"
        "2. No spam or ad links without permission.\n"
        "3. Avoid spoilers in main chat — use threads.\n"
        "4. Respect admins.\n"
        "5. Have fun — and chaos responsibly!"
    )
    await update.message.reply_text(jinx_say(text), parse_mode="Markdown")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user
    text = (
        f"👤 *User Info*\n"
        f"Name: `{user.full_name}`\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"ID: `{user.id}`\n"
    )
    await update.message.reply_text(jinx_say(text), parse_mode="Markdown")

# -------------------------
# Moderation commands (admins only)
# -------------------------
async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a message to warn someone."))
        return
    # check permission
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("You gotta be an admin to pull that trigger!"))
        return

    target = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    user_id = str(target.id)

    new_count = inc_warn(chat_id, user_id)
    await update.message.reply_text(jinx_say(f"{mention(target)} warned ({new_count}/3)."))

    if new_count >= 3:
        await update.effective_chat.ban_member(target.id)
        reset_warn(chat_id, user_id)
        await update.message.reply_text(jinx_say(f"{mention(target)} exploded off the group (banned)."))

async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a user to reset their warnings."))
        return
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Admins only, comrade."))
        return
    target = update.message.reply_to_message.from_user
    reset_warn(str(update.effective_chat.id), str(target.id))
    await update.message.reply_text(jinx_say(f"Warnings for {mention(target)} cleared."))

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a user to mute them."))
        return
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Nope — admin only."))
        return
    target = update.message.reply_to_message.from_user
    try:
        # mute for 1 minute by default (use until_date parameter)
        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False),
            until_date=timedelta(minutes=1)
        )
        await update.message.reply_text(jinx_say(f"{mention(target)} muted for 1 minute. Pow."))
    except Exception as e:
        await update.message.reply_text(jinx_say(f"Oops: {e}"))

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a user to unmute them."))
        return
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Admin permission required."))
        return
    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        )
        await update.message.reply_text(jinx_say(f"{mention(target)} unmuted. Back to chaos!"))
    except Exception as e:
        await update.message.reply_text(jinx_say(f"Oops: {e}"))

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a message to ban someone."))
        return
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Only admins may ban."))
        return
    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.ban_member(target.id)
        await update.message.reply_text(jinx_say(f"{mention(target)} has been banished."))
    except Exception as e:
        await update.message.reply_text(jinx_say(f"Error: {e}"))

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Only admins can do that."))
        return
    if not context.args:
        await update.message.reply_text(jinx_say("Usage: /unban <user_id>"))
        return
    try:
        user_id = int(context.args[0])
        await update.effective_chat.unban_member(user_id)
        await update.message.reply_text(jinx_say(f"User `{user_id}` unbanned."))
    except Exception as e:
        await update.message.reply_text(jinx_say(f"Error: {e}"))

async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: reply to a message and send /purge — deletes from replied msg id to current
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a message to start purging from there."))
        return
    sender_id = update.effective_user.id
    if not is_admin(update.effective_chat, sender_id, context):
        await update.message.reply_text(jinx_say("Admins only for the big cleanup."))
        return
    chat = update.effective_chat
    start_id = update.message.reply_to_message.message_id
    end_id = update.message.message_id
    deleted = 0
    for mid in range(start_id, end_id + 1):
        try:
            await chat.delete_message(mid)
            deleted += 1
        except Exception:
            pass
    await update.message.reply_text(jinx_say(f"Purged ~{deleted} messages. Boom."))

# -------------------------
# Welcome & Leave handlers
# -------------------------
async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        txt = f"🎉 {mention(member)} — welcome to {update.effective_chat.title}! Read /rules and keep your trigger happy finger safe."
        await update.message.reply_text(jinx_say(txt))

async def left_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.left_chat_member:
        return
    member = update.message.left_chat_member
    await update.message.reply_text(jinx_say(f"{mention(member)} left. Too chaotic even for them."))

# -------------------------
# Bad words & link filter (simple)
# -------------------------
BAD_WORDS = ["idiot", "noob", "trash", "badword", "spam"]
BLOCK_LINKS = True

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()

    if BLOCK_LINKS and ("http://" in text or "https://" in text or "t.me/" in text):
        # if sender is not admin, delete link
        sender = update.effective_user
        if not is_admin(update.effective_chat, sender.id, context):
            try:
                await update.message.delete()
                await update.message.reply_text(jinx_say(f"No links, {mention(sender)}."))
            except Exception:
                pass
            return

    if any(bad in text for bad in BAD_WORDS):
        sender = update.effective_user
        if not is_admin(update.effective_chat, sender.id, context):
            try:
                await update.message.delete()
                await update.message.reply_text(jinx_say(f"Watch your tongue, {mention(sender)}!"))
            except Exception:
                pass
            return

# -------------------------
# Quote handlers (QuotLy-like)
# -------------------------
async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reply to a message to save it as a quote
    if not update.message.reply_to_message:
        await update.message.reply_text(jinx_say("Reply to a message with /quote to save that line to the arcade wall."))
        return
    replied = update.message.reply_to_message
    text = replied.text or replied.caption or ""
    if not text:
        await update.message.reply_text(jinx_say("Can't quote that (no text)."))
        return
    author_name = replied.from_user.full_name
    added_by = update.effective_user.username or update.effective_user.full_name
    q = add_quote(text, author_name, added_by)
    await update.message.reply_text(jinx_say(f"Quote #{q['id']} saved: \"{text[:80]}...\""))

async def getquote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /getquote or /getquote <id>
    if context.args:
        try:
            qid = int(context.args[0])
            q = get_quote_by_id(qid)
            if not q:
                await update.message.reply_text(jinx_say("Quote not found."))
                return
            await update.message.reply_text(jinx_say(f"#{q['id']} — \"{q['text']}\" — {q['author']}"))
            return
        except ValueError:
            pass
    q = get_random_quote()
    if not q:
        await update.message.reply_text(jinx_say("No quotes yet. Be the first to /quote someone!"))
        return
    await update.message.reply_text(jinx_say(f"#{q['id']} — \"{q['text']}\" — {q['author']}"))

async def listquotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quotes = load_json(QUOTE_FILE)
    if not quotes:
        await update.message.reply_text(jinx_say("No quotes in the arcade."))
        return
    recent = quotes[-10:]
    lines = [f"#{q['id']} — {q['text'][:60]}... — {q['author']}" for q in recent]
    await update.message.reply_text(jinx_say("Recent quotes:\n" + "\n".join(lines)))

# -------------------------
# Startup
# -------------------------
def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN environment variable not set.")
        return
    app = ApplicationBuilder().token(TOKEN).build()

    # Basic
    app.add_handler(CommandHandler(["start"], start))
    app.add_handler(CommandHandler(["help"], help_cmd))
    app.add_handler(CommandHandler(["about"], about))
    app.add_handler(CommandHandler(["rules"], rules))
    app.add_handler(CommandHandler(["info"], info))

    # Moderation commands
    app.add_handler(CommandHandler(["warn"], warn_cmd))
    app.add_handler(CommandHandler(["resetwarns"], resetwarns_cmd))
    app.add_handler(CommandHandler(["mute"], mute_cmd))
    app.add_handler(CommandHandler(["unmute"], unmute_cmd))
    app.add_handler(CommandHandler(["ban"], ban_cmd))
    app.add_handler(CommandHandler(["unban"], unban_cmd))
    app.add_handler(CommandHandler(["purge"], purge_cmd))

    # Quotes
    app.add_handler(CommandHandler(["quote"], quote_cmd))
    app.add_handler(CommandHandler(["getquote"], getquote_cmd))
    app.add_handler(CommandHandler(["quotes"], listquotes_cmd))

    # Events
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter))

    print("💥 Jinx bot starting up...")
    app.run_polling()

if __name__ == "__main__":
    main()
