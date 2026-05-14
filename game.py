"""
Логика игры "Бункер"
"""
import random
from data import (
    PROFESSIONS, BIOLOGY, HEALTH, HOBBY,
    BAGGAGE, PHOBIAS, FACTS, CATASTROPHES, BUNKERS
)


class Player:
    """Игрок с набором характеристик."""

    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.profession = random.choice(PROFESSIONS)
        self.biology = random.choice(BIOLOGY)
        self.health = random.choice(HEALTH)
        self.hobby = random.choice(HOBBY)
        self.baggage = random.choice(BAGGAGE)
        self.phobia = random.choice(PHOBIAS)
        self.fact = random.choice(FACTS)
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

    def get_card(self) -> str:
        """Возвращает полную карточку игрока (для личного сообщения)."""
        return (
            f"🎭 *Твоя карточка:*\n\n"
            f"👔 Профессия: {self.profession}\n"
            f"🧬 Биология: {self.biology}\n"
            f"❤️ Здоровье: {self.health}\n"
            f"🎯 Хобби: {self.hobby}\n"
            f"🎒 Багаж: {self.baggage}\n"
            f"😱 Фобия: {self.phobia}\n"
            f"📝 Факт: {self.fact}\n"
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
            lines.append(f"👔 Профессия: {self.profession}")
        if self.revealed["biology"]:
            lines.append(f"🧬 Биология: {self.biology}")
        if self.revealed["health"]:
            lines.append(f"❤️ Здоровье: {self.health}")
        if self.revealed["hobby"]:
            lines.append(f"🎯 Хобби: {self.hobby}")
        if self.revealed["baggage"]:
            lines.append(f"🎒 Багаж: {self.baggage}")
        if self.revealed["phobia"]:
            lines.append(f"😱 Фобия: {self.phobia}")
        if self.revealed["fact"]:
            lines.append(f"📝 Факт: {self.fact}")
        if not lines:
            return "Ничего не раскрыто"
        return "\n".join(lines)


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
        self.state = self.STATE_LOBBY
        self.catastrophe = ""
        self.bunker = ""
        self.round_number = 0
        self.votes: dict[int, int] = {}  # voter_id -> target_id
        self.current_reveal_index = 0
        self.reveal_order: list[int] = []  # порядок раскрытия

    def add_player(self, user_id: int, username: str) -> bool:
        """Добавить игрока. Возвращает True если успешно."""
        if self.state != self.STATE_LOBBY:
            return False
        if user_id in self.players:
            return False
        self.players[user_id] = Player(user_id, username)
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
        return (
            f"🌍 *Катастрофа:* {self.catastrophe}\n"
            f"🏠 *Бункер:* {self.bunker}\n\n"
            f"В бункер поместится только *{self.get_survivors_count()}* из "
            f"*{len(self.get_alive_players())}* игроков!\n\n"
            f"Раунд {self.round_number}. Каждый игрок раскрывает одну характеристику."
        )

    def get_survivors_count(self) -> int:
        """Количество мест в бункере (половина живых игроков)."""
        alive = len(self.get_alive_players())
        return max(1, alive // 2)

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
        for target_id in self.votes.values():
            vote_count[target_id] = vote_count.get(target_id, 0) + 1

        if not vote_count:
            return None, "Никто не проголосовал!"

        max_votes = max(vote_count.values())
        candidates = [uid for uid, count in vote_count.items() if count == max_votes]

        # При ничьей - случайный выбор
        kicked_id = random.choice(candidates)
        kicked_player = self.players[kicked_id]
        kicked_player.is_alive = False

        # Формируем результат голосования
        result_lines = ["📊 *Результаты голосования:*\n"]
        for uid, count in sorted(vote_count.items(), key=lambda x: -x[1]):
            player = self.players[uid]
            marker = " ❌" if uid == kicked_id else ""
            result_lines.append(f"• {player.username}: {count} голос(ов){marker}")

        result_lines.append(f"\n🚪 *{kicked_player.username}* покидает бункер!")
        result_lines.append(f"\nПолная карточка изгнанного:")
        result_lines.append(kicked_player.get_card())

        # Проверяем окончание игры
        alive = self.get_alive_players()
        if len(alive) <= self.get_survivors_count():
            self.state = self.STATE_FINISHED
            survivors = "\n".join([f"• {p.username}" for p in alive])
            result_lines.append(f"\n🎉 *Игра окончена!*\nВыжившие в бункере:\n{survivors}")
        else:
            # Следующий раунд
            self.round_number += 1
            self.state = self.STATE_PLAYING
            self.current_reveal_index = 0
            self.votes = {}
            result_lines.append(
                f"\n▶️ *Раунд {self.round_number}*. "
                f"Осталось игроков: {len(alive)}. "
                f"Мест в бункере: {self.get_survivors_count()}."
            )

        return kicked_player, "\n".join(result_lines)


# Хранилище активных игр (chat_id -> Game)
active_games: dict[int, Game] = {}
