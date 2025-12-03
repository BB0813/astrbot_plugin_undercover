import time
from typing import List, Dict, Any

class StatsManager:
    """游戏统计管理器"""
    
    def __init__(self):
        self.player_stats = {}  # 玩家统计数据 {user_id: player_stats}
        self.global_stats = {
            "total_games": 0,  # 总游戏次数
            "total_players": 0,  # 总玩家数
            "avg_players_per_game": 0.0,  # 平均每局玩家数
            "created_at": time.time(),  # 创建时间
            "last_update_time": time.time(),  # 最后更新时间
        }  # 全局统计数据
    
    def update_player_stats(self, user_id: str, player_stats: Dict[str, Any]):
        """更新玩家统计数据"""
        self.player_stats[user_id] = player_stats
        self.global_stats["last_update_time"] = time.time()
        
        # 更新总玩家数
        self.global_stats["total_players"] = len(self.player_stats)
    
    def get_player_stats(self, user_id: str) -> Dict[str, Any]:
        """获取玩家统计数据"""
        return self.player_stats.get(user_id, {})
    
    def get_all_player_stats(self) -> Dict[str, Any]:
        """获取所有玩家统计数据"""
        return self.player_stats
    
    def update_global_stats(self, game_data: Dict[str, Any]):
        """更新全局统计数据"""
        # 更新总游戏次数
        self.global_stats["total_games"] += 1
        
        # 更新平均每局玩家数
        total_players = self.global_stats["total_games"] * self.global_stats["avg_players_per_game"] + game_data.get("player_count", 0)
        self.global_stats["avg_players_per_game"] = round(total_players / self.global_stats["total_games"], 2)
        
        self.global_stats["last_update_time"] = time.time()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计数据"""
        return self.global_stats
    
    def get_rankings(self, sort_by: str = "wins", limit: int = 10) -> List[Dict[str, Any]]:
        """获取排行榜"""
        # 转换为列表并排序
        rankings = []
        for user_id, stats in self.player_stats.items():
            if stats.get("total_games", 0) > 0:  # 只统计至少玩过一局的玩家
                rankings.append({
                    "user_id": user_id,
                    "stats": stats
                })
        
        # 排序
        rankings.sort(key=lambda x: x["stats"].get(sort_by, 0), reverse=True)
        
        # 返回前N名
        return rankings[:limit]
    
    def get_civilian_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取平民排行榜"""
        rankings = []
        for user_id, stats in self.player_stats.items():
            civilian_games = stats.get("civilian_games", 0)
            if civilian_games > 0:
                civilian_win_rate = (stats.get("civilian_wins", 0) / civilian_games) * 100
                rankings.append({
                    "user_id": user_id,
                    "civilian_games": civilian_games,
                    "civilian_wins": stats.get("civilian_wins", 0),
                    "civilian_win_rate": round(civilian_win_rate, 2)
                })
        
        rankings.sort(key=lambda x: x["civilian_win_rate"], reverse=True)
        return rankings[:limit]
    
    def get_undercover_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取卧底排行榜"""
        rankings = []
        for user_id, stats in self.player_stats.items():
            undercover_games = stats.get("undercover_games", 0)
            if undercover_games > 0:
                undercover_win_rate = (stats.get("undercover_wins", 0) / undercover_games) * 100
                rankings.append({
                    "user_id": user_id,
                    "undercover_games": undercover_games,
                    "undercover_wins": stats.get("undercover_wins", 0),
                    "undercover_win_rate": round(undercover_win_rate, 2)
                })
        
        rankings.sort(key=lambda x: x["undercover_win_rate"], reverse=True)
        return rankings[:limit]
    
    def get_blank_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取白板排行榜"""
        rankings = []
        for user_id, stats in self.player_stats.items():
            blank_games = stats.get("blank_games", 0)
            if blank_games > 0:
                blank_win_rate = (stats.get("blank_wins", 0) / blank_games) * 100
                rankings.append({
                    "user_id": user_id,
                    "blank_games": blank_games,
                    "blank_wins": stats.get("blank_wins", 0),
                    "blank_win_rate": round(blank_win_rate, 2)
                })
        
        rankings.sort(key=lambda x: x["blank_win_rate"], reverse=True)
        return rankings[:limit]
    
    def get_survival_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取存活率排行榜"""
        rankings = []
        for user_id, stats in self.player_stats.items():
            if stats.get("total_games", 0) > 0:
                rankings.append({
                    "user_id": user_id,
                    "survival_rate": stats.get("survival_rate", 0),
                    "avg_survival_rounds": stats.get("avg_survival_rounds", 0)
                })
        
        rankings.sort(key=lambda x: x["survival_rate"], reverse=True)
        return rankings[:limit]
    
    def reset_stats(self):
        """重置统计数据"""
        self.player_stats = {}
        self.global_stats = {
            "total_games": 0,
            "total_players": 0,
            "avg_players_per_game": 0.0,
            "created_at": time.time(),
            "last_update_time": time.time(),
        }
