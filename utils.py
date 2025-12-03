import time
import random

class Utils:
    @staticmethod
    def format_time(timestamp: float) -> str:
        """格式化时间戳为可读字符串"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    
    @staticmethod
    def get_time_diff(timestamp1: float, timestamp2: float) -> str:
        """计算两个时间戳的差值，返回可读字符串"""
        diff = abs(timestamp1 - timestamp2)
        minutes, seconds = divmod(diff, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        if days > 0:
            return f"{int(days)}天{int(hours)}小时"
        elif hours > 0:
            return f"{int(hours)}小时{int(minutes)}分钟"
        elif minutes > 0:
            return f"{int(minutes)}分钟{int(seconds)}秒"
        else:
            return f"{int(seconds)}秒"
    
    @staticmethod
    def generate_random_string(length: int = 8) -> str:
        """生成随机字符串"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        """验证用户ID是否有效"""
        return isinstance(user_id, str) and len(user_id) > 0
    
    @staticmethod
    def is_valid_room_id(room_id: int) -> bool:
        """验证房间ID是否有效"""
        return isinstance(room_id, int) and room_id > 0
    
    @staticmethod
    def sanitize_message(content: str) -> str:
        """清理消息内容，去除特殊字符"""
        # 这里可以添加更多的清理规则
        return content.strip()
    
    @staticmethod
    def get_room_info_text(room) -> str:
        """获取房间信息文本"""
        info = f"房间号：{room.room_id}\n"
        info += f"房主：{room.players[room.owner_id].user_name}\n"
        info += f"状态：{room.status}\n"
        info += f"玩家数：{len(room.players)}/{GameConfig.MAX_PLAYERS}\n"
        info += f"卧底数：{room.undercover_count}\n"
        info += f"白板数：{room.blank_count}\n"
        info += f"创建时间：{Utils.format_time(room.game_start_time or room.last_activity_time)}\n"
        return info
    
    @staticmethod
    def get_player_info_text(player) -> str:
        """获取玩家信息文本"""
        info = f"用户名：{player.user_name}\n"
        info += f"身份：{player.role or '未分配'}\n"
        info += f"词语：{player.word or '未分配'}\n"
        info += f"状态：{'存活' if player.is_alive else '已淘汰'}\n"
        return info
    
    @staticmethod
    def calculate_win_rate(wins: int, total: int) -> str:
        """计算胜率"""
        if total == 0:
            return "0.00%"
        return f"{round(wins / total * 100, 2)}%"

# 导入需要的模块
from .config import GameConfig
