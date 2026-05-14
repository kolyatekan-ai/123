"""
Логика игры "Бункер"
"""
import random
from data import (
    PROFESSIONS, BIOLOGY, HEALTH, HOBBY,
    BAGGAGE, PHOBIAS, FACTS, CATASTROPHES, BUNKERS, ACTION_CARDS
)


class Player:
    """Игрок с набором характеристик."""

    def __init__(self, user_id: int, username: str, number: int):
        self.user_id = user_id
        self.username = username
        self.number = number  # Номер игрока
        self.profession = random.choice(PROFESSIONS)
        self.biology = random.choice(BIOLOGY)
        self.health = random.choice(HEALTH)
        self.hobby = random.choice(HOBBY)
        self.baggage = random.choice(BAGGAGE)
        self.phobia = random.choice(PHOBIAS)
        self.fact = random.choice(FACTS)
        # Карта действия
        self.action_card = random.choice(ACTION_CARDS)
        self.action_used = False
        self.revealed = {
            "profession": False,
            "biology": False,
            "health": False,
            "hobby": False,
            "baggage": False,
            "phobia": False,
            "fact": False,
        }
        self.is_alive = True  # не выгнан из бункера
        self.has_immunity = False  # иммунитет на раунд
        self.double_vote = False  # двойной голос на раунд
        self.is_tiebreaker = False  # решающий голос при ничьей

    @property
    def display_name(self) -> str:
        """Имя с номером."""
        return f"#{self.number} {self.username}"

    def get_card(self) -> str:
        """Возвращает полную карточку игрока (для личного сообщения)."""
        action_status = "✅ Доступна" if not self.action_used else "❌ Использована"
        return (
            f"🎭 *Твоя карточка (Игрок #{self.number}):*\n\n"
            f"👔 Профессия: {self.profession}\n"
            f"🧬 Биология: {self.biology}\n"
            f"❤️ Здоровье: {self.health}\n"
            f"🎯 Хобби: {self.hobby}\n"
            f"🎒 Багаж: {self.baggage}\n"
            f"😱 Фобия: {self.phobia}\n"
            f"📝 Факт: {self.fact}\n\n"
            f"🃏 *Карта действия:* {self.action_card['name']}\n"
            f"   _{self.action_card['description']}_\n"
            f"   Статус: {action_status}\n"
        )

    def reveal(self, attribute: str) -> str | None:
        """Раскрыть характеристику. Возвращает текст или None если уже раскрыта."""
        if attribute not in self.revealed:
            return None
        if self.revealed[attribute]:
            return None
        self.revealed[attribute] = True
        values = {
            "profession": f"👔 Профессия: {self.profession}",
            "biology": f"🧬 Биология: {self.biology}",
            "health": f"❤️ Здоровье: {self.health}",
            "hobby": f"🎯 Хобби: {self.hobby}",
            "baggage": f"🎒 Багаж: {self.baggage}",
            "phobia": f"😱 Фобия: {self.phobia}",
            "fact": f"📝 Факт: {self.fact}",
        }
        return values[attribute]

    def get_revealed_info(self) -> str:
        """Возвращает все раскрытые характеристики."""
        lines = []
        if self.revealed["profession"]:
            lines.append(f"  👔 {self.profession}")
        if self.revealed["biology"]:
            lines.append(f"  🧬 {self.biology}")
        if self.revealed["health"]:
            lines.append(f"  ❤️ {self.health}")
        if self.revealed["hobby"]:
            lines.append(f"  🎯 {self.hobby}")
        if self.revealed["baggage"]:
            lines.append(f"  🎒 {self.baggage}")
        if self.revealed["phobia"]:
            lines.append(f"  😱 {self.phobia}")
        if self.revealed["fact"]:
            lines.append(f"  📝 {self.fact}")
        if not lines:
            return "  _Ничего не раскрыто_"
        return "\n".join(lines)

    def use_action(self) -> bool:
        """Использовать карту действия. Возвращает True если успешно."""
        if self.action_used:
            return False
        self.action_used = True
        return True


class Game:
    """Управление одной игровой сессией."""

    STATE_LOBBY = "lobby"
    STATE_PLAYING = "playing"
    STATE_VOTING = "voting"
    STATE_FINISHED = "finished"

    def __init__(self, chat_id: int, creator_id: int):
        self.chat_id = chat_id
        self.creator_id = creator_id
        self.players: dict[int, Player] = {}
        self.player_counter = 0  # Счётчик для нумерации
        self.state = self.STATE_LOBBY
        self.catastrophe = ""
        self.bunker = ""
        self.round_number = 0
        self.votes: dict[int, int] = {}  # voter_id -> target_id
        self.current_reveal_index = 0
        self.reveal_order: list[int] = []  # порядок раскрытия
        self.sabotage_active = False  # саботаж на раунд

    def add_player(self, user_id: int, username: str) -> bool:
        """Добавить игрока. Возвращает True если успешно."""
        if self.state != self.STATE_LOBBY:
            return False
        if user_id in self.players:
            return False
        self.player_counter += 1
        self.players[user_id] = Player(user_id, username, self.player_counter)
        return True

    def start_game(self) -> str | None:
        """Начать игру. Возвращает описание катастрофы или None при ошибке."""
        if len(self.players) < 3:
            return None
        self.state = self.STATE_PLAYING
        self.catastrophe = random.choice(CATASTROPHES)
        self.bunker = random.choice(BUNKERS)
        self.round_number = 1
        self.reveal_order = list(self.players.keys())
        random.shuffle(self.reveal_order)
        self.current_reveal_index = 0

        # Список игроков с номерами
        players_list = "\n".join(
            [f"  #{p.number} {p.username}" for p in self.players.values()]
        )

        return (
            f"🌍 *КАТАСТРОФА:*\n{self.catastrophe}\n\n"
            f"🏠 *БУНКЕР:*\n{self.bunker}\n\n"
            f"👥 *Игроки:*\n{players_list}\n\n"
            f"В бункер поместится *{self.get_survivors_count()}* из "
            f"*{len(self.get_alive_players())}* игроков!\n\n"
            f"▶️ *Раунд {self.round_number}*. Каждый раскрывает одну характеристику."
        )

    def get_survivors_count(self) -> int:
        """Количество мест в бункере (половина живых игроков)."""
        alive = len(self.get_alive_players())
        count = max(1, alive // 2)
        if self.sabotage_active:
            count = max(1, count - 1)
        return count

    def get_alive_players(self) -> list[Player]:
        """Список живых игроков."""
        return [p for p in self.players.values() if p.is_alive]

    def get_current_turn_player(self) -> Player | None:
        """Текущий игрок, чья очередь раскрывать."""
        alive_order = [uid for uid in self.reveal_order
                       if uid in self.players and self.players[uid].is_alive]
        if self.current_reveal_index >= len(alive_order):
            return None
        return self.players[alive_order[self.current_reveal_index]]

    def next_turn(self):
        """Перейти к следующему ходу."""
        self.current_reveal_index += 1
        alive_order = [uid for uid in self.reveal_order
                       if uid in self.players and self.players[uid].is_alive]
        if self.current_reveal_index >= len(alive_order):
            # Все раскрыли - переход к голосованию
            self.state = self.STATE_VOTING
            self.votes = {}

    def vote(self, voter_id: int, target_id: int) -> bool:
        """Проголосовать за изгнание. Возвращает True если голос принят."""
        if self.state != self.STATE_VOTING:
            return False
        if voter_id not in self.players or not self.players[voter_id].is_alive:
            return False
        if target_id not in self.players or not self.players[target_id].is_alive:
            return False
        if voter_id == target_id:
            return False
        self.votes[voter_id] = target_id
        return True

    def all_voted(self) -> bool:
        """Все ли живые игроки проголосовали."""
        alive = self.get_alive_players()
        return len(self.votes) >= len(alive)

    def resolve_votes(self) -> tuple[Player | None, str]:
        """Подсчитать голоса и изгнать игрока. Возвращает (изгнанный, текст)."""
        vote_count: dict[int, int] = {}
        for voter_id, target_id in self.votes.items():
            voter = self.players[voter_id]
            weight = 2 if voter.double_vote else 1
            vote_count[target_id] = vote_count.get(target_id, 0) + weight

        if not vote_count:
            return None, "Никто не проголосовал!"

        max_votes = max(vote_count.values())
        candidates = [uid for uid, count in vote_count.items() if count == max_votes]

        # При ничьей — проверяем tiebreaker
        if len(candidates) > 1:
            for voter_id, target_id in self.votes.items():
                if self.players[voter_id].is_tiebreaker and target_id in candidates:
                    candidates = [target_id]
                    break

        # При ничьей без tiebreaker — случайный выбор
        kicked_id = random.choice(candidates)
        kicked_player = self.players[kicked_id]

        # Проверяем иммунитет
        if kicked_player.has_immunity:
            kicked_player.has_immunity = False
            # Убираем защищённого из кандидатов и выбираем следующего
            remaining = [uid for uid in candidates if uid != kicked_id]
            if remaining:
                kicked_id = random.choice(remaining)
                kicked_player = self.players[kicked_id]
            else:
                # Все с иммунитетом — никто не выгнан
                self._reset_round_effects()
                return None, "🛡 Игрок с наибольшим числом голосов использовал иммунитет! Никто не изгнан.\n\n▶️ Следующий раунд!"

        kicked_player.is_alive = False

        # Формируем результат голосования
        result_lines = ["📊 *Результаты голосования:*\n"]
        for uid, count in sorted(vote_count.items(), key=lambda x: -x[1]):
            player = self.players[uid]
            marker = " ❌" if uid == kicked_id else ""
            result_lines.append(f"• {player.display_name}: {count} голос(ов){marker}")

        result_lines.append(f"\n🚪 *{kicked_player.display_name}* покидает бункер!")
        result_lines.append(f"\nПолная карточка изгнанного:")
        result_lines.append(kicked_player.get_card())

        # Сбрасываем эффекты раунда
        self._reset_round_effects()

        # Проверяем окончание игры
        alive = self.get_alive_players()
        if len(alive) <= self.get_survivors_count():
            self.state = self.STATE_FINISHED
            survivors = "\n".join([f"• {p.display_name}" for p in alive])
            result_lines.append(f"\n🎉 *Игра окончена!*\nВыжившие в бункере:\n{survivors}")
        else:
            # Следующий раунд
            self.round_number += 1
            self.state = self.STATE_PLAYING
            self.current_reveal_index = 0
            self.votes = {}
            self.sabotage_active = False
            result_lines.append(
                f"\n▶️ *Раунд {self.round_number}*. "
                f"Осталось игроков: {len(alive)}. "
                f"Мест в бункере: {self.get_survivors_count()}."
            )

        return kicked_player, "\n".join(result_lines)

    def _reset_round_effects(self):
        """Сброс эффектов, действующих один раунд."""
        for p in self.players.values():
            p.has_immunity = False
            p.double_vote = False
            p.is_tiebreaker = False
        self.sabotage_active = False

    # ==================== КАРТЫ ДЕЙСТВИЯ ====================

    def use_action_card(self, user_id: int, target_id: int | None = None) -> str | None:
        """
        Использовать карту действия.
        Возвращает текст результата или None при ошибке.
        """
        if user_id not in self.players:
            return None
        player = self.players[user_id]
        if player.action_used:
            return None
        if not player.is_alive:
            return None

        card_type = player.action_card["type"]
        card_name = player.action_card["name"]

        # Обрабатываем разные типы карт
        if card_type == "immunity":
            player.use_action()
            player.has_immunity = True
            return f"🛡 *{player.display_name}* активирует иммунитет! Нельзя выгнать в этом раунде."

        elif card_type == "double_vote":
            player.use_action()
            player.double_vote = True
            return f"🗳 *{player.display_name}* активирует двойной голос! Голос считается за два."

        elif card_type == "tiebreaker":
            player.use_action()
            player.is_tiebreaker = True
            return f"🎯 *{player.display_name}* активирует снайпера! При ничьей голос решающий."

        elif card_type == "heal":
            player.use_action()
            player.health = "Абсолютно здоров"
            return f"💊 *{player.display_name}* исцеляется! Здоровье теперь: Абсолютно здоров."

        elif card_type == "new_profession":
            player.use_action()
            old = player.profession
            player.profession = random.choice(PROFESSIONS)
            return (f"🎭 *{player.display_name}* перевоплощается!\n"
                    f"Новая профессия: {player.profession}")

        elif card_type == "new_baggage":
            player.use_action()
            player.baggage = random.choice(BAGGAGE)
            return (f"🎒 *{player.display_name}* получает новый багаж!\n"
                    f"Новый предмет: {player.baggage}")

        elif card_type == "sabotage":
            player.use_action()
            self.sabotage_active = True
            return (f"⚡ *{player.display_name}* саботирует бункер!\n"
                    f"Вместимость бункера уменьшена на 1 в этом раунде.")

        elif card_type == "swap_profession":
            if target_id is None or target_id not in self.players:
                return None
            target = self.players[target_id]
            if not target.is_alive:
                return None
            player.use_action()
            player.profession, target.profession = target.profession, player.profession
            return (f"🔄 *{player.display_name}* обменялся профессией с "
                    f"*{target.display_name}*!")

        elif card_type == "spy":
            if target_id is None or target_id not in self.players:
                return None
            target = self.players[target_id]
            if not target.is_alive:
                return None
            player.use_action()
            # Находим нераскрытую характеристику
            unrevealed = [k for k, v in target.revealed.items() if not v]
            if not unrevealed:
                return f"🔍 У *{target.display_name}* все характеристики уже раскрыты!"
            attr = random.choice(unrevealed)
            values = {
                "profession": f"👔 Профессия: {target.profession}",
                "biology": f"🧬 Биология: {target.biology}",
                "health": f"❤️ Здоровье: {target.health}",
                "hobby": f"🎯 Хобби: {target.hobby}",
                "baggage": f"🎒 Багаж: {target.baggage}",
                "phobia": f"😱 Фобия: {target.phobia}",
                "fact": f"📝 Факт: {target.fact}",
            }
            # Возвращаем текст для отправки в ЛС
            return f"SPY_PRIVATE|🔍 Ты подсмотрел у *{target.display_name}*:\n{values[attr]}"

        elif card_type == "expose":
            if target_id is None or target_id not in self.players:
                return None
            target = self.players[target_id]
            if not target.is_alive:
                return None
            player.use_action()
            # Раскрываем 2 случайные характеристики
            unrevealed = [k for k, v in target.revealed.items() if not v]
            if not unrevealed:
                return f"👁 У *{target.display_name}* все характеристики уже раскрыты!"
            revealed_attrs = random.sample(unrevealed, min(2, len(unrevealed)))
            results = []
            for attr in revealed_attrs:
                result = target.reveal(attr)
                if result:
                    results.append(result)
            return (f"👁 *{player.display_name}* разоблачает *{target.display_name}*!\n"
                    f"Раскрыто:\n" + "\n".join(results))

        elif card_type == "rescue":
            dead_players = [p for p in self.players.values() if not p.is_alive]
            if not dead_players:
                return None
            if target_id is None or target_id not in self.players:
                return None
            target = self.players[target_id]
            if target.is_alive:
                return None
            player.use_action()
            target.is_alive = True
            return f"❤️ *{player.display_name}* спасает *{target.display_name}*! Игрок возвращается в игру."

        elif card_type == "reorder":
            player.use_action()
            # Ставим игрока следующим
            alive_order = [uid for uid in self.reveal_order
                           if uid in self.players and self.players[uid].is_alive]
            if user_id in alive_order:
                alive_order.remove(user_id)
                insert_pos = min(self.current_reveal_index, len(alive_order))
                alive_order.insert(insert_pos, user_id)
                self.reveal_order = alive_order
            return f"🔀 *{player.display_name}* меняет порядок! Ходит следующим."

        elif card_type == "joker":
            player.use_action()
            # Заменяем случайную характеристику
            attrs = ["profession", "biology", "health", "hobby", "baggage", "phobia", "fact"]
            attr = random.choice(attrs)
            sources = {
                "profession": PROFESSIONS,
                "biology": BIOLOGY,
                "health": HEALTH,
                "hobby": HOBBY,
                "baggage": BAGGAGE,
                "phobia": PHOBIAS,
                "fact": FACTS,
            }
            new_val = random.choice(sources[attr])
            setattr(player, attr, new_val)
            attr_names = {
                "profession": "Профессия", "biology": "Биология",
                "health": "Здоровье", "hobby": "Хобби",
                "baggage": "Багаж", "phobia": "Фобия", "fact": "Факт"
            }
            return (f"🃏 *{player.display_name}* использует джокера!\n"
                    f"Заменена характеристика: {attr_names[attr]}")

        elif card_type == "cancel":
            player.use_action()
            return f"🚫 *{player.display_name}* активирует заглушку! (Используйте в ответ на чужую карту)"

        elif card_type == "alliance":
            if target_id is None or target_id not in self.players:
                return None
            target = self.players[target_id]
            if not target.is_alive:
                return None
            player.use_action()
            return (f"🤝 *{player.display_name}* заключает союз с *{target.display_name}*!\n"
                    f"Их нельзя выгнать по одному (решение за группой).")

        return None


# Хранилище активных игр (chat_id -> Game)
active_games: dict[int, Game] = {}
