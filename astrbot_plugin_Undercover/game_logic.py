import random
import time
from .models import GameState
from .config import GameConfig

class GameLogic:
    def __init__(self, game_manager):
        self.game_manager = game_manager
    
    def assign_roles(self, room):
        """分配身份和词语"""
        # 根据游戏模式调整设置
        self.adjust_settings_by_mode(room)
        
        # 随机选择词语
        civilian_word, undercover_word = random.choice(self.game_manager.word_list)
        room.words = (civilian_word, undercover_word)
        
        # 生成玩家列表
        players = list(room.players.values())
        random.shuffle(players)
        
        # 分配身份
        roles = []
        # 添加卧底
        for _ in range(room.undercover_count):
            roles.append(GameState.UNDERCOVER)
        # 添加白板
        for _ in range(room.blank_count):
            roles.append(GameState.BLANK)
        # 添加平民
        civilian_count = len(players) - len(roles)
        for _ in range(civilian_count):
            roles.append(GameState.CIVILIAN)
        
        # 随机打乱身份顺序
        random.shuffle(roles)
        
        # 分配身份和词语
        for player, role in zip(players, roles):
            player.role = role
            if role == GameState.CIVILIAN:
                player.word = civilian_word
            elif role == GameState.UNDERCOVER:
                player.word = undercover_word
            else:  # BLANK
                player.word = None
        
        # 生成发言顺序
        room.speaking_order = [player.user_id for player in players]
        room.current_speaker_index = 0
        room.current_phase = GameState.ROLE_ASSIGNMENT
        room.current_phase_start_time = time.time()
    
    def adjust_settings_by_mode(self, room):
        """根据游戏模式调整设置"""
        game_mode = room.settings.get("game_mode", "classic")
        room.game_mode = game_mode
        
        total_players = len(room.players)
        
        if game_mode == "classic":
            # 经典模式：标准设置
            room.undercover_count = self.calculate_undercover_count(total_players)
            room.blank_count = self.calculate_blank_count(total_players)
        elif game_mode == "happy":
            # 欢乐模式：更多白板，更短发言时间
            room.undercover_count = self.calculate_undercover_count(total_players)
            room.blank_count = max(1, self.calculate_blank_count(total_players))
            room.speak_time = int(GameConfig.MAX_SPEAK_TIME * 0.8)  # 发言时间缩短20%
            room.vote_time = int(GameConfig.MAX_VOTE_TIME * 0.8)  # 投票时间缩短20%
        elif game_mode == "advanced":
            # 高级模式：更多卧底，更长发言时间
            room.undercover_count = min(3, self.calculate_undercover_count(total_players) + 1)
            room.blank_count = self.calculate_blank_count(total_players)
            room.speak_time = int(GameConfig.MAX_SPEAK_TIME * 1.2)  # 发言时间延长20%
            room.vote_time = int(GameConfig.MAX_VOTE_TIME * 1.2)  # 投票时间延长20%
        elif game_mode == "team":
            # 团队模式：2组对抗，每组有自己的卧底
            room.undercover_count = 2  # 每组1个卧底
            room.blank_count = 0  # 团队模式无白板
        
        # 更新发言和投票时间
        room.speak_time = max(30, room.speak_time)  # 最短30秒
        room.vote_time = max(15, room.vote_time)  # 最短15秒
    
    def get_current_speaker(self, room):
        """获取当前发言玩家ID"""
        if not room.speaking_order:
            return None
        if room.current_speaker_index >= len(room.speaking_order):
            return None
        return room.speaking_order[room.current_speaker_index]
    
    def next_speaker(self, room):
        """切换到下一个发言玩家"""
        room.current_speaker_index += 1
        if room.current_speaker_index >= len(room.speaking_order):
            return None  # 发言结束
        return room.speaking_order[room.current_speaker_index]
    
    def start_new_round(self, room):
        """开始新回合"""
        room.current_round += 1
        room.current_speaker_index = 0
        room.votes = {}
        room.current_phase = GameState.SPEAKING
        room.current_phase_start_time = time.time()
        
        # 重置玩家发言状态
        for player in room.players.values():
            if player.is_alive:
                player.has_spoken = False
        
        # 更新发言顺序（存活玩家）
        alive_players = [p for p in room.players.values() if p.is_alive]
        random.shuffle(alive_players)
        room.speaking_order = [p.user_id for p in alive_players]
    
    def count_votes(self, room):
        """统计投票结果"""
        vote_counts = {}
        for voted_id in room.votes.values():
            if voted_id in vote_counts:
                vote_counts[voted_id] += 1
            else:
                vote_counts[voted_id] = 1
        return vote_counts
    
    def get_eliminated_player(self, room):
        """确定被淘汰的玩家"""
        vote_counts = self.count_votes(room)
        if not vote_counts:
            return None, None
        
        # 找出得票最多的玩家
        max_votes = max(vote_counts.values())
        candidates = [user_id for user_id, count in vote_counts.items() if count == max_votes]
        
        # 如果平票，随机选择一个
        if len(candidates) > 1:
            eliminated_id = random.choice(candidates)
        else:
            eliminated_id = candidates[0]
        
        eliminated_player = room.players[eliminated_id]
        return eliminated_id, eliminated_player.role
    
    def eliminate_player(self, room, user_id):
        """淘汰玩家"""
        if user_id not in room.players:
            return False
        
        player = room.players[user_id]
        player.is_alive = False
        room.eliminated_players.append((user_id, player.role))
        
        # 如果被淘汰的是当前发言玩家，切换到下一个
        if room.current_phase == GameState.SPEAKING and self.get_current_speaker(room) == user_id:
            self.next_speaker(room)
        
        return True
    
    def check_game_end(self, room):
        """检查游戏是否结束"""
        # 统计存活玩家身份
        civilian_count = 0
        undercover_count = 0
        blank_count = 0
        
        for player in room.players.values():
            if player.is_alive:
                if player.role == GameState.CIVILIAN:
                    civilian_count += 1
                elif player.role == GameState.UNDERCOVER:
                    undercover_count += 1
                elif player.role == GameState.BLANK:
                    blank_count += 1
        
        # 游戏结束条件
        if undercover_count == 0:
            # 卧底全部被淘汰，平民胜利
            return GameState.CIVILIAN
        elif undercover_count >= civilian_count + blank_count:
            # 卧底数量大于等于平民+白板，卧底胜利
            return GameState.UNDERCOVER
        elif civilian_count == 0:
            # 平民全部被淘汰，卧底胜利
            return GameState.UNDERCOVER
        
        return None  # 游戏继续
    
    def get_winner_text(self, winner_role):
        """获取获胜方文本"""
        if winner_role == GameState.CIVILIAN:
            return GameConfig.MESSAGE_TEMPLATES["CIVILIAN_WIN"]
        elif winner_role == GameState.UNDERCOVER:
            return GameConfig.MESSAGE_TEMPLATES["UNDERCOVER_WIN"]
        return ""
    
    def get_role_name(self, role):
        """获取身份中文名称"""
        return GameConfig.ROLE_NAMES.get(role, role)
    
    def update_game_stats(self, room, winner_role):
        """更新游戏统计数据"""
        # 更新全局统计数据
        game_data = {
            "player_count": len(room.players),
            "game_mode": room.game_mode,
            "winner_role": winner_role
        }
        self.game_manager.stats_manager.update_global_stats(game_data)
        
        # 更新玩家统计数据
        for user_id, player in room.players.items():
            # 获取当前玩家统计
            current_stats = self.game_manager.stats_manager.get_player_stats(user_id)
            
            # 初始化统计数据
            if not current_stats:
                current_stats = {
                    "total_games": 0,
                    "wins": 0,
                    "civilian_games": 0,
                    "civilian_wins": 0,
                    "undercover_games": 0,
                    "undercover_wins": 0,
                    "blank_games": 0,
                    "blank_wins": 0,
                    "total_speeches": 0,
                    "total_votes": 0,
                    "survival_rate": 0.0,
                    "avg_survival_rounds": 0.0,
                    "last_game_time": 0
                }
            
            # 更新总游戏次数
            current_stats["total_games"] += 1
            
            # 更新身份相关统计
            if player.role == GameState.CIVILIAN:
                current_stats["civilian_games"] += 1
                if winner_role == GameState.CIVILIAN:
                    current_stats["wins"] += 1
                    current_stats["civilian_wins"] += 1
            elif player.role == GameState.UNDERCOVER:
                current_stats["undercover_games"] += 1
                if winner_role == GameState.UNDERCOVER:
                    current_stats["wins"] += 1
                    current_stats["undercover_wins"] += 1
            elif player.role == GameState.BLANK:
                current_stats["blank_games"] += 1
                if winner_role == GameState.UNDERCOVER:
                    current_stats["wins"] += 1
                    current_stats["blank_wins"] += 1
            
            # 更新存活情况
            survival_rounds = room.current_round
            if not player.is_alive:
                # 计算玩家存活的回合数
                for round_num, (eliminated_id, _) in enumerate(room.eliminated_players):
                    if eliminated_id == user_id:
                        survival_rounds = round_num + 1
                        break
            
            # 更新平均存活回合数
            total_rounds = (current_stats["avg_survival_rounds"] * (current_stats["total_games"] - 1)) + survival_rounds
            current_stats["avg_survival_rounds"] = round(total_rounds / current_stats["total_games"], 2)
            
            # 更新存活率
            if player.is_alive:
                current_stats["survival_rate"] = round(
                    ((current_stats["survival_rate"] * (current_stats["total_games"] - 1)) + 100) / current_stats["total_games"],
                    2
                )
            else:
                current_stats["survival_rate"] = round(
                    (current_stats["survival_rate"] * (current_stats["total_games"] - 1)) / current_stats["total_games"],
                    2
                )
            
            # 更新最后游戏时间
            current_stats["last_game_time"] = time.time()
            
            # 保存更新后的统计数据
            self.game_manager.stats_manager.update_player_stats(user_id, current_stats)
    
    def validate_speech(self, content):
        """验证发言内容"""
        # 检查发言长度
        if len(content) == 0:
            return False, "发言内容不能为空"
        if len(content) > 200:
            return False, "发言内容不能超过200字"
        
        # 检查是否包含敏感词（可扩展）
        # sensitive_words = ["作弊", "偷看", "词语是"]
        # for word in sensitive_words:
        #     if word in content:
        #         return False, "发言内容包含敏感词"
        
        return True, ""
    
    def calculate_undercover_count(self, total_players):
        """根据玩家总数计算卧底数量"""
        if total_players <= 4:
            return 1
        elif total_players <= 7:
            return 2
        else:
            return 3
    
    def calculate_blank_count(self, total_players):
        """根据玩家总数计算白板数量"""
        if total_players >= 6:
            return 1
        return 0
