from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from .config import GameConfig
from .models import GameState
import time

class CommandHandler:
    def __init__(self, plugin):
        self.plugin = plugin
        self.game_manager = plugin.game_manager
        self.game_logic = plugin.game_logic
    
    async def handle_command(self, event: AstrMessageEvent):
        """处理指令"""
        args = event.message_str.split()
        if len(args) < 2:
            async for result in self.send_help(event):
                yield result
            return
        
        sub_cmd = args[1].lower()
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        
        # 指令映射
        command_map = {
            "create": self.handle_create,
            "join": self.handle_join,
            "leave": self.handle_leave,
            "start": self.handle_start,
            "speak": self.handle_speak,
            "vote": self.handle_vote,
            "status": self.handle_status,
            "settings": self.handle_settings,
            "kick": self.handle_kick,
            "spectate": self.handle_spectate,
            "leave_spectate": self.handle_leave_spectate,
            "help": self.send_help,
            "addword": self.handle_add_word,
            "removeword": self.handle_remove_word,
            "approveword": self.handle_approve_word,
            "rejectword": self.handle_reject_word,
            "listwords": self.handle_list_words,
            "stats": self.handle_stats,
            "rankings": self.handle_rankings,
            "myrole": self.handle_myrole,  # 添加查看自己身份的指令
        }
        
        # 执行指令
        if sub_cmd in command_map:
            async for result in command_map[sub_cmd](event, args, user_id, user_name):
                yield result
        else:
            async for result in self.send_help(event):
                yield result
    
    async def handle_create(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理创建房间指令"""
        # 检查用户是否已在其他房间
        if self.game_manager.is_user_in_room(user_id):
            yield event.plain_result("您已在其他房间中，无法创建新房间")
            return
        
        room = self.game_manager.create_room(user_id, user_name)
        if room:
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["ROOM_CREATE_SUCCESS"].format(
                    room_id=room.room_id,
                    prefix=GameConfig.COMMAND_PREFIX
                )
            )
        else:
            yield event.plain_result("创建房间失败，请稍后重试")
    
    async def handle_join(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理加入房间指令"""
        if len(args) < 3:
            yield event.plain_result(f"请输入房间号，格式：{GameConfig.COMMAND_PREFIX} join <房间号>")
            return
        
        try:
            room_id = int(args[2])
        except ValueError:
            yield event.plain_result("房间号必须是数字")
            return
        
        success = self.game_manager.join_room(user_id, user_name, room_id)
        if success:
            room = self.game_manager.get_room_by_id(room_id)
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["JOIN_ROOM_SUCCESS"].format(
                    room_id=room_id,
                    player_count=len(room.players),
                    MAX_PLAYERS=GameConfig.MAX_PLAYERS
                )
            )
            # 通知房间内其他玩家
            async for result in self.broadcast_to_room(room, f"{user_name} 加入了房间", event):
                yield result
        else:
            yield event.plain_result("加入房间失败，房间不存在或游戏已开始")
    
    async def handle_leave(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理离开房间指令"""
        success = self.game_manager.leave_room(user_id)
        if success:
            yield event.plain_result("已成功离开房间")
            # 通知房间内其他玩家
            room = self.game_manager.get_room_by_user_id(user_id)
            if room:
                async for result in self.broadcast_to_room(room, f"{user_name} 离开了房间", event):
                    yield result
        else:
            yield event.plain_result("您不在任何房间中")
    
    async def handle_start(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理开始游戏指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查是否为房主
        if room.owner_id != user_id:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_ROOM_OWNER"])
            return
        
        # 检查房间人数
        if len(room.players) < GameConfig.MIN_PLAYERS:
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["NOT_ENOUGH_PLAYERS"].format(
                    min_players=GameConfig.MIN_PLAYERS
                )
            )
            return
        
        # 分配身份和词语
        self.game_logic.assign_roles(room)
        
        # 设置游戏状态
        room.status = GameState.PLAYING
        room.game_start_time = time.time()
        room.current_phase = GameState.SPEAKING
        room.current_phase_start_time = time.time()
        
        # 尝试向每个玩家发送身份和词语
        sent_success_count = 0
        for player_id, player in room.players.items():
            role_name = self.game_logic.get_role_name(player.role)
            word_text = player.word if player.word else "无"
            message = GameConfig.MESSAGE_TEMPLATES["ROLE_ASSIGN"].format(
                role=role_name,
                word=word_text
            )
            
            try:
                if event.get_platform_name() == "aiocqhttp":
                    # 使用 aiocqhttp 平台的 API 发送私聊消息
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    client = event.bot
                    
                    # 构建send_msg API的参数
                    payloads = {
                        "message_type": "private",
                        "user_id": player_id,
                        "message": message
                    }
                    
                    # 尝试获取group_id，支持临时聊天
                    group_id = None
                    
                    # 方法1：检查event对象是否有group_id属性
                    if hasattr(event, 'group_id'):
                        group_id = getattr(event, 'group_id', None)
                    
                    # 方法2：检查event对象是否有raw_event属性，且raw_event有group_id属性
                    elif hasattr(event, 'raw_event'):
                        raw_event = getattr(event, 'raw_event', None)
                        if raw_event and hasattr(raw_event, 'group_id'):
                            group_id = getattr(raw_event, 'group_id', None)
                    
                    # 如果获取到group_id，添加到payloads中
                    if group_id:
                        payloads["group_id"] = group_id
                    
                    # 调用send_msg API发送消息
                    await client.api.call_action('send_msg', **payloads)
                    sent_success_count += 1
                else:
                    # 其他平台暂不支持私聊，使用群聊提示
                    yield event.plain_result(f"[CQ:at,qq={player_id}] 您的身份是：{role_name}，词语是：{word_text}")
                    sent_success_count += 1
            except Exception as e:
                # 如果发送失败，记录错误日志
                logger.error(f"发送私聊消息失败：{e}")
        
        # 广播游戏开始
        yield event.plain_result(
            GameConfig.MESSAGE_TEMPLATES["GAME_START"].format(
                player_count=len(room.players),
                undercover_count=room.undercover_count,
                blank_count=room.blank_count,
                game_mode=room.game_mode
            )
        )
        
        # 提示玩家获取身份和词语
        if sent_success_count == len(room.players):
            yield event.plain_result("✅ 所有玩家的身份和词语已发送，请查看私信！")
        else:
            yield event.plain_result("⚠️ 部分玩家的身份和词语发送失败，请私聊机器人发送 '/undercover myrole' 获取！")
        
        # 通知第一个玩家发言
        first_speaker_id = self.game_logic.get_current_speaker(room)
        if first_speaker_id:
            first_speaker = room.players[first_speaker_id]
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["TURN_TO_SPEAK"].format(
                    player_name=first_speaker.user_name,
                    speak_time=room.speak_time,
                    prefix=GameConfig.COMMAND_PREFIX
                )
            )
    
    def check_phase_timeout(self, room):
        """检查当前阶段是否超时"""
        if not room.current_phase or not room.current_phase_start_time:
            return False
        
        current_time = time.time()
        elapsed_time = current_time - room.current_phase_start_time
        
        if room.current_phase == GameState.SPEAKING:
            # 发言阶段超时检查
            if elapsed_time > room.speak_time * len(room.speaking_order):
                # 总发言时间 = 单轮发言时间 * 玩家数量
                return True
        elif room.current_phase == GameState.VOTING:
            # 投票阶段超时检查
            if elapsed_time > room.vote_time:
                return True
        
        return False
    
    async def handle_speak(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理发言指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查游戏状态
        if room.status != GameState.PLAYING:
            yield event.plain_result("游戏尚未开始")
            return
        
        # 检查当前阶段
        if room.current_phase != GameState.SPEAKING:
            yield event.plain_result("当前不是发言阶段")
            return
        
        # 检查是否超时
        if self.check_phase_timeout(room):
            # 发言阶段超时，直接进入投票阶段
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["SPEAK_TIME_OUT"])
            room.current_phase = GameState.VOTING
            room.current_phase_start_time = time.time()
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["VOTE_START"].format(
                    vote_time=room.vote_time,
                    prefix=GameConfig.COMMAND_PREFIX
                )
            )
            return
        
        # 检查是否为当前发言玩家
        current_speaker_id = self.game_logic.get_current_speaker(room)
        if current_speaker_id != user_id:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_YOUR_TURN"])
            return
        
        # 检查是否已发言
        player = room.players[user_id]
        if player.has_spoken:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["ALREADY_SPOKEN"])
            return
        
        # 获取发言内容
        if len(args) < 3:
            yield event.plain_result(f"请输入发言内容，格式：{GameConfig.COMMAND_PREFIX} speak <内容>")
            return
        
        content = " ".join(args[2:])
        
        # 验证发言内容
        is_valid, error_msg = self.game_logic.validate_speech(content)
        if not is_valid:
            yield event.plain_result(error_msg)
            return
        
        # 标记为已发言
        player.has_spoken = True
        
        # 广播发言内容
        yield event.plain_result(f"{user_name}：{content}")
        
        # 切换到下一个发言玩家
        next_speaker_id = self.game_logic.next_speaker(room)
        if next_speaker_id:
            next_speaker = room.players[next_speaker_id]
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["TURN_TO_SPEAK"].format(
                    player_name=next_speaker.user_name,
                    speak_time=room.speak_time,
                    prefix=GameConfig.COMMAND_PREFIX
                )
            )
        else:
            # 发言结束，开始投票
            room.current_phase = GameState.VOTING
            room.current_phase_start_time = time.time()
            yield event.plain_result(
                GameConfig.MESSAGE_TEMPLATES["VOTE_START"].format(
                    vote_time=room.vote_time,
                    prefix=GameConfig.COMMAND_PREFIX
                )
            )
    
    async def handle_vote(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理投票指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查游戏状态
        if room.status != GameState.PLAYING:
            yield event.plain_result("游戏尚未开始")
            return
        
        # 检查当前阶段
        if room.current_phase != GameState.VOTING:
            yield event.plain_result("当前不是投票阶段")
            return
        
        # 检查是否已投票
        if user_id in room.votes:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["ALREADY_VOTED"])
            return
        
        # 检查是否超时
        if self.check_phase_timeout(room):
            # 投票阶段超时，直接统计结果
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["VOTE_TIME_OUT"])
            
            # 统计投票结果
            eliminated_id, eliminated_role = self.game_logic.get_eliminated_player(room)
            if eliminated_id:
                eliminated_player = room.players[eliminated_id]
                
                # 淘汰玩家
                self.game_logic.eliminate_player(room, eliminated_id)
                
                # 广播淘汰结果
                role_name = self.game_logic.get_role_name(eliminated_role)
                yield event.plain_result(
                    GameConfig.MESSAGE_TEMPLATES["PLAYER_ELIMINATED"].format(
                        player_name=eliminated_player.user_name,
                        role=role_name
                    )
                )
                
                # 检查游戏是否结束
                winner_role = self.game_logic.check_game_end(room)
                if winner_role:
                    # 游戏结束
                    room.status = GameState.ENDED
                    room.game_end_time = time.time()
                    room.current_phase = GameState.GAME_OVER
                    
                    # 更新游戏统计数据
                    self.game_logic.update_game_stats(room, winner_role)
                    
                    # 广播游戏结果
                    winner_text = self.game_logic.get_winner_text(winner_role)
                    yield event.plain_result(
                        GameConfig.MESSAGE_TEMPLATES["GAME_END"].format(
                            winner=winner_text
                        )
                    )
                    
                    # 广播本轮词语
                    yield event.plain_result(f"本轮词语：平民词 - {room.words[0]}，卧底词 - {room.words[1]}")
                else:
                    # 开始新回合
                    self.game_logic.start_new_round(room)
                    
                    # 通知第一个玩家发言
                    first_speaker_id = self.game_logic.get_current_speaker(room)
                    if first_speaker_id:
                        first_speaker = room.players[first_speaker_id]
                        yield event.plain_result(
                            GameConfig.MESSAGE_TEMPLATES["TURN_TO_SPEAK"].format(
                                player_name=first_speaker.user_name,
                                speak_time=room.speak_time,
                                prefix=GameConfig.COMMAND_PREFIX
                            )
                        )
            return
        
        # 获取投票对象
        if len(args) < 3:
            yield event.plain_result(f"请输入投票对象，格式：{GameConfig.COMMAND_PREFIX} vote <玩家>")
            return
        
        vote_target_name = " ".join(args[2:])
        
        # 查找投票对象
        vote_target = None
        for player in room.players.values():
            if player.user_name == vote_target_name and player.is_alive:
                vote_target = player
                break
        
        if not vote_target:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["VOTE_TARGET_INVALID"])
            return
        
        # 记录投票
        room.votes[user_id] = vote_target.user_id
        
        # 检查是否所有玩家都已投票
        alive_players = [p for p in room.players.values() if p.is_alive]
        if len(room.votes) == len(alive_players):
            # 统计投票结果
            eliminated_id, eliminated_role = self.game_logic.get_eliminated_player(room)
            if eliminated_id:
                eliminated_player = room.players[eliminated_id]
                
                # 淘汰玩家
                self.game_logic.eliminate_player(room, eliminated_id)
                
                # 广播淘汰结果
                role_name = self.game_logic.get_role_name(eliminated_role)
                yield event.plain_result(
                    GameConfig.MESSAGE_TEMPLATES["PLAYER_ELIMINATED"].format(
                        player_name=eliminated_player.user_name,
                        role=role_name
                    )
                )
                
                # 检查游戏是否结束
                winner_role = self.game_logic.check_game_end(room)
                if winner_role:
                    # 游戏结束
                    room.status = GameState.ENDED
                    room.game_end_time = time.time()
                    room.current_phase = GameState.GAME_OVER
                    
                    # 更新游戏统计数据
                    self.game_logic.update_game_stats(room, winner_role)
                    
                    # 广播游戏结果
                    winner_text = self.game_logic.get_winner_text(winner_role)
                    yield event.plain_result(
                        GameConfig.MESSAGE_TEMPLATES["GAME_END"].format(
                            winner=winner_text
                        )
                    )
                    
                    # 广播本轮词语
                    yield event.plain_result(f"本轮词语：平民词 - {room.words[0]}，卧底词 - {room.words[1]}")
                else:
                    # 开始新回合
                    self.game_logic.start_new_round(room)
                    
                    # 通知第一个玩家发言
                    first_speaker_id = self.game_logic.get_current_speaker(room)
                    if first_speaker_id:
                        first_speaker = room.players[first_speaker_id]
                        yield event.plain_result(
                            GameConfig.MESSAGE_TEMPLATES["TURN_TO_SPEAK"].format(
                                player_name=first_speaker.user_name,
                                speak_time=room.speak_time,
                                prefix=GameConfig.COMMAND_PREFIX
                            )
                        )
    
    async def handle_status(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理查看状态指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 计算剩余时间
        remaining_time = None
        if room.current_phase and room.current_phase_start_time:
            current_time = time.time()
            elapsed_time = current_time - room.current_phase_start_time
            
            if room.current_phase == GameState.SPEAKING:
                # 发言阶段剩余时间 = 总发言时间 - 已用时间
                total_speak_time = room.speak_time * len(room.speaking_order)
                remaining_time = max(0, int(total_speak_time - elapsed_time))
            elif room.current_phase == GameState.VOTING:
                # 投票阶段剩余时间 = 投票时间 - 已用时间
                remaining_time = max(0, int(room.vote_time - elapsed_time))
        
        # 构建状态信息
        status_text = f"房间号：{room.room_id}\n"
        status_text += f"房主：{room.players[room.owner_id].user_name}\n"
        status_text += f"房间状态：{room.status}\n"
        status_text += f"当前回合：{room.current_round}\n"
        status_text += f"当前阶段：{room.current_phase}\n"
        if remaining_time is not None:
            status_text += f"剩余时间：{remaining_time}秒\n"
        status_text += f"玩家数量：{len(room.players)}\n"
        status_text += f"存活玩家：{len([p for p in room.players.values() if p.is_alive])}\n"
        status_text += f"卧底数量：{room.undercover_count}\n"
        status_text += f"白板数量：{room.blank_count}\n"
        status_text += "玩家列表：\n"
        for player in room.players.values():
            alive_status = "存活" if player.is_alive else "已淘汰"
            status_text += f"  - {player.user_name} ({alive_status})\n"
        
        yield event.plain_result(status_text)
    
    async def handle_settings(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理设置指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查是否为房主
        if room.owner_id != user_id:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_ROOM_OWNER"])
            return
        
        # 处理设置
        if len(args) < 4:
            yield event.plain_result(f"请输入设置项和值，格式：{GameConfig.COMMAND_PREFIX} settings <项> <值>")
            return
        
        setting_key = args[2]
        setting_value = args[3]
        
        # 验证设置项
        valid_settings = ["allow_spectators", "auto_start", "min_players_auto_start"]
        if setting_key not in valid_settings:
            yield event.plain_result(f"无效的设置项，可用设置项：{', '.join(valid_settings)}")
            return
        
        # 转换设置值
        if setting_key in ["allow_spectators", "auto_start"]:
            setting_value = setting_value.lower() in ["true", "yes", "1"]
        elif setting_key == "min_players_auto_start":
            try:
                setting_value = int(setting_value)
                if setting_value < 3 or setting_value > 10:
                    yield event.plain_result("自动开始最小玩家数必须在3-10之间")
                    return
            except ValueError:
                yield event.plain_result("自动开始最小玩家数必须是数字")
                return
        
        # 更新设置
        room.settings[setting_key] = setting_value
        yield event.plain_result(f"设置已更新：{setting_key} = {setting_value}")
    
    async def handle_kick(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理踢人指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查是否为房主
        if room.owner_id != user_id:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_ROOM_OWNER"])
            return
        
        # 获取踢人对象
        if len(args) < 3:
            yield event.plain_result(f"请输入要踢的玩家，格式：{GameConfig.COMMAND_PREFIX} kick <玩家>")
            return
        
        kick_target_name = " ".join(args[2:])
        
        # 查找踢人对象
        kick_target = None
        for player in room.players.values():
            if player.user_name == kick_target_name:
                kick_target = player
                break
        
        if not kick_target:
            yield event.plain_result("玩家不存在")
            return
        
        # 不能踢自己
        if kick_target.user_id == user_id:
            yield event.plain_result("不能踢自己")
            return
        
        # 踢人
        self.game_manager.kick_player(room.room_id, user_id, kick_target.user_id)
        yield event.plain_result(f"已将 {kick_target.user_name} 踢出房间")
        
        # 直接在群聊中通知被踢玩家
        yield event.plain_result(f"{kick_target.user_name} 已被房主 {user_name} 踢出房间")
    
    async def handle_spectate(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理观战指令"""
        if len(args) < 3:
            yield event.plain_result(f"请输入房间号，格式：{GameConfig.COMMAND_PREFIX} spectate <房间号>")
            return
        
        try:
            room_id = int(args[2])
        except ValueError:
            yield event.plain_result("房间号必须是数字")
            return
        
        # 加入观战
        success = self.game_manager.spectate_room(user_id, room_id)
        if success:
            yield event.plain_result(f"已加入房间 {room_id} 观战")
        else:
            yield event.plain_result("加入观战失败，房间不存在或不允许观战")
    
    async def handle_leave_spectate(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理离开观战指令"""
        # 离开观战
        success = self.game_manager.leave_spectate(user_id)
        if success:
            yield event.plain_result("已成功离开观战")
        else:
            yield event.plain_result("您不在任何观战房间中")
    
    async def send_help(self, event: AstrMessageEvent):
        """发送帮助信息"""
        help_text = """谁是卧底游戏指令帮助：

/undercover create - 创建游戏房间
/undercover join <房间号> - 加入指定房间
/undercover leave - 离开当前房间
/undercover start - 开始游戏（房主）
/undercover speak <内容> - 发言（当前发言玩家）
/undercover vote <玩家> - 投票（所有存活玩家）
/undercover status - 查看游戏状态
/undercover settings <项> <值> - 修改房间设置（房主）
/undercover kick <玩家> - 踢出玩家（房主）
/undercover spectate <房间号> - 观战模式
/undercover leave_spectate - 离开观战
/undercover help - 查看帮助信息
/undercover addword <平民词> <卧底词> - 添加自定义词语
/undercover removeword <平民词> <卧底词> - 移除自定义词语
/undercover approveword <索引> - 审核通过词语
/undercover rejectword <索引> - 拒绝词语
/undercover listwords <类型> - 列出词语（all/custom/pending）
/undercover stats - 查看个人游戏统计
/undercover rankings <类型> - 查看排行榜（wins/civilian/undercover/blank/survival）
/undercover myrole - 查看自己的身份
        """
        yield event.plain_result(help_text)
    
    async def broadcast_to_room(self, room, message, event):
        """广播消息到房间所有玩家"""
        # 只在群聊中发送消息
        yield event.plain_result(message)
    
    async def handle_add_word(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理添加词语指令"""
        if len(args) < 4:
            yield event.plain_result(f"请输入词语对，格式：{GameConfig.COMMAND_PREFIX} addword <平民词> <卧底词>")
            return
        
        civilian_word = args[2]
        undercover_word = args[3]
        
        # 添加词语
        success = self.game_manager.word_manager.add_custom_word(civilian_word, undercover_word, user_id)
        if success:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["WORD_ADD_SUCCESS"])
        else:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["WORD_EXISTS"])
    
    async def handle_remove_word(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理移除词语指令"""
        if len(args) < 4:
            yield event.plain_result(f"请输入词语对，格式：{GameConfig.COMMAND_PREFIX} removeword <平民词> <卧底词>")
            return
        
        civilian_word = args[2]
        undercover_word = args[3]
        
        # 移除词语
        success = self.game_manager.word_manager.remove_custom_word(civilian_word, undercover_word)
        if success:
            yield event.plain_result("词语已成功移除")
        else:
            yield event.plain_result("词语不存在或不是自定义词语")
    
    async def handle_approve_word(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理审核通过词语指令"""
        if len(args) < 3:
            yield event.plain_result(f"请输入词语索引，格式：{GameConfig.COMMAND_PREFIX} approveword <索引>")
            return
        
        try:
            index = int(args[2])
        except ValueError:
            yield event.plain_result("索引必须是数字")
            return
        
        # 审核通过词语
        success = self.game_manager.word_manager.approve_word(index)
        if success:
            yield event.plain_result("词语审核通过")
        else:
            yield event.plain_result("索引无效")
    
    async def handle_reject_word(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理拒绝词语指令"""
        if len(args) < 3:
            yield event.plain_result(f"请输入词语索引，格式：{GameConfig.COMMAND_PREFIX} rejectword <索引>")
            return
        
        try:
            index = int(args[2])
        except ValueError:
            yield event.plain_result("索引必须是数字")
            return
        
        # 拒绝词语
        success = self.game_manager.word_manager.reject_word(index)
        if success:
            yield event.plain_result("词语已拒绝")
        else:
            yield event.plain_result("索引无效")
    
    async def handle_list_words(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理列出词语指令"""
        # 获取词语列表类型
        list_type = args[2] if len(args) > 2 else "all"
        
        if list_type == "pending":
            # 列出待审核词语
            pending_words = self.game_manager.word_manager.get_pending_words()
            if not pending_words:
                yield event.plain_result("暂无待审核词语")
                return
            
            result = "待审核词语列表：\n"
            for i, word in enumerate(pending_words):
                result += f"{i}. 平民词：{word['civilian']}，卧底词：{word['undercover']}\n"
            yield event.plain_result(result)
        elif list_type == "custom":
            # 列出自定义词语
            custom_words = self.game_manager.word_manager.get_custom_words()
            if not custom_words:
                yield event.plain_result("暂无自定义词语")
                return
            
            result = "自定义词语列表：\n"
            for civilian, undercover in custom_words:
                result += f"平民词：{civilian}，卧底词：{undercover}\n"
            yield event.plain_result(result)
        else:
            # 列出所有词语
            all_words = self.game_manager.word_manager.get_all_words()
            result = f"所有词语列表（共 {len(all_words)} 组）：\n"
            for i, (civilian, undercover) in enumerate(all_words[:20]):
                result += f"{i+1}. 平民词：{civilian}，卧底词：{undercover}\n"
            if len(all_words) > 20:
                result += f"... 还有 {len(all_words) - 20} 组词语未显示\n"
            yield event.plain_result(result)
    
    async def handle_stats(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理查看统计指令"""
        # 从StatsManager获取玩家统计数据
        stats = self.game_manager.stats_manager.get_player_stats(user_id)
        
        if stats and stats.get("total_games", 0) > 0:
            win_rate = (stats.get("wins", 0) / stats.get("total_games", 1)) * 100
            yield event.plain_result(
                f"您的游戏统计：\n" +
                f"总游戏次数：{stats.get('total_games', 0)}\n" +
                f"总获胜次数：{stats.get('wins', 0)}\n" +
                f"胜率：{round(win_rate, 2)}%\n" +
                f"平民游戏：{stats.get('civilian_games', 0)}局，获胜{stats.get('civilian_wins', 0)}局\n" +
                f"卧底游戏：{stats.get('undercover_games', 0)}局，获胜{stats.get('undercover_wins', 0)}局\n" +
                f"白板游戏：{stats.get('blank_games', 0)}局，获胜{stats.get('blank_wins', 0)}局\n" +
                f"平均存活回合：{stats.get('avg_survival_rounds', 0)}\n" +
                f"存活率：{stats.get('survival_rate', 0)}%"
            )
        else:
            yield event.plain_result("您还没有游戏统计数据")
    
    async def handle_rankings(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理查看排行榜指令"""
        ranking_type = args[2] if len(args) > 2 else "wins"
        
        # 获取排行榜
        if ranking_type == "civilian":
            rankings = self.game_manager.stats_manager.get_civilian_rankings()
            ranking_type_text = "平民胜率"
        elif ranking_type == "undercover":
            rankings = self.game_manager.stats_manager.get_undercover_rankings()
            ranking_type_text = "卧底胜率"
        elif ranking_type == "blank":
            rankings = self.game_manager.stats_manager.get_blank_rankings()
            ranking_type_text = "白板胜率"
        elif ranking_type == "survival":
            rankings = self.game_manager.stats_manager.get_survival_rankings()
            ranking_type_text = "存活率"
        else:
            rankings = self.game_manager.stats_manager.get_rankings(sort_by=ranking_type)
            ranking_type_text = "总获胜次数"
        
        # 构建排行榜文本
        if not rankings:
            yield event.plain_result("暂无排行榜数据")
            return
        
        result = GameConfig.MESSAGE_TEMPLATES["RANKING_HEADER"].format(ranking_type=ranking_type_text) + "\n"
        for i, rank in enumerate(rankings, 1):
            if "stats" in rank:
                # 总排行榜
                result += GameConfig.MESSAGE_TEMPLATES["RANKING_ITEM"].format(
                    rank=i,
                    user_name="玩家" + str(i),  # 这里可以根据实际情况获取用户名
                    value=rank["stats"].get(ranking_type, 0)
                ) + "\n"
            else:
                # 其他排行榜
                value = rank.get("civilian_win_rate", 0) or rank.get("undercover_win_rate", 0) or rank.get("blank_win_rate", 0) or rank.get("survival_rate", 0)
                result += GameConfig.MESSAGE_TEMPLATES["RANKING_ITEM"].format(
                    rank=i,
                    user_name="玩家" + str(i),  # 这里可以根据实际情况获取用户名
                    value=value
                ) + "\n"
        
        yield event.plain_result(result.strip())
    
    async def handle_myrole(self, event: AstrMessageEvent, args: list, user_id: str, user_name: str):
        """处理查看自己身份的指令"""
        # 获取用户所在房间
        room = self.game_manager.get_room_by_user_id(user_id)
        if not room:
            yield event.plain_result(GameConfig.MESSAGE_TEMPLATES["NOT_IN_ROOM"])
            return
        
        # 检查游戏状态
        if room.status == GameState.WAITING:
            yield event.plain_result("游戏尚未开始，请等待房主开始游戏")
            return
        elif room.status == GameState.ENDED:
            yield event.plain_result("游戏已结束，无法查看身份")
            return
        
        # 获取玩家信息
        player = room.players.get(user_id)
        if not player:
            yield event.plain_result("您不在当前房间中")
            return
        
        # 检查玩家是否已被淘汰
        if not player.is_alive:
            yield event.plain_result("您已被淘汰，无法查看身份")
            return
        
        # 获取玩家身份和词语
        role_name = self.game_logic.get_role_name(player.role)
        word_text = player.word if player.word else "无"
        message = GameConfig.MESSAGE_TEMPLATES["ROLE_ASSIGN"].format(
            role=role_name,
            word=word_text
        )
        
        # 添加当前游戏阶段提示
        phase_text = {
            GameState.SPEAKING: "当前处于发言阶段",
            GameState.VOTING: "当前处于投票阶段",
            GameState.ELIMINATION: "当前处于淘汰阶段",
            GameState.GAME_OVER: "游戏已结束"
        }.get(room.current_phase, "当前处于游戏中")
        
        # 发送身份和词语
        yield event.plain_result(f"{message}\n\n📌 {phase_text}")
    
    async def send_help(self, event: AstrMessageEvent):
        """发送帮助信息"""
        help_text = """谁是卧底游戏指令帮助：

基础指令：
/undercover create - 创建游戏房间
/undercover join <房间号> - 加入指定房间
/undercover leave - 离开当前房间
/undercover start - 开始游戏（房主）
/undercover speak <内容> - 发言
/undercover vote <玩家> - 投票
/undercover status - 查看游戏状态
/undercover myrole - 查看自己的身份和词语（需私聊机器人）

管理指令：
/undercover settings <项> <值> - 修改房间设置（房主）
/undercover kick <玩家> - 踢出玩家（房主）

词语管理：
/undercover addword <平民词> <卧底词> - 添加词语
/undercover removeword <平民词> <卧底词> - 移除自定义词语
/undercover approveword <索引> - 审核通过词语（管理员）
/undercover rejectword <索引> - 拒绝词语（管理员）
/undercover listwords [类型] - 列出词语（类型：all/custom/pending）

高级功能：
/undercover spectate <房间号> - 观战模式
/undercover leave_spectate - 离开观战
/undercover stats - 查看个人统计
/undercover rankings [类型] - 查看排行榜（类型：wins/civilian/undercover/blank/survival）

/undercover help - 查看帮助信息
        """
        yield event.plain_result(help_text)

# 导入需要的模块
import time
