import os
import zipfile
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "7930776122:AAGtn0YUQ0cDlvudPRrYUGxKBKJkG1IuMlw"
ADMIN_ID = 7467384643

welcome_msg = "Send a ZIP file to begin."
force_channels = []
normal_channels = []

user_data = {}

logging.basicConfig(level=logging.INFO)

# Admin Commands
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Admin Mode:\n/setwelcome - Set Welcome Message\n/add <link> - Add normal channel\n/force <link> - Add force join channel\n/remove <link> - Remove any channel")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global welcome_msg
    if update.effective_user.id != ADMIN_ID:
        return
    welcome_msg = " ".join(context.args)
    await update.message.reply_text("Welcome message updated.")

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global normal_channels
    if update.effective_user.id != ADMIN_ID:
        return
    for link in context.args:
        if link not in normal_channels:
            normal_channels.append(link)
    await update.message.reply_text("Channels added.")

async def force_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global force_channels
    if update.effective_user.id != ADMIN_ID:
        return
    for link in context.args:
        if link not in force_channels:
            force_channels.append(link)
    await update.message.reply_text("Force channels added.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global force_channels, normal_channels
    if update.effective_user.id != ADMIN_ID:
        return
    for link in context.args:
        if link in force_channels:
            force_channels.remove(link)
        if link in normal_channels:
            normal_channels.remove(link)
    await update.message.reply_text("Channel removed.")

# Join Keyboard
def build_join_keyboard():
    all_links = force_channels + normal_channels
    rows = []
    for i in range(0, len(all_links), 3):
        row = [InlineKeyboardButton(f"Channel {i+j+1}", url=all_links[i+j]) for j in range(min(3, len(all_links) - i))]
        rows.append(row)
    rows.append([InlineKeyboardButton("JOINED", callback_data="joined")])
    return InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if force_channels:
        await update.message.reply_text("Join required channels to continue:", reply_markup=build_join_keyboard())
        user_data[user_id] = {"stage": "waiting_join"}
    else:
        user_data[user_id] = {"stage": "waiting_zip"}
        await update.message.reply_text(welcome_msg)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {"stage": "waiting_zip"}
    await query.edit_message_text("Now send your ZIP file.")

# Handle Documents
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or user_data[user_id].get("stage") not in ["waiting_zip", "awaiting_pass"]:
        return

    file = await update.message.document.get_file()
    file_name = update.message.document.file_name
    path = f"downloads/{user_id}_{file_name}"
    os.makedirs("downloads", exist_ok=True)
    await file.download_to_drive(path)

    if file_name.endswith(".zip"):
        user_data[user_id]["zip"] = path
        user_data[user_id]["stage"] = "awaiting_pass"
        await update.message.reply_text("Now send your `pass.txt` file.", parse_mode="Markdown")

    elif file_name == "pass.txt" and user_data[user_id].get("stage") == "awaiting_pass":
        await try_passwords(update, context, path, user_id)

# Try Passwords
async def try_passwords(update: Update, context: ContextTypes.DEFAULT_TYPE, pass_path: str, user_id: int):
    zip_path = user_data[user_id].get("zip")
    if not zip_path:
        return

    msg = await update.message.reply_text("Trying passwords on your ZIP file...")

    with open(pass_path, "r") as f:
        passwords = [line.strip() for line in f if line.strip()]

    found = False
    for password in passwords:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(f"downloads/{user_id}_unzipped", pwd=bytes(password, 'utf-8'))
                await msg.edit_text(f"*Password Found:* `{password}`", parse_mode="Markdown")
                found = True
                break
        except:
            continue

    if not found:
        await msg.edit_text("Password not found.")

# Bot Setup
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("setwelcome", set_welcome))
app.add_handler(CommandHandler("add", add_channel))
app.add_handler(CommandHandler("force", force_channel))
app.add_handler(CommandHandler("remove", remove_channel))
app.add_handler(CallbackQueryHandler(button_handler, pattern="joined"))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

if __name__ == '__main__':
    print("Bot Running...")
    app.run_polling()
