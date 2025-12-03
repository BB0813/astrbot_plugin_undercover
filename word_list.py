# 谁是卧底词语库
# 格式：(平民词, 卧底词)

# 内置词语库
BUILTIN_WORDS = [
    # 食物类
    ("苹果", "香蕉"),
    ("米饭", "面条"),
    ("牛奶", "豆浆"),
    ("蛋糕", "面包"),
    ("火锅", "烧烤"),
    ("可乐", "雪碧"),
    ("汉堡", "三明治"),
    ("披萨", "蛋挞"),
    ("咖啡", "茶"),
    ("糖果", "巧克力"),
    
    # 生活用品类
    ("手机", "电脑"),
    ("牙刷", "牙膏"),
    ("毛巾", "浴巾"),
    ("拖鞋", "运动鞋"),
    ("雨伞", "雨衣"),
    ("台灯", "吊灯"),
    ("手表", "闹钟"),
    ("书包", "行李箱"),
    ("镜子", "窗户"),
    ("梳子", "发夹"),
    
    # 动物类
    ("猫", "狗"),
    ("大象", "长颈鹿"),
    ("老虎", "狮子"),
    ("兔子", "仓鼠"),
    ("鲸鱼", "海豚"),
    ("企鹅", "北极熊"),
    ("蝴蝶", "蜜蜂"),
    ("蛇", "蜥蜴"),
    ("鸟", "鸡"),
    ("鱼", "虾"),
    
    # 颜色类
    ("红色", "蓝色"),
    ("黄色", "绿色"),
    ("黑色", "白色"),
    ("紫色", "粉色"),
    ("橙色", "棕色"),
    ("灰色", "银色"),
    ("金色", "铜色"),
    ("青色", "蓝色"),
    ("靛色", "紫色"),
    ("彩色", "单色"),
    
    # 自然现象类
    ("太阳", "月亮"),
    ("雨", "雪"),
    ("风", "云"),
    ("山", "水"),
    ("火", "冰"),
    ("彩虹", "晚霞"),
    ("闪电", "雷声"),
    ("雾", "霾"),
    ("春", "秋"),
    ("夏", "冬"),
    
    # 交通工具类
    ("火车", "汽车"),
    ("飞机", "直升机"),
    ("轮船", "潜艇"),
    ("自行车", "电动车"),
    ("公交车", "地铁"),
    ("摩托车", "电动车"),
    ("出租车", "网约车"),
    ("火箭", "卫星"),
    ("马车", "牛车"),
    ("帆船", "游艇"),
    
    # 职业类
    ("老师", "学生"),
    ("医生", "护士"),
    ("警察", "消防员"),
    ("厨师", "服务员"),
    ("司机", "乘客"),
    ("演员", "导演"),
    ("作家", "画家"),
    ("工程师", "设计师"),
    ("农民", "工人"),
    ("律师", "法官"),
    
    # 运动类
    ("篮球", "足球"),
    ("羽毛球", "乒乓球"),
    ("跑步", "游泳"),
    ("跳高", "跳远"),
    ("网球", "排球"),
    ("拳击", "跆拳道"),
    ("瑜伽", "普拉提"),
    ("滑雪", "滑冰"),
    ("攀岩", "登山"),
    ("赛车", "赛马"),
    
    # 娱乐类
    ("电影", "电视剧"),
    ("音乐", "舞蹈"),
    ("游戏", "动漫"),
    ("小说", "漫画"),
    ("唱歌", "跳舞"),
    ("吉他", "钢琴"),
    ("象棋", "围棋"),
    ("扑克牌", "麻将"),
    ("游乐园", "动物园"),
    ("演唱会", "音乐会"),
    
    # 其他
    ("白天", "黑夜"),
    ("快乐", "悲伤"),
    ("朋友", "敌人"),
    ("成功", "失败"),
    ("健康", "疾病"),
    ("和平", "战争"),
    ("爱", "恨"),
    ("美", "丑"),
    ("大", "小"),
    ("长", "短"),
]

# 自定义词语库（动态加载）
CUSTOM_WORDS = []

# 合并词语库
WORDS = BUILTIN_WORDS + CUSTOM_WORDS

class WordManager:
    """词语库管理类"""
    
    def __init__(self):
        self.builtin_words = BUILTIN_WORDS.copy()
        self.custom_words = CUSTOM_WORDS.copy()
        self.approved_words = []
        self.pending_words = []
    
    def add_custom_word(self, civilian_word: str, undercover_word: str, submitter_id: str = None) -> bool:
        """添加自定义词语"""
        # 验证词语格式
        if not civilian_word or not undercover_word:
            return False
        
        # 检查词语是否已存在
        if self.is_word_exist(civilian_word, undercover_word):
            return False
        
        # 添加到待审核列表
        self.pending_words.append({
            "civilian": civilian_word,
            "undercover": undercover_word,
            "submitter_id": submitter_id,
            "submit_time": time.time()
        })
        return True
    
    def approve_word(self, index: int) -> bool:
        """审核通过词语"""
        if 0 <= index < len(self.pending_words):
            word = self.pending_words.pop(index)
            self.custom_words.append((word["civilian"], word["undercover"]))
            self.approved_words.append(word)
            # 更新全局词语库
            global WORDS
            WORDS = self.builtin_words + self.custom_words
            return True
        return False
    
    def reject_word(self, index: int) -> bool:
        """拒绝词语"""
        if 0 <= index < len(self.pending_words):
            self.pending_words.pop(index)
            return True
        return False
    
    def remove_custom_word(self, civilian_word: str, undercover_word: str) -> bool:
        """移除自定义词语"""
        word_pair = (civilian_word, undercover_word)
        if word_pair in self.custom_words:
            self.custom_words.remove(word_pair)
            # 更新全局词语库
            global WORDS
            WORDS = self.builtin_words + self.custom_words
            return True
        return False
    
    def is_word_exist(self, civilian_word: str, undercover_word: str) -> bool:
        """检查词语是否已存在"""
        word_pair = (civilian_word, undercover_word)
        return word_pair in self.builtin_words or word_pair in self.custom_words
    
    def get_all_words(self) -> list:
        """获取所有词语"""
        return self.builtin_words + self.custom_words
    
    def get_custom_words(self) -> list:
        """获取自定义词语"""
        return self.custom_words
    
    def get_pending_words(self) -> list:
        """获取待审核词语"""
        return self.pending_words
    
    def get_approved_words(self) -> list:
        """获取已审核词语"""
        return self.approved_words
    
    def search_words(self, keyword: str) -> list:
        """搜索词语"""
        result = []
        all_words = self.get_all_words()
        for civilian, undercover in all_words:
            if keyword in civilian or keyword in undercover:
                result.append((civilian, undercover))
        return result

# 导入需要的模块
import time

# 创建词语管理器实例
word_manager = WordManager()

