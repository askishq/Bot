import asyncio
import logging
import os
import time
import requests
import sys
import shlex
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import NetworkError, Conflict

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Your new token
TOKEN = "8632100658:AAHGNHnw6_uQ8l0lKnuK8ewIqJ-JF7B-YM8"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def upload_to_catbox(file_path):
    url = "https://catbox.moe/user/api.php"
    try:
        with open(file_path, 'rb') as f:
            data = {'reqtype': 'fileupload', 'userhash': ''}
            files = {'fileToUpload': f}
            response = requests.post(url, data=data, files=files, timeout=600)
            if response.status_code == 200:
                return response.text
    except:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ <b>Bot is Active!</b>\n\n"
        "To record, use the command:\n"
        "<code>/record &lt;link&gt; --duration &lt;seconds&gt; --caption &lt;text&gt;</code>",
        parse_mode=ParseMode.HTML
    )

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = context.args
    if not text_args:
        await update.message.reply_text("Correct format: /record <link> --duration <seconds> --caption <caption_text>")
        return

    url = text_args[0]
    duration = 60  # Default duration in seconds if not provided
    caption_text = None

    # Parse --duration and --caption from arguments
    try:
        if "--duration" in text_args:
            dur_idx = text_args.index("--duration")
            if dur_idx + 1 < len(text_args):
                duration = int(text_args[dur_idx + 1])

        if "--caption" in text_args:
            cap_idx = text_args.index("--caption")
            if cap_idx + 1 < len(text_args):
                # Join remaining words as caption
                caption_text = " ".join(text_args[cap_idx + 1:])
    except Exception as e:
        await update.message.reply_text(f"❌ Argument Error: {str(e)}")
        return

    chat_id = update.message.chat_id
    filename = f"rec_{int(time.time())}.mp4"
    
    status = await update.message.reply_text(f"🔴 Recording started... ({duration} seconds)")

    # FFmpeg command
    cmd = [
        "ffmpeg", 
        "-headers", f"User-Agent: {USER_AGENT}\r\nReferer: https://www.google.com/\r\n",
        "-i", url, 
        "-t", str(duration), 
        "-c", "copy", 
        "-bsf:a", "aac_adtstoasc", 
        "-y", 
        filename
    ]

    try:
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        
        if os.path.exists(filename):
            size = os.path.getsize(filename) / (1024 * 1024)
            if size < 48:
                await update.message.reply_text(f"📤 Sending to Telegram... ({size:.2f} MB)")
                try:
                    with open(filename, 'rb') as f:
                        await context.bot.send_video(
                            chat_id=chat_id, 
                            video=f, 
                            caption=caption_text, 
                            write_timeout=600
                        )
                except Exception as e:
                    logging.error(f"Send Error: {e}")
                    await update.message.reply_text("❌ Problem sending to Telegram, uploading to cloud...")
                    size = 100
            
            if size >= 48:
                await update.message.reply_text(f"🚀 File is large ({size:.2f} MB), uploading to cloud...")
                link = await upload_to_catbox(filename)
                if link:
                    cap_info = f"\n<b>Caption:</b> {caption_text}" if caption_text else ""
                    await update.message.reply_text(f"✅ <b>Download Link:</b>\n{link}{cap_info}", parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("❌ Cloud upload failed.")
            
            if os.path.exists(filename):
                os.remove(filename)
        else:
            await status.edit_text("❌ Recording failed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def run_bot():
    while True:
        try:
            application = ApplicationBuilder().token(TOKEN).build()
            application.add_handler(CommandHandler('start', start))
            application.add_handler(CommandHandler('record', record))
            
            print("Bot is starting... (Termux)")
            await application.initialize()
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            while True:
                await asyncio.sleep(3600)
        except (NetworkError, Conflict):
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
        
