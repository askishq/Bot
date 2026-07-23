import os
import time
import json
import requests
import asyncio
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from requests_toolbelt.multipart.encoder import MultipartEncoder
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Dummy HTTP Server for Render Web Service Port Requirement ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# -------------------------------------------------------------

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_ID = 5592855087  # Your Telegram User ID
USERS_FILE = "vip_users.json"

# --- Subscription Helper Functions ---
def load_vip_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading VIP users: {e}")
    return {}

def save_vip_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    except Exception as e:
        print(f"Error saving VIP users: {e}")

def is_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    
    users = load_vip_users()
    str_user_id = str(user_id)
    if str_user_id in users:
        expiry_date = datetime.strptime(users[str_user_id], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expiry_date:
            return True
        else:
            # Subscription expired, clean up
            del users[str_user_id]
            save_vip_users(users)
    return False
# ------------------------------------

def upload_to_gofile(file_path):
    """
    Uploads large files safely by streaming directly from disk without consuming RAM.
    """
    try:
        server_res = requests.get("https://api.gofile.io/servers", timeout=15).json()
        if server_res.get("status") == "ok":
            server_name = server_res["data"]["servers"][0]["name"]
            upload_url = f"https://{server_name}.gofile.io/contents/uploadfile"
            
            with open(file_path, 'rb') as f:
                m = MultipartEncoder(
                    fields={'file': (os.path.basename(file_path), f, 'video/mp4')}
                )
                headers = {'Content-Type': m.content_type}
                response = requests.post(upload_url, data=m, headers=headers, timeout=1800)
                
            res_data = response.json()
            if res_data.get("status") == "ok":
                return res_data["data"]["downloadPage"]
            else:
                print(f"GoFile Response Error: {res_data}")
    except Exception as e:
        print(f"GoFile Exception: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to the Recorder Bot!**\n\n"
        "Available Commands:\n"
        "• /record `<URL> <duration>` - Record Stream\n"
        "• /how_to_use - Usage Instructions\n"
        "• /plans - Subscription Plans\n"
        "• /contact - Contact Support\n",
        parse_mode="Markdown"
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 **Contact Admin:** @Turkey_series_bangla5", parse_mode="Markdown")

async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 **How to Use the Bot:**\n\n"
        "Use the `/record` command with an M3U8 link and recording duration (in seconds).\n\n"
        "👉 **Format:**\n"
        "`/record <M3U8_URL> <Duration_in_seconds>`\n\n"
        "💡 **Example:**\n"
        "`/record https://example.com/stream.m3u8 300`\n"
        "*(This will record 300 seconds / 5 minutes of video)*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💎 **Subscription Plans:**\n\n"
        "🗓 **7 Days:** 100 ৳ / ₹\n"
        "🗓 **30 Days:** 300 ৳ / ₹\n\n"
        "💳 **Payment Methods:** Bkash, Nagad, Binance\n\n"
        "📩 Contact @Turkey_series_bangla5 to buy a subscription!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- Admin Commands ---
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Format: `/addvip <user_id> <days>`", parse_mode="Markdown")
        return

    try:
        target_user = args[0]
        days = int(args[1])
        expiry = datetime.now() + timedelta(days=days)
        
        users = load_vip_users()
        users[target_user] = expiry.strftime("%Y-%m-%d %H:%M:%S")
        save_vip_users(users)

        await update.message.reply_text(f"✅ Subscription granted to User `{target_user}` for {days} days!\nExpired on: {expiry.strftime('%Y-%m-%d')}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Format: `/removevip <user_id>`", parse_mode="Markdown")
        return

    target_user = args[0]
    users = load_vip_users()
    if target_user in users:
        del users[target_user]
        save_vip_users(users)
        await update.message.reply_text(f"✅ Subscription removed for User `{target_user}`.")
    else:
        await update.message.reply_text("❌ User not found in VIP list.")
# ----------------------

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Subscription Check
    if not is_subscribed(user_id):
        await update.message.reply_text(
            "❌ **Access Denied!** You do not have an active subscription.\n\n"
            "Check /plans and contact @Turkey_series_bangla5 to subscribe.",
            parse_mode="Markdown"
        )
        return

    args = [arg for arg in context.args if arg.strip()]

    if len(args) < 2:
        await update.message.reply_text("❌ Correct format: `/record <URL> <duration_in_seconds>`", parse_mode="Markdown")
        return

    url = args[0]
    try:
        duration = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Duration must be a number (e.g., 300).")
        return

    status_msg = await update.message.reply_text("⏳ Recording started...")
    filename = f"rec_{int(time.time())}.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-rw_timeout", "15000000",
        "-i", url,
        "-t", str(duration),
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        filename
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await asyncio.wait_for(process.communicate(), timeout=duration + 30)
        except asyncio.TimeoutError:
            print("FFmpeg process timed out. Terminating gracefully...")
            try:
                process.terminate()
                await process.wait()
            except Exception as kill_err:
                print(f"Error terminating process: {kill_err}")

        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            file_size_bytes = os.path.getsize(filename)
            file_size_mb = file_size_bytes / (1024 * 1024)

            if file_size_mb <= 50:
                await status_msg.edit_text(f"📤 File size is {file_size_mb:.2f} MB. Sending directly to Telegram...")
                with open(filename, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"✅ **Recording Successful!**\n📏 Size: {file_size_mb:.2f} MB",
                        parse_mode="Markdown"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text(
                    f"🚀 File size is {file_size_mb:.2f} MB.\n"
                    f"Uploading to GoFile..."
                )
                
                loop = asyncio.get_running_loop()
                gofile_link = await loop.run_in_executor(None, upload_to_gofile, filename)

                if gofile_link:
                    await status_msg.edit_text(
                        f"✅ **Recording Successful!**\n"
                        f"📏 Size: {file_size_mb:.2f} MB\n\n"
                        f"🔗 [Download/Watch Link]({gofile_link})",
                        parse_mode="Markdown"
                    )
                else:
                    await status_msg.edit_text("❌ Cloud upload failed. There was an error uploading the file to GoFile.")

            if os.path.exists(filename):
                os.remove(filename)
        else:
            await status_msg.edit_text("❌ Recording failed (0 Byte File). Stream link might be invalid or expired.")

    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Bot is starting...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Public Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("contact", contact))
    app.add_handler(CommandHandler("how_to_use", how_to_use))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("record", record))

    # Admin Commands
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("removevip", remove_vip))

    app.run_polling()

if __name__ == "__main__":
    main()
                
