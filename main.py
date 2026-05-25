from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
import json
import os

# 数据类定义
class Player:
    """玩家类"""
    def __init__(self, user_id, user_name):
        self.user_id = user_id
        self.user_name = user_name
        self.is_alive = True
        self.role = None  # citizen, undercover, whiteboard
        self.word = None

class GameRoom:
    """游戏房间类"""
    def __init__(self, room_id, owner_id, owner_name):
        self.room_id = room_id
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.players = []  # Player对象列表
        self.status = "waiting"  # waiting, playing, ended
        self.speech_order = []  # 发言顺序，存储player对象
        self.current_speaker_index = 0  # 当前发言玩家索引
        self.votes = {}  # user_id: voted_user_id
        self.round = 1  # 当前轮次

# 主插件类
@register("undercover", "YourName", "谁是卧底游戏插件", "1.2.0")
class UndercoverPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.game_rooms = {}  # room_id: GameRoom对象
        self.user_rooms = {}  # user_id: room_id，记录用户所在房间
        self.word_pairs_file = "word_pairs.json"  # 词语库文件
        self.word_pairs = self.load_word_pairs()  # 加载词语库
        self.room_counter = 1  # 房间ID计数器

    async def initialize(self):
        """插件初始化"""
        logger.info("谁是卧底插件初始化成功")
        # 确保词语库文件存在
        if not os.path.exists(self.word_pairs_file):
            self.save_word_pairs(self.get_default_word_pairs())
            self.word_pairs = self.get_default_word_pairs()

    @filter.command_group("uc")
    def uc(self):
        pass

    @uc.command("")
    async def uc_help(self, event: AstrMessageEvent):
        help_text = (
            "谁是卧底游戏指令：\n"
            "/uc create - 创建游戏房间\n"
            "/uc join <房间号> - 加入游戏房间\n"
            "/uc start - 开始游戏（房主）\n"
            "/uc leave - 离开当前房间\n"
            "/uc say <内容> - 游戏中发言\n"
            "/uc vote <玩家> - 游戏中投票\n"
            "/uc end - 结束游戏（房主）\n"
            "/uc add <词语1> <词语2> - 添加词语对\n"
            "/uc word - 查看我的词语(请私聊使用)\n"
            "/uc list - 查看游戏列表\n"
        )
        yield event.plain_result(help_text)

    @uc.command("create")
    async def create_game(self, event: AstrMessageEvent):
        """创建游戏房间"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        if user_id in self.user_rooms:
            yield event.plain_result("你已在其他游戏房间中，请先离开")
            return

        room_id = str(self.room_counter)
        self.room_counter += 1

        game_room = GameRoom(room_id, user_id, user_name)
        self.game_rooms[room_id] = game_room

        player = Player(user_id, user_name)
        game_room.players.append(player)
        self.user_rooms[user_id] = room_id

        yield event.plain_result(f"游戏房间创建成功！房间号：{room_id}\n"
                                f"房主：{user_name}\n"
                                f"使用 /uc join {room_id} 邀请其他玩家加入")

    @uc.command("join")
    async def join_game(self, event: AstrMessageEvent, room_id: str = ""):
        """加入游戏房间"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        if not room_id:
            yield event.plain_result("请输入房间号，格式：/uc join <房间号>")
            return

        if room_id not in self.game_rooms:
            yield event.plain_result("房间不存在，请检查房间号")
            return

        game_room = self.game_rooms[room_id]

        if game_room.status != "waiting":
            yield event.plain_result("该房间游戏已开始，无法加入")
            return

        if user_id in self.user_rooms and self.user_rooms[user_id] == room_id:
            yield event.plain_result("你已在该房间中")
            return

        if user_id in self.user_rooms:
            yield event.plain_result("你已在其他游戏房间中，请先离开")
            return

        player = Player(user_id, user_name)
        game_room.players.append(player)
        self.user_rooms[user_id] = room_id

        async for r in self.notify_room(event, f"玩家 {user_name} 加入了游戏"):
            yield r
        yield event.plain_result(f"成功加入房间 {room_id}")

    @uc.command("start")
    async def start_game(self, event: AstrMessageEvent):
        """开始游戏"""
        user_id = event.get_sender_id()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]

        if game_room.owner_id != user_id:
            yield event.plain_result("只有房主可以开始游戏")
            return

        if game_room.status != "waiting":
            yield event.plain_result("游戏已开始")
            return

        if len(game_room.players) < 3:
            yield event.plain_result("玩家数量不足，至少需要3人")
            return

        game_room.status = "playing"

        word_pair = random.choice(self.word_pairs)
        citizen_word, undercover_word = word_pair

        num_players = len(game_room.players)
        if num_players <= 5:
            num_undercover = 1
        elif num_players <= 7:
            num_undercover = 2
        else:
            num_undercover = 3

        random.shuffle(game_room.players)

        for i, player in enumerate(game_room.players):
            if i < num_undercover:
                player.role = "undercover"
                player.word = undercover_word
            else:
                player.role = "citizen"
                player.word = citizen_word

        game_room.speech_order = game_room.players.copy()
        game_room.current_speaker_index = 0

        async for r in self.notify_room(event, "游戏开始！\n"
                              f"本轮词语：[机密]\n"
                              f"玩家列表：{', '.join(p.user_name for p in game_room.players)}\n"
                              "请私聊机器人发送 /uc word 查看你的词语"):
            yield r

        current_player = game_room.speech_order[game_room.current_speaker_index]
        async for r in self.notify_room(event, f"第 {game_room.round} 轮发言开始！\n"
                              f"当前发言玩家：{current_player.user_name}"):
            yield r

    @uc.command("leave")
    async def leave_game(self, event: AstrMessageEvent):
        """离开游戏房间"""
        user_id = event.get_sender_id()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]
        user_name = event.get_sender_name()

        game_room.players = [p for p in game_room.players if p.user_id != user_id]
        del self.user_rooms[user_id]

        if game_room.owner_id == user_id:
            if game_room.players:
                new_owner = game_room.players[0]
                game_room.owner_id = new_owner.user_id
                game_room.owner_name = new_owner.user_name
                async for r in self.notify_room(event, f"房主 {user_name} 已离开，新房主：{new_owner.user_name}"):
                    yield r
            else:
                del self.game_rooms[room_id]
                yield event.plain_result("你已离开游戏房间")
                return
        else:
            async for r in self.notify_room(event, f"玩家 {user_name} 已离开游戏"):
                yield r

        yield event.plain_result("你已离开游戏房间")

    @uc.command("say")
    async def say(self, event: AstrMessageEvent, *content: str):
        """游戏中发言"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        text = " ".join(content).strip()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]

        if game_room.status != "playing":
            yield event.plain_result("游戏未开始")
            return

        current_player = game_room.speech_order[game_room.current_speaker_index]
        if current_player.user_id != user_id:
            yield event.plain_result(f"当前不是你的发言轮次，现在是 {current_player.user_name} 发言")
            return

        player = next(p for p in game_room.players if p.user_id == user_id)
        if not player.is_alive:
            yield event.plain_result("你已被淘汰，无法发言")
            return

        async for r in self.notify_room(event, f"{user_name}：{text}"):
            yield r

        game_room.current_speaker_index += 1

        if game_room.current_speaker_index >= len(game_room.speech_order):
            async for r in self.notify_room(event, "发言结束，开始投票！\n"
                                  "请使用 /uc vote <玩家> 进行投票"):
                yield r
        else:
            next_player = game_room.speech_order[game_room.current_speaker_index]
            async for r in self.notify_room(event, f"下一位发言玩家：{next_player.user_name}"):
                yield r

    @uc.command("vote")
    async def vote(self, event: AstrMessageEvent, target_name: str = ""):
        """游戏中投票"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]

        if game_room.status != "playing":
            yield event.plain_result("游戏未开始")
            return

        if game_room.current_speaker_index < len(game_room.speech_order):
            yield event.plain_result("当前仍在发言阶段，无法投票")
            return

        voter = next(p for p in game_room.players if p.user_id == user_id)
        if not voter.is_alive:
            yield event.plain_result("你已被淘汰，无法投票")
            return

        target_player = None
        for p in game_room.players:
            if p.is_alive and target_name in p.user_name:
                target_player = p
                break

        if not target_player:
            yield event.plain_result(f"未找到存活玩家：{target_name}")
            return

        game_room.votes[user_id] = target_player.user_id
        async for r in self.notify_room(event, f"{user_name} 投票给了 {target_player.user_name}"):
            yield r

        alive_players = [p for p in game_room.players if p.alive]
        if len(game_room.votes) >= len(alive_players):
            vote_counts = {}
            for voted_id in game_room.votes.values():
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

            max_votes = max(vote_counts.values())
            eliminated_players = [p for p in alive_players if vote_counts.get(p.user_id, 0) == max_votes]

            if len(eliminated_players) == 1:
                eliminated = eliminated_players[0]
                eliminated.is_alive = False
                role_name = "卧底" if eliminated.role == "undercover" else "平民"

                result_msg = (f"🗳️ 投票结果：\n"
                            f"玩家 {eliminated.user_name} 被票出局！\n"
                            f"👤 身份：{role_name}\n"
                            f"📝 词语：{eliminated.word}")

                async for r in self.notify_room(event, result_msg):
                    yield r

                async for r in self.check_winner(game_room, event):
                    yield r
                if game_room.status == "ended":
                    return

                game_room.round += 1
                game_room.current_speaker_index = 0
                game_room.votes.clear()

                game_room.speech_order = [p for p in game_room.players if p.alive]
                random.shuffle(game_room.speech_order)

                current_player = game_room.speech_order[game_room.current_speaker_index]
                async for r in self.notify_room(event, f"第 {game_room.round} 轮发言开始！\n"
                                      f"当前发言玩家：{current_player.user_name}"):
                    yield r
            else:
                async for r in self.notify_room(event, f"投票结果平票：{', '.join(p.user_name for p in eliminated_players)}\n"
                                      "重新投票！"):
                    yield r
                game_room.votes.clear()

    async def check_winner(self, game_room: GameRoom, event: AstrMessageEvent):
        """检查游戏是否结束"""
        alive_players = [p for p in game_room.players if p.alive]
        alive_citizens = [p for p in alive_players if p.role == "citizen"]
        alive_undercovers = [p for p in alive_players if p.role == "undercover"]

        winner = None
        if len(alive_undercovers) == 0:
            winner = "平民"
        elif len(alive_undercovers) >= len(alive_citizens):
            winner = "卧底"

        if winner:
            player_list_str = "\n".join([
                f"{p.user_name}：{'卧底' if p.role == 'undercover' else '平民'} - {p.word}"
                for p in game_room.players
            ])

            msg = f"游戏结束！\n{winner}胜利！\n\n全员身份公示：\n{player_list_str}"

            async for r in self.notify_room(event, msg):
                yield r
            game_room.status = "ended"

    @uc.command("end")
    async def end_game(self, event: AstrMessageEvent):
        """结束游戏"""
        user_id = event.get_sender_id()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]

        if game_room.owner_id != user_id:
            yield event.plain_result("只有房主可以结束游戏")
            return

        async for r in self.notify_room(event, "游戏已结束"):
            yield r

        for player in game_room.players:
            if player.user_id in self.user_rooms:
                del self.user_rooms[player.user_id]

        del self.game_rooms[room_id]

    @uc.command("add")
    async def add_word_pair(self, event: AstrMessageEvent, word1: str = "", word2: str = ""):
        """添加词语对"""
        if not word1 or not word2:
            yield event.plain_result("请输入两个词语，格式：/uc add <词语1> <词语2>")
            return

        if [word1, word2] not in self.word_pairs and [word2, word1] not in self.word_pairs:
            self.word_pairs.append([word1, word2])
            self.save_word_pairs(self.word_pairs)
            yield event.plain_result(f"词语对添加成功：{word1} - {word2}")
        else:
            yield event.plain_result("该词语对已存在")

    @uc.command("list")
    async def list_games(self, event: AstrMessageEvent):
        """查看游戏列表"""
        if not self.game_rooms:
            yield event.plain_result("当前没有游戏房间")
            return

        game_list = "当前游戏房间列表：\n"
        for room_id, game_room in self.game_rooms.items():
            game_list += f"房间号：{room_id} | 状态：{game_room.status} | 玩家数：{len(game_room.players)}\n"

        yield event.plain_result(game_list)

    @uc.command("word")
    async def get_word(self, event: AstrMessageEvent):
        """获取自己的词语（建议私聊使用）"""
        user_id = event.get_sender_id()

        if user_id not in self.user_rooms:
            yield event.plain_result("你不在任何游戏房间中")
            return

        room_id = self.user_rooms[user_id]
        game_room = self.game_rooms[room_id]

        if game_room.status != "playing":
            yield event.plain_result("游戏未开始")
            return

        player = next((p for p in game_room.players if p.user_id == user_id), None)
        if not player:
            yield event.plain_result("未找到玩家信息")
            return

        if not player.is_alive:
            yield event.plain_result("你已被淘汰")
            return

        yield event.plain_result(f"你的词语是：{player.word}\n(请确保你在私聊中查看此消息)")

    async def notify_room(self, event: AstrMessageEvent, message: str):
        """通知房间内所有玩家"""
        yield event.plain_result(message)

    def load_word_pairs(self) -> list:
        """加载词语库"""
        if os.path.exists(self.word_pairs_file):
            try:
                with open(self.word_pairs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_word_pairs()
        else:
            return self.get_default_word_pairs()

    def save_word_pairs(self, word_pairs: list):
        """保存词语库"""
        with open(self.word_pairs_file, 'w', encoding='utf-8') as f:
            json.dump(word_pairs, f, ensure_ascii=False, indent=2)

    def get_default_word_pairs(self) -> list:
        """获取默认词语库"""
        return [
            ["苹果", "梨"],
            ["电脑", "手机"],
            ["篮球", "足球"],
            ["牛奶", "豆浆"],
            ["面包", "蛋糕"],
            ["红色", "蓝色"],
            ["猫", "狗"],
            ["书", "杂志"],
            ["沙发", "椅子"],
            ["电视", "电影"],
            ["自行车", "电动车"],
            ["火车", "高铁"],
            ["飞机", "直升机"],
            ["老师", "学生"],
            ["医生", "护士"]
        ]

    async def terminate(self):
        """插件销毁时调用"""
        logger.info("谁是卧底插件已卸载")
