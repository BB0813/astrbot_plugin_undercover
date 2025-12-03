from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio
import time

from .game_manager import GameManager
from .game_logic import GameLogic
from .commands import CommandHandler
from .config import GameConfig

@register("undercover", "YourName", "一个谁是卧底游戏插件", "1.0.0")
class UndercoverPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.game_manager = GameManager()
        self.game_logic = GameLogic(self.game_manager)
        self.command_handler = CommandHandler(self)
        self.cleanup_task = None  # 清理任务
    
    async def initialize(self):
        """插件初始化"""
        logger.info("谁是卧底插件初始化成功")
        # 启动定期清理任务
        self.cleanup_task = asyncio.create_task(self.periodic_cleanup())
    
    async def terminate(self):
        """插件销毁"""
        logger.info("谁是卧底插件销毁")
        # 取消清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()
    
    @filter.command("undercover")
    async def handle_command(self, event: AstrMessageEvent):
        """处理指令"""
        async for result in self.command_handler.handle_command(event):
            yield result
    
    async def periodic_cleanup(self):
        """定期清理闲置房间"""
        while True:
            await asyncio.sleep(3600)  # 每小时清理一次
            self.game_manager.cleanup_idle_rooms()
            logger.info("已清理闲置房间")
    
    def get_game_manager(self):
        """获取游戏管理器"""
        return self.game_manager
    
    def get_game_logic(self):
        """获取游戏逻辑"""
        return self.game_logic
