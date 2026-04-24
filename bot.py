import os
import tempfile
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from pydub import AudioSegment

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

SYSTEM_PROMPT = "Отвечай полезно, кратко и только на русском языке."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает! Пиши текстом или отправляй голосовые.")

def ask_llm(user_text: str) -> str:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        temperature=0.6,
        max_tokens=700
    )
    return completion.choices[0].message.content

def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="ru"
        )
    return transcript.text

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        answer = ask_llm(update.message.text)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ogg_path = None
    mp3_path = None
    try:
        await update.message.reply_text("Обрабатываю голосовое...")
        voice = update.message.voice
        tg_file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as f:
            ogg_path = f.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            mp3_path = f.name

        await tg_file.download_to_drive(custom_path=ogg_path)
        AudioSegment.from_ogg(ogg_path).export(mp3_path, format="mp3")

        transcript = transcribe_audio(mp3_path)
        await update.message.reply_text(f"Распознал: {transcript}")

        answer = ask_llm(transcript)
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
    finally:
        for path in [ogg_path, mp3_path]:
            if path and os.path.exists(path):
                os.remove(path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()