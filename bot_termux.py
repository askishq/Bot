import asyncio
import logging
import os
import time
import requests
import sys
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

# ржЖржкржирж╛рж░ ржирждрзБржи ржЯрзЛржХрзЗржи
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
        "тЬЕ <b>ржмржЯ рж╕ржЪрж▓ ржЖржЫрзЗ!</b>\n\n"
        "рж░рзЗржХрж░рзНржб ржХрж░рждрзЗ ржХржорж╛ржирзНржб ржжрж┐ржи:\n"
        "<code>/record <рж▓рж┐ржВржХ> <рж╕ржорзЯ_рж╕рзЗржХрзЗржирзНржбрзЗ></code>",
        parse_mode=ParseMode.HTML
    )

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("рж╕ржарж┐ржХ ржлрж░ржорзНржпрж╛ржЯ: /record <рж▓рж┐ржВржХ> <рж╕ржорзЯ_рж╕рзЗржХрзЗржирзНржбрзЗ>")
        return
    
    url = context.args[0]
    try:
        duration = int(context.args[1])
    except ValueError:
        await update.message.reply_text("рж╕ржорзЯ ржЕржмрж╢рзНржпржЗ рж╕ржВржЦрзНржпрж╛рзЯ рж╣рждрзЗ рж╣ржмрзЗред")
        return

    chat_id = update.message.chat_id
    filename = f"rec_{int(time.time())}.mp4"
    
    status = await update.message.reply_text(f"ЁЯФ┤ рж░рзЗржХрж░рзНржбрж┐ржВ рж╢рзБрж░рзБ рж╣рзЯрзЗржЫрзЗ... ({duration} рж╕рзЗржХрзЗржирзНржб)")

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
                await update.message.reply_text(f"ЁЯУд ржЯрзЗрж▓рж┐ржЧрзНрж░рж╛ржорзЗ ржкрж╛ржарж╛ржирзЛ рж╣ржЪрзНржЫрзЗ... ({size:.2f} MB)")
                try:
                    with open(filename, 'rb') as f:
                        await context.bot.send_video(chat_id=chat_id, video=f, write_timeout=600)
                except Exception as e:
                    logging.error(f"Send Error: {e}")
                    await update.message.reply_text("тЭМ ржЯрзЗрж▓рж┐ржЧрзНрж░рж╛ржорзЗ ржкрж╛ржарж╛рждрзЗ рж╕ржорж╕рзНржпрж╛ рж╣рзЯрзЗржЫрзЗ, ржХрзНрж▓рж╛ржЙржбрзЗ ржЖржкрж▓рзЛржб ржХрж░ржЫрж┐...")
                    size = 100
            
            if size >= 48:
                await update.message.reply_text(f"ЁЯЪА ржлрж╛ржЗрж▓ ржмрзЬ ({size:.2f} MB), ржХрзНрж▓рж╛ржЙржбрзЗ ржЖржкрж▓рзЛржб рж╣ржЪрзНржЫрзЗ...")
                link = await upload_to_catbox(filename)
                if link:
                    await update.message.reply_text(f"тЬЕ <b>ржбрж╛ржЙржирж▓рзЛржб рж▓рж┐ржВржХ:</b>\n{link}", parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("тЭМ ржЖржкрж▓рзЛржб ржмрзНржпрж░рзНрже рж╣рзЯрзЗржЫрзЗред")
            
            if os.path.exists(filename):
                os.remove(filename)
        else:
            await status.edit_text("тЭМ рж░рзЗржХрж░рзНржбрж┐ржВ ржмрзНржпрж░рзНрже рж╣рзЯрзЗржЫрзЗред")
    except Exception as e:
        await update.message.reply_text(f"тЭМ рждрзНрж░рзБржЯрж┐: {str(e)}")

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
