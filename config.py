# 游戏配置类
class GameConfig:
    # 游戏基本配置
    MIN_PLAYERS = 3  # 最小玩家数
    MAX_PLAYERS = 10  # 最大玩家数
    DEFAULT_UNDERCOVER_COUNT = 1  # 默认卧底数量
    DEFAULT_BLANK_COUNT = 0  # 默认白板数量
    MAX_SPEAK_TIME = 60  # 最大发言时间（秒）
    MAX_VOTE_TIME = 30  # 最大投票时间（秒）
    
    # 词语库配置
    WORD_PAIRS_PATH = "word_list.py"  # 词语库文件路径
    
    # 指令配置
    COMMAND_PREFIX = "/undercover"  # 指令前缀
    
    # 消息模板
    MESSAGE_TEMPLATES = {
        # 房间相关
        "ROOM_CREATE_SUCCESS": "🎉 游戏房间创建成功！\n房间号：{room_id}\n使用 `{prefix} join {room_id}` 邀请其他玩家加入",
        "JOIN_ROOM_SUCCESS": "✅ 成功加入房间 {room_id}！\n当前房间人数：{player_count}/{MAX_PLAYERS}",
        "LEAVE_ROOM_SUCCESS": "👋 已成功离开房间",
        "PLAYER_JOINED": "👤 {player_name} 加入了房间",
        "PLAYER_LEFT": "👋 {player_name} 离开了房间",
        "OWNER_CHANGED": "👑 房主已变更为 {player_name}",
        "ROOM_NOT_EXIST": "❌ 房间不存在，请检查房间号是否正确",
        "GAME_ALREADY_STARTED": "⏰ 游戏已开始，无法加入",
        "NOT_IN_ROOM": "❌ 您不在任何游戏房间中",
        
        # 游戏相关
        "GAME_START": "🎮 游戏开始！\n当前模式：{game_mode}\n玩家人数：{player_count}\n卧底人数：{undercover_count}\n白板人数：{blank_count}",
        "ROLE_ASSIGN": "🔍 您的身份是：{role}\n您的词语是：{word}\n请保护好自己的身份！",
        "TURN_TO_SPEAK": "🗣️ 轮到 {player_name} 发言了！\n请在 {speak_time} 秒内使用 `{prefix} speak <内容>` 发言",
        "SPEAK_SUCCESS": "💬 {player_name}：{content}",
        "VOTE_START": "🗳️ 发言结束，开始投票！\n请在 {vote_time} 秒内使用 `{prefix} vote <玩家>` 投票",
        "VOTE_SUCCESS": "✅ 投票成功！您已投票给 {voted_player}",
        "PLAYER_ELIMINATED": "💀 {player_name} 被淘汰！\n身份是：{role}",
        "GAME_END": "🏆 游戏结束！\n{winner} 获胜！\n本轮词语：平民词 - {civilian_word}，卧底词 - {undercover_word}",
        "CIVILIAN_WIN": "平民阵营",
        "UNDERCOVER_WIN": "卧底阵营",
        
        # 错误提示
        "INVALID_COMMAND": "❌ 请输入正确的指令\n使用 `{prefix} help` 查看所有可用指令",
        "NOT_ROOM_OWNER": "🔒 只有房主可以执行此操作",
        "NOT_ENOUGH_PLAYERS": "👥 至少需要 {min_players} 名玩家才能开始游戏",
        "NOT_YOUR_TURN": "⏳ 当前不是您的回合",
        "ALREADY_SPOKEN": "💬 您已经发过言了",
        "VOTE_TARGET_INVALID": "❌ 投票对象不存在或已被淘汰",
        "ALREADY_VOTED": "🗳️ 您已经投过票了",
        "SPEAK_TIME_OUT": "⏰ 发言时间已到！",
        "VOTE_TIME_OUT": "⏰ 投票时间已到！",
        "SPEAK_EMPTY": "💬 发言内容不能为空",
        "SPEAK_TOO_LONG": "💬 发言内容不能超过200字",
        
        # 词语库相关
        "WORD_ADD_SUCCESS": "✅ 词语添加成功，等待审核",
        "WORD_APPROVED": "✅ 词语审核通过，已加入词语库",
        "WORD_REJECTED": "❌ 词语审核未通过",
        "WORD_REMOVED": "✅ 词语已从词语库中移除",
        "WORD_EXISTS": "❌ 该词语已存在于词语库中",
        
        # 统计相关
        "PLAYER_STATS": "📊 您的游戏统计\n总游戏次数：{total_games}\n获胜次数：{wins}\n胜率：{win_rate}%\n平民身份次数：{civilian_games}\n平民获胜次数：{civilian_wins}\n卧底身份次数：{undercover_games}\n卧底获胜次数：{undercover_wins}\n白板身份次数：{blank_games}\n白板获胜次数：{blank_wins}\n存活率：{survival_rate}%\n平均存活回合数：{avg_survival_rounds}",
        "GLOBAL_STATS": "🌍 全局游戏统计\n总游戏次数：{total_games}\n总玩家数：{total_players}\n平均每局玩家数：{avg_players_per_game}",
        
        # 排行榜相关
        "RANKING_HEADER": "🏆 {ranking_type}排行榜",
        "RANKING_ITEM": "{rank}. {user_name} - {value}",
    }
    
    # 身份名称映射
    ROLE_NAMES = {
        "civilian": "平民",
        "undercover": "卧底",
        "blank": "白板",
    }
