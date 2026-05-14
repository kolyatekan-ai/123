"""
Telegram бот для игры "Бункер"
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from game import Game, active_games

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")


# ==================== КОМАНДЫ ====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение."""
    await update.message.reply_text(
        "🏠 *Добро пожаловать в игру «Бункер»!*\n\n"
        "Произошла катастрофа, и лишь часть людей сможет спастись в бункере. "
        "Каждый игрок получает случайную карточку с характеристиками. "
        "Задача — убедить остальных, что именно ты достоин места в бункере!\n\n"
        "*Команды:*\n"
        "/create — создать новую игру\n"
        "/join — присоединиться к игре\n"
        "/begin — начать игру (создатель)\n"
        "/card — посмотреть свою карточку (в ЛС)\n"
        "/reveal — раскрыть характеристику\n"
        "/vote — голосовать за изгнание\n"
        "/status — статус игры\n"
        "/end — завершить игру (создатель)\n",
        parse_mode="Markdown"
    )


async def cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать новую игру в чате."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id in active_games:
        await update.message.reply_text("⚠️ В этом чате уже есть активная игра! "
                                        "Используй /end чтобы завершить её.")
        return

    game = Game(chat_id, user_id)
    username = update.effective_user.first_name or update.effective_user.username or "Игрок"
    game.add_player(user_id, username)
    active_games[chat_id] = game

    await update.message.reply_text(
        f"🎮 *Игра создана!*\n\n"
        f"Создатель: {username}\n"
        f"Игроки: 1\n\n"
        f"Присоединяйтесь командой /join\n"
        f"Для начала игры минимум 3 игрока.\n"
        f"Создатель запускает игру командой /begin",
        parse_mode="Markdown"
    )


async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединиться к игре."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ В этом чате нет активной игры. "
                                        "Создай её командой /create")
        return

    game = active_games[chat_id]
    username = update.effective_user.first_name or update.effective_user.username or "Игрок"

    if not game.add_player(user_id, username):
        if user_id in game.players:
            await update.message.reply_text("⚠️ Ты уже в игре!")
        else:
            await update.message.reply_text("⚠️ Игра уже началась, нельзя присоединиться.")
        return

    players_list = "\n".join([f"• {p.username}" for p in game.players.values()])
    await update.message.reply_text(
        f"✅ *{username}* присоединился к игре!\n\n"
        f"Игроки ({len(game.players)}):\n{players_list}",
        parse_mode="Markdown"
    )


async def cmd_begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать игру (только создатель)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = active_games[chat_id]

    if game.creator_id != user_id:
        await update.message.reply_text("⚠️ Только создатель может начать игру!")
        return

    result = game.start_game()
    if result is None:
        await update.message.reply_text("⚠️ Нужно минимум 3 игрока для начала!")
        return

    await update.message.reply_text(result, parse_mode="Markdown")

    # Отправляем карточки в ЛС каждому игроку
    for player in game.players.values():
        try:
            await context.bot.send_message(
                chat_id=player.user_id,
                text=player.get_card(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить карточку {player.username}: {e}")
            await update.message.reply_text(
                f"⚠️ Не удалось отправить карточку игроку {player.username}. "
                f"Напишите боту /card в ЛС."
            )

    # Показать чья очередь
    current = game.get_current_turn_player()
    if current:
        await update.message.reply_text(
            f"🎲 Ход: *{current.username}*\n"
            f"Используй /reveal чтобы раскрыть характеристику.",
            parse_mode="Markdown"
        )


async def cmd_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать карточку игрока (работает в ЛС)."""
    user_id = update.effective_user.id

    # Ищем игру, в которой участвует этот игрок
    for game in active_games.values():
        if user_id in game.players:
            player = game.players[user_id]
            await update.message.reply_text(player.get_card(), parse_mode="Markdown")
            return

    await update.message.reply_text("❌ Ты не участвуешь ни в одной игре.")


async def cmd_reveal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Раскрыть характеристику."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = active_games[chat_id]

    if game.state != Game.STATE_PLAYING:
        await update.message.reply_text("⚠️ Сейчас не фаза раскрытия!")
        return

    current = game.get_current_turn_player()
    if not current or current.user_id != user_id:
        await update.message.reply_text(
            f"⚠️ Сейчас не твой ход! Ходит: {current.username if current else '???'}"
        )
        return

    # Показать кнопки для раскрытия
    attributes = {
        "profession": "👔 Профессия",
        "biology": "🧬 Биология",
        "health": "❤️ Здоровье",
        "hobby": "🎯 Хобби",
        "baggage": "🎒 Багаж",
        "phobia": "😱 Фобия",
        "fact": "📝 Факт",
    }

    buttons = []
    for attr, label in attributes.items():
        if not current.revealed[attr]:
            buttons.append(
                InlineKeyboardButton(label, callback_data=f"reveal_{attr}")
            )

    if not buttons:
        await update.message.reply_text("⚠️ Все характеристики уже раскрыты!")
        game.next_turn()
        await _show_next_turn(update, game)
        return

    # Разбиваем на ряды по 2
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Выбери характеристику для раскрытия:",
        reply_markup=reply_markup
    )


async def callback_reveal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки раскрытия."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if chat_id not in active_games:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    game = active_games[chat_id]
    current = game.get_current_turn_player()

    if not current or current.user_id != user_id:
        await query.answer("Сейчас не твой ход!", show_alert=True)
        return

    attribute = query.data.replace("reveal_", "")
    result = current.reveal(attribute)

    if result is None:
        await query.answer("Эта характеристика уже раскрыта!", show_alert=True)
        return

    await query.edit_message_text(
        f"🔓 *{current.username}* раскрывает:\n{result}",
        parse_mode="Markdown"
    )

    # Следующий ход
    game.next_turn()
    await _show_next_turn_from_query(query, game, context)


async def _show_next_turn(update: Update, game: Game):
    """Показать информацию о следующем ходе."""
    if game.state == Game.STATE_VOTING:
        alive = game.get_alive_players()
        buttons = []
        for p in alive:
            buttons.append(
                InlineKeyboardButton(p.username, callback_data=f"vote_{p.user_id}")
            )
        keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🗳 *Голосование!*\n"
            "Выберите, кого изгнать из бункера:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif game.state == Game.STATE_PLAYING:
        current = game.get_current_turn_player()
        if current:
            await update.message.reply_text(
                f"🎲 Ход: *{current.username}*\n"
                f"Используй /reveal чтобы раскрыть характеристику.",
                parse_mode="Markdown"
            )


async def _show_next_turn_from_query(query, game: Game, context):
    """Показать информацию о следующем ходе (из callback_query)."""
    chat_id = query.message.chat_id

    if game.state == Game.STATE_VOTING:
        alive = game.get_alive_players()
        buttons = []
        for p in alive:
            buttons.append(
                InlineKeyboardButton(p.username, callback_data=f"vote_{p.user_id}")
            )
        keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text="🗳 *Голосование!*\n"
                 "Выберите, кого изгнать из бункера:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif game.state == Game.STATE_PLAYING:
        current = game.get_current_turn_player()
        if current:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎲 Ход: *{current.username}*\n"
                     f"Используй /reveal чтобы раскрыть характеристику.",
                parse_mode="Markdown"
            )


async def callback_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосования."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if chat_id not in active_games:
        await query.answer("Игра не найдена!", show_alert=True)
        return

    game = active_games[chat_id]

    if game.state != Game.STATE_VOTING:
        await query.answer("Сейчас нет голосования!", show_alert=True)
        return

    target_id = int(query.data.replace("vote_", ""))

    if not game.vote(user_id, target_id):
        if user_id == target_id:
            await query.answer("Нельзя голосовать за себя!", show_alert=True)
        else:
            await query.answer("Не удалось проголосовать!", show_alert=True)
        return

    voter_name = game.players[user_id].username
    target_name = game.players[target_id].username
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✋ *{voter_name}* проголосовал(а).",
        parse_mode="Markdown"
    )

    # Проверяем, все ли проголосовали
    if game.all_voted():
        kicked, result_text = game.resolve_votes()
        await context.bot.send_message(
            chat_id=chat_id,
            text=result_text,
            parse_mode="Markdown"
        )

        # Если игра продолжается, показать следующий ход
        if game.state == Game.STATE_PLAYING:
            current = game.get_current_turn_player()
            if current:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🎲 Ход: *{current.username}*\n"
                         f"Используй /reveal чтобы раскрыть характеристику.",
                    parse_mode="Markdown"
                )
        elif game.state == Game.STATE_FINISHED:
            del active_games[chat_id]


async def cmd_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать кнопки голосования."""
    chat_id = update.effective_chat.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = active_games[chat_id]

    if game.state != Game.STATE_VOTING:
        await update.message.reply_text("⚠️ Сейчас не фаза голосования!")
        return

    alive = game.get_alive_players()
    buttons = []
    for p in alive:
        buttons.append(
            InlineKeyboardButton(p.username, callback_data=f"vote_{p.user_id}")
        )
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🗳 *Голосование!*\nВыберите, кого изгнать из бункера:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус текущей игры."""
    chat_id = update.effective_chat.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры в этом чате.")
        return

    game = active_games[chat_id]

    state_names = {
        Game.STATE_LOBBY: "Ожидание игроков",
        Game.STATE_PLAYING: "Раскрытие характеристик",
        Game.STATE_VOTING: "Голосование",
        Game.STATE_FINISHED: "Завершена",
    }

    alive = game.get_alive_players()
    dead = [p for p in game.players.values() if not p.is_alive]

    text = f"📋 *Статус игры*\n\n"
    text += f"Состояние: {state_names[game.state]}\n"
    text += f"Раунд: {game.round_number}\n"

    if game.catastrophe:
        text += f"Катастрофа: {game.catastrophe}\n"
        text += f"Бункер: {game.bunker}\n"

    text += f"\n👥 *Живые ({len(alive)}):*\n"
    for p in alive:
        text += f"• {p.username}\n"
        revealed = p.get_revealed_info()
        if revealed != "Ничего не раскрыто":
            text += f"  {revealed}\n"

    if dead:
        text += f"\n💀 *Изгнанные ({len(dead)}):*\n"
        for p in dead:
            text += f"• {p.username}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершить игру (только создатель)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = active_games[chat_id]

    if game.creator_id != user_id:
        await update.message.reply_text("⚠️ Только создатель может завершить игру!")
        return

    del active_games[chat_id]
    await update.message.reply_text("🛑 Игра завершена!")


def main():
    """Запуск бота."""
    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("create", cmd_create))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("begin", cmd_begin))
    app.add_handler(CommandHandler("card", cmd_card))
    app.add_handler(CommandHandler("reveal", cmd_reveal))
    app.add_handler(CommandHandler("vote", cmd_vote))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("end", cmd_end))

    # Callback-кнопки
    app.add_handler(CallbackQueryHandler(callback_reveal, pattern="^reveal_"))
    app.add_handler(CallbackQueryHandler(callback_vote, pattern="^vote_"))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
