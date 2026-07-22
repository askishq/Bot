import os
import subprocess
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Enter your Telegram Bot Token here
BOT_TOKEN = "8632100658:AAHGNHnw6_uQ8l0lKnuK8ewIqJ-JF7B-YM8"

def upload_to_pixeldrain(file_path):
    """
    Streams and uploads the file to Pixeldrain and returns the download link.
    """
    url = f"https://pixeldrain.com/api/file/{os.path.basename(file_path)}"
    
    try:
        with open(file_path, 'rb') as f:
            # Pixeldrain API uses PUT request for file uploads
            # Timeout set to 15 minutes (900 seconds) for large files
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
    if len(context.args) < 2:
        await update.message.reply_text("❌ Correct format: `/record <URL> <duration_in_seconds>`", parse_mode="Markdown")
        return

    url = context.args[0]
    try:
        duration = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Duration must be a number (e.g., 300).")
        return

    status_msg = await update.message.reply_text("⏳ Recording started...")
    filename = f"rec_{int(time.time())}.mp4"

    # FFmpeg Command
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-reconnect", "1",
        "-reconnect_at_eof", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", url,
        "-t", str(duration),
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        filename
    ]

    try:
        subprocess.run(cmd, check=True)
        
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            file_size_bytes = os.path.getsize(filename)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # If file size is 50 MB or less, send directly to Telegram
            if file_size_mb <= 50:
                await status_msg.edit_text(f"📤 File size is {file_size_mb:.2f} MB. Sending directly to Telegram...")
                with open(filename, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"✅ **Recording Successful!**\n📏 Size: {file_size_mb:.2f} MB",
                        parse_mode="Markdown"
                    )
                await status_msg.delete()

            # If file size is greater than 50 MB, upload to Pixeldrain
            else:
                await status_msg.edit_text(f"🚀 File size is {file_size_mb:.2f} MB. Uploading to Pixeldrain cloud...")
                pixeldrain_link = upload_to_pixeldrain(filename)

                if pixeldrain_link:
                    await status_msg.edit_text(
                        f"✅ **Recording Successful!**\n"
                        f"📏 Size: {file_size_mb:.2f} MB\n\n"
                        f"🔗 [Download/Watch Link]({pixeldrain_link})",
                        parse_mode="Markdown"
                    )
                else:
                    await status_msg.edit_text("❌ Cloud upload failed. There was an error uploading the file to Pixeldrain.")

            # Remove file from server after upload
            if os.path.exists(filename):
                os.remove(filename)
        else:
            await status_msg.edit_text("❌ Recording failed (0 Byte File). Please check your link.")

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
    
