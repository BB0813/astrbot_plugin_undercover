import time

# 游戏状态类
class GameState:
    # 房间状态枚举
    WAITING = "waiting"
    PLAYING = "playing"
    ENDED = "ended"
    
    # 玩家身份枚举
    CIVILIAN = "civilian"
    UNDERCOVER = "undercover"
    BLANK = "blank"
    
    # 游戏阶段枚举
    ROLE_ASSIGNMENT = "role_assignment"
    SPEAKING = "speaking"
    VOTING = "voting"
    ELIMINATION = "elimination"
    GAME_OVER = "game_over"

# 玩家类
class Player:
    def __init__(self, user_id: str, user_name: str):
        self.user_id = user_id  # 用户唯一标识
        self.user_name = user_name  # 用户名
        self.role = None  # 身份：civilian(平民)/undercover(卧底)/blank(白板)
        self.word = None  # 分配的词语
        self.is_alive = True  # 是否存活
        self.has_spoken = False  # 本回合是否已发言
        self.voted_for = None  # 本回合投票给谁
        self.join_time = None  # 加入房间时间
        self.game_stats = {
            "total_games": 0,  # 总游戏次数
            "wins": 0,  # 获胜次数
            "civilian_games": 0,  # 平民身份次数
            "civilian_wins": 0,  # 平民获胜次数
            "undercover_games": 0,  # 卧底身份次数
            "undercover_wins": 0,  # 卧底获胜次数
            "blank_games": 0,  # 白板身份次数
            "blank_wins": 0,  # 白板获胜次数
            "survival_rate": 0.0,  # 存活率
            "avg_survival_rounds": 0.0,  # 平均存活回合数
            "total_speeches": 0,  # 总发言次数
            "total_votes": 0,  # 总投票次数
            "correct_votes": 0,  # 正确投票次数
            "created_at": time.time(),  # 统计创建时间
            "last_game_time": None,  # 最后游戏时间
        }  # 游戏统计数据
    
    def reset(self):
        """重置玩家游戏状态"""
        self.role = None
        self.word = None
        self.is_alive = True
        self.has_spoken = False
        self.voted_for = None
    
    def update_stats(self, is_winner: bool, survival_rounds: int = 0):
        """更新玩家游戏统计"""
        self.game_stats["total_games"] += 1
        self.game_stats["last_game_time"] = time.time()
        
        if is_winner:
            self.game_stats["wins"] += 1
        
        # 更新身份相关统计
        if self.role == GameState.CIVILIAN:
            self.game_stats["civilian_games"] += 1
            if is_winner:
                self.game_stats["civilian_wins"] += 1
        elif self.role == GameState.UNDERCOVER:
            self.game_stats["undercover_games"] += 1
            if is_winner:
                self.game_stats["undercover_wins"] += 1
        elif self.role == GameState.BLANK:
            self.game_stats["blank_games"] += 1
            if is_winner:
                self.game_stats["blank_wins"] += 1
        
        # 更新存活回合数
        total_rounds = self.game_stats["total_games"] * self.game_stats["avg_survival_rounds"] + survival_rounds
        self.game_stats["avg_survival_rounds"] = round(total_rounds / self.game_stats["total_games"], 2)
        
        # 更新存活率
        if self.game_stats["total_games"] > 0:
            self.game_stats["survival_rate"] = round(
                self.game_stats["wins"] / self.game_stats["total_games"] * 100, 2
            )

# 游戏房间类
class GameRoom:
    def __init__(self, room_id: int, owner_id: str):
        self.room_id = room_id  # 房间唯一标识
        self.owner_id = owner_id  # 房主ID
        self.players = {}  # 玩家字典 {user_id: Player}
        self.status = GameState.WAITING  # 房间状态：waiting(等待中)/playing(游戏中)/ended(已结束)
        self.current_round = 1  # 当前回合数
        self.current_speaker_index = 0  # 当前发言玩家索引
        self.speaking_order = []  # 发言顺序列表
        self.votes = {}  # 投票记录 {voter_id: voted_id}
        self.eliminated_players = []  # 已淘汰玩家列表 [(user_id, role)]
        self.game_start_time = None  # 游戏开始时间
        self.game_end_time = None  # 游戏结束时间
        self.words = None  # 本轮词语 (civilian_word, undercover_word)
        self.undercover_count = GameConfig.DEFAULT_UNDERCOVER_COUNT  # 卧底数量
        self.blank_count = GameConfig.DEFAULT_BLANK_COUNT  # 白板数量
        self.speak_time = GameConfig.MAX_SPEAK_TIME  # 发言时间限制（秒）
        self.vote_time = GameConfig.MAX_VOTE_TIME  # 投票时间限制（秒）
        self.last_activity_time = time.time()  # 最后活动时间
        self.settings = {
            "allow_spectators": False,  # 是否允许观战
            "auto_start": False,  # 是否自动开始
            "min_players_auto_start": 4,  # 自动开始最小玩家数
            "game_mode": "classic",  # 游戏模式：classic(经典), happy(欢乐), advanced(高级), team(团队)
        }  # 房间设置
        self.current_phase = None  # 当前游戏阶段
        self.game_mode = "classic"  # 当前游戏模式
        self.current_phase_start_time = None  # 当前阶段开始时间
        self.spectators = {}  # 观战者字典 {user_id: spectator_info}
    
    def add_player(self, player: Player):
        """添加玩家"""
        self.players[player.user_id] = player
        player.join_time = time.time()
        self.last_activity_time = time.time()
    
    def remove_player(self, user_id: str):
        """移除玩家"""
        if user_id in self.players:
            del self.players[user_id]
        if user_id in self.votes:
            del self.votes[user_id]
        self.last_activity_time = time.time()
    
    def reset(self):
        """重置房间状态"""
        self.status = GameState.WAITING
        self.current_round = 1
        self.current_speaker_index = 0
        self.speaking_order = []
        self.votes = {}
        self.eliminated_players = []
        self.game_start_time = None
        self.game_end_time = None
        self.words = None
        self.current_phase = None
        self.current_phase_start_time = None
        self.spectators = {}
        for player in self.players.values():
            player.reset()
        self.last_activity_time = time.time()
    
    def get_alive_players(self):
        """获取存活玩家列表"""
        return [player for player in self.players.values() if player.is_alive]
    
    def get_player_by_name(self, name: str):
        """通过用户名获取玩家"""
        for player in self.players.values():
            if player.user_name == name:
                return player
        return None
    
    def update_activity_time(self):
        """更新活动时间"""
        self.last_activity_time = time.time()

# 导入配置
from .config import GameConfig
