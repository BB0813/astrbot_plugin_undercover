import time
from .models import GameRoom, Player, GameState
from .config import GameConfig
from .stats_manager import StatsManager

class GameManager:
    def __init__(self):
        self.rooms = {}  # 房间字典 {room_id: GameRoom}
        self.room_counter = 1  # 房间ID计数器
        self.user_room_map = {}  # 用户房间映射 {user_id: room_id}
        self.spectators = {}  # 观战者映射 {user_id: room_id}
        self.word_list = self.load_word_list()  # 加载词语库
        self.stats_manager = StatsManager()  # 统计管理器
    
    def load_word_list(self):
        """加载词语库"""
        from .word_list import WORDS, word_manager
        self.word_manager = word_manager
        return WORDS
    
    def create_room(self, owner_id: str, owner_name: str) -> GameRoom:
        """创建新房间"""
        # 检查用户是否已在其他房间
        if owner_id in self.user_room_map:
            return None
        
        room_id = self.room_counter
        self.room_counter += 1
        room = GameRoom(room_id, owner_id)
        owner_player = Player(owner_id, owner_name)
        room.add_player(owner_player)
        self.rooms[room_id] = room
        self.user_room_map[owner_id] = room_id
        return room
    
    def join_room(self, user_id: str, user_name: str, room_id: int) -> bool:
        """加入房间"""
        # 检查用户是否已在其他房间
        if user_id in self.user_room_map:
            return False
        
        # 检查房间是否存在
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 检查房间状态
        if room.status != GameState.WAITING:
            return False
        
        # 检查房间人数是否已满
        if len(room.players) >= GameConfig.MAX_PLAYERS:
            return False
        
        # 添加玩家
        player = Player(user_id, user_name)
        room.add_player(player)
        self.user_room_map[user_id] = room_id
        
        # 检查是否需要自动开始
        if room.settings["auto_start"] and len(room.players) >= room.settings["min_players_auto_start"]:
            # 这里可以触发自动开始游戏的逻辑
            pass
        
        return True
    
    def leave_room(self, user_id: str) -> bool:
        """离开房间"""
        # 检查用户是否在房间中
        if user_id not in self.user_room_map:
            return False
        
        room_id = self.user_room_map[user_id]
        room = self.rooms[room_id]
        
        # 移除玩家
        room.remove_player(user_id)
        del self.user_room_map[user_id]
        
        # 如果房主离开，转让房主权限
        if room.owner_id == user_id:
            if room.players:
                # 转让给第一个玩家
                new_owner_id = next(iter(room.players.keys()))
                room.owner_id = new_owner_id
            else:
                # 房间为空，删除房间
                del self.rooms[room_id]
        
        return True
    

    
    def get_room_by_user_id(self, user_id: str) -> GameRoom:
        """通过用户ID获取房间"""
        if user_id in self.user_room_map:
            room_id = self.user_room_map[user_id]
            return self.rooms.get(room_id)
        return None
    
    def get_room_by_id(self, room_id: int) -> GameRoom:
        """通过房间ID获取房间"""
        return self.rooms.get(room_id)
    
    def is_user_in_room(self, user_id: str) -> bool:
        """检查用户是否在房间中"""
        return user_id in self.user_room_map
    

    
    def cleanup_idle_rooms(self):
        """清理闲置房间"""
        current_time = time.time()
        idle_rooms = []
        
        for room_id, room in self.rooms.items():
            # 清理超过24小时未活动的房间
            if current_time - room.last_activity_time > 86400:
                idle_rooms.append(room_id)
            # 清理只有房主一个人的房间，且超过1小时未开始游戏
            elif len(room.players) == 1 and room.status == GameState.WAITING and room.game_start_time is None:
                if current_time - list(room.players.values())[0].join_time > 3600:
                    idle_rooms.append(room_id)
        
        # 删除闲置房间
        for room_id in idle_rooms:
            room = self.rooms[room_id]
            
            # 清理用户房间映射
            for user_id, rid in list(self.user_room_map.items()):
                if rid == room_id:
                    del self.user_room_map[user_id]
            
            # 清理观战者
            for user_id, rid in list(self.spectators.items()):
                if rid == room_id:
                    del self.spectators[user_id]
            
            # 删除房间
            del self.rooms[room_id]
    
    def kick_player(self, room_id: int, owner_id: str, target_user_id: str) -> bool:
        """踢人功能"""
        # 检查房间是否存在
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 检查是否为房主
        if room.owner_id != owner_id:
            return False
        
        # 检查目标用户是否在房间中
        if target_user_id not in room.players:
            return False
        
        # 不能踢自己
        if target_user_id == owner_id:
            return False
        
        # 移除玩家
        room.remove_player(target_user_id)
        del self.user_room_map[target_user_id]
        
        return True
    
    def update_room_settings(self, room_id: int, owner_id: str, settings: dict) -> bool:
        """更新房间设置"""
        # 检查房间是否存在
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 检查是否为房主
        if room.owner_id != owner_id:
            return False
        
        # 更新设置
        room.settings.update(settings)
        room.last_activity_time = time.time()
        
        return True
    
    def spectate_room(self, user_id: str, room_id: int) -> bool:
        """加入观战"""
        # 检查房间是否存在
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 检查是否允许观战
        if not room.settings["allow_spectators"]:
            return False
        
        # 检查用户是否已在其他房间或观战中
        if user_id in self.user_room_map or user_id in self.spectators:
            return False
        
        # 添加到观战列表
        self.spectators[user_id] = room_id
        room.spectators[user_id] = {
            "join_time": time.time()
        }
        
        return True
    
    def leave_spectate(self, user_id: str) -> bool:
        """离开观战"""
        if user_id in self.spectators:
            room_id = self.spectators[user_id]
            if room_id in self.rooms:
                room = self.rooms[room_id]
                if user_id in room.spectators:
                    del room.spectators[user_id]
            del self.spectators[user_id]
            return True
        return False
    
    def is_user_spectating(self, user_id: str) -> bool:
        """检查用户是否在观战"""
        return user_id in self.spectators
    
    def get_spectating_room(self, user_id: str) -> int:
        """获取用户观战的房间号"""
        return self.spectators.get(user_id, 0)
    
    def get_spectators_by_room(self, room_id: int) -> dict:
        """获取房间的观战者列表"""
        if room_id in self.rooms:
            return self.rooms[room_id].spectators
        return {}
