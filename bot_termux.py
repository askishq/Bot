import os
import time
import requests
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

BOT_TOKEN = "8632100658:AAHGNHnw6_uQ8l0lKnuK8ewIqJ-JF7B-YM8"

def upload_to_pixeldrain(file_path):
    url = f"https://pixeldrain.com/api/file/{os.path.basename(file_path)}"
    try:
        with open(file_path, 'rb') as f:
            response = requests.put(url, data=f, timeout=900)
        if response.status_code == 201:
            result = response.json()
            if result.get("success"):
                file_id = result.get("id")
                return f"https://pixeldrain.com/u/{file_id}"
    except Exception as e:
        print(f"Pixeldrain Upload Error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot is active!\n\n"
        "To record, use the following format:\n"
        "`/record <M3U8_URL> <Duration_in_seconds>`",
        parse_mode="Markdown"
    )

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # FFmpeg Command with Force Stop Flag
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-rw_timeout", "15000000",  # 15 seconds read timeout
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
        
        # Give FFmpeg maximum duration + 15 extra seconds, then force stop if hanging
        try:
            await asyncio.wait_for(process.communicate(), timeout=duration + 15)
        except asyncio.TimeoutError:
            print("FFmpeg process timed out. Terminating gracefully...")
            try:
                process.terminate()
                await process.wait()
            except Exception as kill_err:
                print(f"Error terminating process: {kill_err}")

        # Check if video was saved
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
                await status_msg.edit_text(f"🚀 File size is {file_size_mb:.2f} MB. Uploading to Pixeldrain cloud...")
                
                loop = asyncio.get_event_loop()
                pixeldrain_link = await loop.run_in_executor(None, upload_to_pixeldrain, filename)

                if pixeldrain_link:
                    await status_msg.edit_text(
                        f"✅ **Recording Successful!**\n"
                        f"📏 Size: {file_size_mb:.2f} MB\n\n"
                        f"🔗 [Download/Watch Link]({pixeldrain_link})",
                        parse_mode="Markdown"
                    )
                else:
                    await status_msg.edit_text("❌ Cloud upload failed. There was an error uploading the file to Pixeldrain.")

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("record", record))

    app.run_polling()

if __name__ == "__main__":
    main()
    
