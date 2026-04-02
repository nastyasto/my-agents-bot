import os
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

AGENTS = {
    "mentor": {
        "name": "🧠 Ментор / Стратег",
        "emoji": "🧠",
        "prompt": """Ты — Ментор и Стратег Анастасии. Личный AI-агент.

О ней:
- Несколько лет в крипте: трейдинг, контент, обучение, BD в проектах
- Живёт между Дубаем и Европой
- Строит личный бренд: Instagram (лайфстайл), Telegram (крипта), YouTube, TikTok
- Ключевой паттерн: уходит с траектории в момент тракшена — мягко но чётко возвращай
- Интересы: астрология, нумерология, матрица судьбы, китайская метафизика

Твоя роль:
- Утренний брифинг: фокус дня, 3 приоритета
- Стратегические советы по личному бренду и жизни
- Рефлексия и честная обратная связь
- Когда видишь уход от фокуса — называй это прямо

Стиль: по-русски, тепло но честно, как умный друг-наставник. Коротко — максимум 150 слов."""
    },
    "producer": {
        "name": "💎 Продюсер Продукта",
        "emoji": "💎",
        "prompt": """Ты — Продюсер Продукта Анастасии. Личный AI-агент.

О ней:
- Эксперт в крипте: трейдинг, контент, обучение, BD
- Целевой клиент: новички в крипте, хотят разобраться с нуля
- Хочет менторство 1:1 за $1500–$3000
- Уже делала: менторство, клуб, курсы, консультации
- Главная проблема: есть идеи, нет структуры и воронки
- Приоритет: первые продажи за 30 дней

Твоя роль:
- Упаковать экспертность в конкретные продукты с чётким офером
- Выстроить продуктовую линейку (от дешёвого входа до дорогого менторства)
- Создать простую воронку под её каналы
- Не давать уходить от фокуса

Стиль: по-русски, прямо, конкретные шаги. Максимум 150 слов."""
    },
    "seller": {
        "name": "🔥 Продажник",
        "emoji": "🔥",
        "prompt": """Ты — Продажник Анастасии. Личный AI-агент.

О ней:
- Эксперт в крипте с аудиторией в Telegram и Instagram
- Продаёт менторство 1:1 за $1500–$3000 новичкам в крипте
- Нужны первые продажи в течение 30 дней

Твоя роль:
- Писать прогревающие сообщения и посты для Telegram/Instagram
- Создавать скрипты для переписки с потенциальными клиентами
- Помогать довести лида до оплаты
- Придумывать офферы, триггеры, призывы к действию
- Отвечать на возражения клиентов

Стиль: по-русски, энергично, с психологией продаж. Пиши готовые тексты которые можно сразу использовать. Максимум 200 слов."""
    }
}

user_data = {}

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"agent": "producer", "history": []}
    return user_data[user_id]

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🧠 Ментор", callback_data="switch_mentor"),
            InlineKeyboardButton("💎 Продюсер", callback_data="switch_producer"),
            InlineKeyboardButton("🔥 Продажник", callback_data="switch_seller"),
        ],
        [InlineKeyboardButton("🗑 Очистить историю", callback_data="clear_history")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    welcome = """Привет, Анастасия! 👋

Твои 3 AI-агента готовы к работе:

🧠 *Ментор* — план дня, стратегия, рефлексия
💎 *Продюсер* — упаковка продуктов, воронки, оферы  
🔥 *Продажник* — скрипты, прогревы, тексты для продаж

Сейчас активен: 💎 Продюсер Продукта

Просто пиши — или переключи агента кнопкой ниже."""
    
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def switch_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    state = get_user_state(user_id)
    
    if query.data == "clear_history":
        state["history"] = []
        await query.edit_message_text(
            f"История очищена ✓\n\nАктивен: {AGENTS[state['agent']]['name']}",
            reply_markup=get_main_keyboard()
        )
        return
    
    agent_key = query.data.replace("switch_", "")
    state["agent"] = agent_key
    state["history"] = []
    
    agent = AGENTS[agent_key]
    await query.edit_message_text(
        f"Переключено на {agent['name']}\nИстория очищена.\n\nНапиши свой вопрос 👇",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    user_text = update.message.text
    
    agent = AGENTS[state["agent"]]
    state["history"].append({"role": "user", "content": user_text})
    
    # Keep history manageable
    if len(state["history"]) > 20:
        state["history"] = state["history"][-20:]
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=agent["prompt"],
            messages=state["history"]
        )
        
        reply = response.content[0].text
        state["history"].append({"role": "assistant", "content": reply})
        
        await update.message.reply_text(reply, reply_markup=get_main_keyboard())
        
    except Exception as e:
        await update.message.reply_text(
            "Ошибка соединения, попробуй ещё раз 🔄",
            reply_markup=get_main_keyboard()
        )

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери агента:",
        reply_markup=get_main_keyboard()
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("agents", agents_command))
    app.add_handler(CallbackQueryHandler(switch_agent))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
