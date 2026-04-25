import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import random
import os
import sys
from typing import List, Dict, Any

class Question:
    def __init__(self, question_type: str, question_text: str, chinese_text: str, 
                 options: List[str], correct_answer: int, category: str):
        self.type = question_type  # "multiple_choice" or "true_false"
        self.question_text = question_text
        self.chinese_text = chinese_text
        self.options = options
        self.correct_answer = correct_answer
        self.category = category

class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("大学英语IV（阅读）刷题软件")
        
        # 优化2K屏幕显示
        self.setup_high_dpi()
        
        # 题目数据
        self.all_questions = self.load_questions()  # 所有题目
        self.current_questions = self.all_questions.copy()  # 当前显示的题目列表
        self.wrong_questions = []  # 错题列表
        self.current_question_index = 0
        self.has_answered = False  # 当前题目是否已回答
        self.is_wrong_question_mode = False  # 是否为错题模式
        self.selected_categories = set()  # 选择的分类
        
        # 创建界面
        self.setup_ui()
        self.load_question()
    
    def setup_high_dpi(self):
        """设置高DPI显示优化"""
        try:
            # 设置DPI感知
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # 获取屏幕尺寸并设置合适的窗口大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 根据屏幕尺寸调整窗口大小（适配2K屏幕）
        if screen_width >= 2560:  # 2K屏幕或更高
            window_width = 1600
            window_height = 1200
            self.font_scale = 1.3
        elif screen_width >= 1920:  # 1080P屏幕
            window_width = 1000
            window_height = 800
            self.font_scale = 1.1
        else:  # 较小屏幕
            window_width = 900
            window_height = 700
            self.font_scale = 1.0
        
        # 设置窗口大小和位置（居中显示）
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.configure(bg='#f0f0f0')
        
        # 设置最小窗口大小
        self.root.minsize(1600, 1200)
    
    def get_font_size(self, base_size):
        """根据屏幕缩放计算字体大小"""
        return int(base_size * self.font_scale)
    
    def get_resource_path(self, relative_path):
        """获取资源文件路径，兼容打包后的exe"""
        try:
            # PyInstaller创建的临时文件夹
            base_path = sys._MEIPASS
        except Exception:
            # 开发环境
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def load_questions(self) -> List[Question]:
        """加载题目数据"""
        questions = []
        
        # 英美报刊简介+新闻结构 选择题 (10题)
        intro_questions = [
            {
                "question": "Like *The Economist*, *Forbes*, *Fortune* and *The Atlantic*, _______ is an iconic magazine. It has the world's largest circulation for a weekly news magazine.",
                "chinese": "与《经济学人》《福布斯》《财富》和《大西洋月刊》一样，_______ 是一本标志性杂志，其发行量在全球新闻周刊中位居首位。",
                "options": ["The Times（《泰晤士报》）", "Times Square（时代广场）", "Time（《时代周刊》）", "Time Square（时代广场）"],
                "answer": 2,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "_____________ is one of the earliest papers and enjoys high reputation in the world.",
                "chinese": "_____________ 是最早的报纸之一，在国际上享有盛誉。",
                "options": ["Los Angeles Times（《洛杉矶时报》）", "The Washington Post（《华盛顿邮报》）", "The Daily Telegraph（《每日电讯报》）", "The Times（《泰晤士报》）"],
                "answer": 3,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "In the world of print journalism, the two main formats for newspapers are__________.",
                "chinese": "在印刷新闻领域，报纸的两种主要版式是__________。",
                "options": ["big and small（大报和小报）", "words and pictures（文字和图片）", "formal and informal（正式和非正式）", "broadsheet and tabloid（大报和小报）"],
                "answer": 3,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "Which one of these is NOT newspaper?",
                "chinese": "以下哪一项不是报纸？",
                "options": ["Time（《时代周刊》）", "The New York Times（《纽约时报》）", "Los Angeles Times（《洛杉矶时报》）", "The Times（《泰晤士报》）"],
                "answer": 0,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "_________ Founded in 1851, and has won 127 Pulitzer Prizes until 2019, more than any other newspaper.",
                "chinese": "_________ 创刊于1851年，截至2019年已获得127项普利策奖，超过其他任何报纸。",
                "options": ["Time（《时代周刊》）", "The Washington Post（《华盛顿邮报》）", "The Guardian（《卫报》）", "The New York Times（《纽约时报》）"],
                "answer": 3,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "_________ is descriptive information appearing with the picture.",
                "chinese": "_________ 是图片旁附带的描述性文字。",
                "options": ["By-line（署名行）", "Deck（副标题）", "Caption（图片说明）", "The body（正文）"],
                "answer": 2,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "In general, news stories are organized using the _________ style, in which information is presented in descending order of importance.",
                "chinese": "通常，新闻报道采用_________结构，信息按重要性递减排列。",
                "options": ["inverted pyramid（倒金字塔结构）", "headline（标题）", "body（正文）", "picture（图片）"],
                "answer": 0,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "Which one of these is NOT British Newspaper?",
                "chinese": "以下哪份报纸不属于英国？",
                "options": ["The Guardian（《卫报》）", "Financial Times（《金融时报》）", "The Wall Street Journal（《华尔街日报》）", "The Times（《泰晤士报》）"],
                "answer": 2,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "_______ is the first sentence or the first paragraph of a news event informing the reader of WHO, WHERE, WHAT, WHEN, AND sometimes HOW & WHY.",
                "chinese": "_______ 是新闻事件的第一句话或第一段，向读者交代人物、地点、事件、时间，有时还包括方式和原因。",
                "options": ["Lead（导语）", "Caption（图片说明）", "Picture（图片）", "Deck（副标题）"],
                "answer": 0,
                "category": "英美报刊简介+新闻结构"
            },
            {
                "question": "Which one is NOT the popular newspapers and magazines established in the United States of America?",
                "chinese": "以下哪份报刊不是美国创办的知名报刊？",
                "options": ["USA Today（《今日美国》）", "The New York Times（《纽约时报》）", "The Times（《泰晤士报》）", "The Washington Post（《华盛顿邮报》）"],
                "answer": 2,
                "category": "英美报刊简介+新闻结构"
            }
        ]
        
        # 新闻体裁+新闻导语 选择题 (12题)
        genre_questions = [
            {
                "question": "_____ likely makes first-person statements like \"I\" and may follow it up with \"believe\" or \"think\".",
                "chinese": "_____ 通常会使用第一人称表述如\"我\"，并可能接\"相信\"或\"认为\"等词。",
                "options": ["An editorial（社论）", "An Op-ed（专栏评论）", "A feature story（特写报道）", "A soft news（软新闻）"],
                "answer": 1,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "The inverted pyramid structure is more likely to be adopted in the _______.",
                "chinese": "倒金字塔结构更可能用于_______中。",
                "options": ["editorial（社论）", "Op-ed（专栏评论）", "feature story（特写报道）", "straight news（硬新闻）"],
                "answer": 3,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "What are the two basic types of news lead?\na. question lead\nb. delayed lead\nc. direct lead\nd. anecdotal lead",
                "chinese": "新闻导语的两种基本类型是什么？",
                "options": ["b + c（延迟式导语 + 直接式导语）", "d + a", "c + d", "a + b"],
                "answer": 0,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "In general, news stories are organized using the _________ style, in which information is presented in descending order of importance.",
                "chinese": "通常，新闻报道采用_________结构，信息按重要性递减排列。",
                "options": ["headline（标题）", "inverted pyramid（倒金字塔结构）", "body（正文）", "picture（图片）"],
                "answer": 1,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "A report with the headline \"Gas Price Up 20%\" is probably ___.",
                "chinese": "标题为\"油价上涨20%\"的报道可能是___。",
                "options": ["an opinion（观点文章）", "a news（新闻）", "a feature story（特写报道）", "A fiction（虚构故事）"],
                "answer": 1,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "If you can not find a byline in the news report, it's probably because ___.",
                "chinese": "如果新闻报道中未署名，可能是因为___。",
                "options": ["It is outsourced rather than written by this newspaper's reporter（外包而非本报记者撰写）", "It is an editorial（社论）", "It is written by a nobody（由无名人士撰写）", "It is a letter to the editor（读者来信）"],
                "answer": 1,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "_______ takes a factual approach: What happened? Who was involved? Where and when did it happen? Why?",
                "chinese": "_______ 采用事实性表述：发生了什么？涉及谁？何时何地发生？为什么？",
                "options": ["A soft news（软新闻）", "An opinion（观点文章）", "A feature story（特写报道）", "A hard news（硬新闻）"],
                "answer": 3,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "According to the contents, news articles can be broadly classified into _____ types, namely ___.",
                "chinese": "根据内容，新闻文章大致可分为_____类，即___。",
                "options": ["two types; news, and opinion pieces（两类：新闻和观点文章）", "three types; news, features, and opinion pieces（三类：新闻、特写和观点文章）", "two types; news and features（两类：新闻和特写）", "three types; hard news and soft news and opinion pieces（三类：硬新闻、软新闻和观点文章）"],
                "answer": 1,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "_________ is descriptive information appearing with the picture.",
                "chinese": "_________ 是图片旁附带的描述性文字。",
                "options": ["The body（正文）", "By-line（署名行）", "Deck（副标题）", "Caption（图片说明）"],
                "answer": 3,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "A type of opinion article is called \"Op-ed\" which stands for ___.",
                "chinese": "一种观点文章称为\"Op-ed\"，其全称是___。",
                "options": ["opposite the editorial（社论对页）", "opined（观点）", "opened（开放）", "opposed（反对）"],
                "answer": 0,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "_______ is the first sentence or the first paragraph of a news event informing the reader of WHO, WHERE, WHAT, WHEN, AND sometimes HOW & WHY.",
                "chinese": "_______ 是新闻事件的第一句话或第一段，向读者交代人物、地点、事件、时间，有时还包括方式和原因。",
                "options": ["Picture（图片）", "Caption（图片说明）", "Lead（导语）", "Deck（副标题）"],
                "answer": 2,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "News about politics, war, economics, and crimes used to be considered ___.",
                "chinese": "关于政治、战争、经济和犯罪的新闻过去被视为___。",
                "options": ["Opinions（观点）", "world news（国际新闻）", "soft news（软新闻）", "hard news（硬新闻）"],
                "answer": 3,
                "category": "新闻体裁+新闻导语"
            }
        ]
        
        # 新闻语法 选择题 (10题)
        grammar_questions = [
            {
                "question": "Which of the following headlines is given to a future event?",
                "chinese": "以下哪个标题描述的是未来事件？",
                "options": ["Japan to Help Elderly Jobless（日本将帮助失业老人）", "Journalist fired in spy debate（记者因间谍辩论被解雇）", "Meet the 'selfish giant' of global trade（认识全球贸易的\"自私巨人\"）", "Longevity Star Dies at 110（长寿明星110岁去世）"],
                "answer": 0,
                "category": "新闻语法"
            },
            {
                "question": "The news headline \"Trump Criticized After Sharing Name of Alleged Whistleblower On Twitter\" means ___.",
                "chinese": "新闻标题\"特朗普在推特分享举报人姓名后遭批评\"的意思是___。",
                "options": ["Trump was criticized after the alleged whistleblower share his name on twitter.（举报人在推特分享特朗普姓名后，特朗普遭批评）", "Trump criticized the alleged whistleblower and shared his name on twitter.（特朗普批评举报人并在推特分享其姓名）", "Trump criticized someone who shared the name of the alleged whistleblower on twitter.（特朗普批评了在推特分享举报人姓名的人）", "Trump was criticized because he shared the name of the alleged whistleblower on twitter.（特朗普因在推特分享举报人姓名而遭批评）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "What are usually omitted in the news?",
                "chinese": "新闻中通常会省略哪些词？",
                "options": ["\"their\" and \"they\"（\"他们的\"和\"他们\"）", "\"we\" and \"you\"（\"我们\"和\"你\"）", "\"what\" and \"that\"（\"什么\"和\"那个\"）", "\"be\" and \"the\"（\"be动词\"和\"定冠词\"）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "A _______ can be inserted after \"Toyota Chief to Employees\" to introduce the direct quotation \"We Must Restart\" to the news headline.",
                "chinese": "在\"丰田总裁致员工\"后可以插入_______来引入直接引语\"我们必须重启\"。",
                "options": ["，（逗号）", "！（感叹号）", "？（问号）", "：（冒号）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "Which part in the news headline \"Both Ends of Films Are to be Shortened\" can be taken away?",
                "chinese": "新闻标题\"电影两端将被缩短\"中可以去掉哪个部分？",
                "options": ["Are", "Be", "Both", "to"],
                "answer": 0,
                "category": "新闻语法"
            },
            {
                "question": "The headline of this news is a(n) ___, and the sub-head is a(n) ___.",
                "chinese": "这则新闻的标题是___，副标题是___。",
                "options": ["opinion, opinion（观点，观点）", "fact, fact（事实，事实）", "opinion, fact（观点，事实）", "fact, opinion（事实，观点）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "Donald Trump is depicted by most of the mainstream newspaper as a moody guy, an unqualified president, a liar by the intentional use of a variety of dramatic, sensational words on him. This is called _______.",
                "chinese": "大多数主流报纸将唐纳德·特朗普描绘成一个情绪化的人、不合格的总统、骗子，故意使用各种戏剧性、煽动性的词语来描述他。这被称为_______。",
                "options": ["unproved claims（未经证实的说法）", "slant（倾向性报道）", "sensationalism（煽情主义）", "spin（导向性报道）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "Bequele added: \"It is completely unacceptable that children are still going hungry in Africa in the 21st century.\" (The Guardian) What can be useful clues to help us judge the attitude of the speaker in the news?",
                "chinese": "贝克尔补充说：\"在21世纪的非洲，儿童仍在挨饿，这完全令人无法接受。\"（《卫报》）什么可以成为帮助我们判断新闻中说话者态度的有用线索？",
                "options": ["The verb \"add\".（动词\"add\"）", "The key words \"hungry\".（关键词\"hungry\"）", "The word \"Africa\".（词语\"Africa\"）", "The key word \"unacceptable\".（关键词\"unacceptable\"）"],
                "answer": 3,
                "category": "新闻语法"
            },
            {
                "question": "Which is NOT the reason we read different reports of the same news events from different news agencies?",
                "chinese": "以下哪一项不是我们从不同新闻机构阅读同一新闻事件的不同报道的原因？",
                "options": ["To understand a news event comprehensively.（全面理解一个新闻事件）", "To compare different perspectives given by different news agencies.（比较不同新闻机构提供的不同视角）", "To find out the universal view for the same news event.（找出对同一新闻事件的普遍观点）", "To search for different responses from different groups of readers.（寻找不同读者群体的不同反应）"],
                "answer": 2,
                "category": "新闻语法"
            },
            {
                "question": "In the sentence \"Trump trashed his former secretary of defense, retired four-star Marine Gen. Jim Mattis, as a failure after once holding him out as a star of his administration.\" , which of the following is NOT an emotional expression?",
                "chinese": "在句子\"特朗普抨击他前国防部长、退休的四星海军陆战队将军吉姆·马蒂斯是个失败者，而他曾经将其视为政府之星。\"中，以下哪一项不是情感表达？",
                "options": ["secretary of defense（国防部长）", "a failure（失败者）", "a star（明星）", "trashed（抨击）"],
                "answer": 0,
                "category": "新闻语法"
            }
        ]
        
        # 新闻词汇 选择题 (9题)
        vocabulary_questions = [
            {
                "question": "Which one of the following statements is NOT true about midget words?",
                "chinese": "关于\"midget words\"（迷你词）下列哪项陈述是不正确的？",
                "options": ["They can save time but are difficult to understand.（它们可以节省时间但难以理解。）", "They are simple or short words.（它们是简单或简短的词汇。）", "They are often applied to save space and avoid changing lines in newspapers.（它们常被用于节省空间并避免报纸排版换行。）", "They usually only have one syllable, but sound powerful and forceful.（它们通常只有一个音节，但听起来有力且强有力。）"],
                "answer": 0,
                "category": "新闻词汇"
            },
            {
                "question": "The news headline \"CBS sitcom 'Mom' to end after 8 seasons\" includes all the following words except ___.",
                "chinese": "新闻标题\"CBS情景喜剧《Mom》将在8季后结束\"包含以下所有词汇，除了___。",
                "options": ["clipped word（截短词）", "new words（新词）", "acronym word（首字母缩略词）", "midget word（迷你词）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "Journalists often quote or cite the talks of relevant personnel. As a result, a series of synonyms of _____ come up to avoid repetition and monotony.",
                "chinese": "记者经常引用相关人员的谈话。因此，为了避免重复和单调，会出现一系列_____的同义词。",
                "options": ["have（有）", "do（做）", "be（是）", "say（说）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "The suffix \"-free\" means ___.",
                "chinese": "后缀\"-free\"的意思是___。",
                "options": ["being addicted to（对...上瘾）", "part of the whole（整体的一部分）", "clean（干净的）", "not blocked or unrestricted（不受限制的/自由的）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "In the news headline \"Two explosions in Afghanistan kill at least three\", which of the following is the example of midget word(s)?",
                "chinese": "在新闻标题\"阿富汗两起爆炸至少造成三人死亡\"中，下列哪项是迷你词（midget word）的例子？",
                "options": ["two & three（数字\"二\"和\"三\"）", "in & at（介词\"in\"和\"at\"）", "explosion（名词\"爆炸\"）", "kill（动词\"杀死\"）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "The word \"Brexit\" is coined the same way as _______.",
                "chinese": "单词\"Brexit\"（英国脱欧）的构词方式与_______相同。",
                "options": ["thinktank（智囊团）", "dorm（宿舍）", "anti-vaccine（反疫苗）", "smog（烟雾，由smoke和fog合成）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "Which one of the following is NOT true about vogue words?",
                "chinese": "下列关于时髦词汇（vogue words）的哪项陈述是不正确的？",
                "options": ["They are closely related to the fashionable trend.（它们与时尚潮流密切相关。）", "Vogue words are also called buzzwords.（时髦词汇也被称为流行语。）", "They are words that are fashionable for a time.（它们是某段时间内流行的词汇。）", "They will never lose influence as time goes by.（随着时间的推移，它们永远不会失去影响力。）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "Which of the following words refers to a scandal?",
                "chinese": "下列哪个词指的是丑闻？",
                "options": ["Park gate（公园大门）", "School gate（学校大门）", "Bill Gates（比尔·盖茨）", "Watergate（水门事件，代指丑闻）"],
                "answer": 3,
                "category": "新闻词汇"
            },
            {
                "question": "Which one is the acronym of 世界卫生组织？",
                "chinese": "下列哪项是世界卫生组织（World Health Organization）的缩写？",
                "options": ["NGO（非政府组织）", "WTO（世界贸易组织）", "NATO（北大西洋公约组织）", "WHO（世界卫生组织）"],
                "answer": 3,
                "category": "新闻词汇"
            }
        ]
        
        # 新闻修辞与媒介特征 选择题 (8题)
        rhetoric_questions = [
            {
                "question": "Which of the following rhetorical devices is used in the headline of news, 'Happy couple? America's \"phase one\" trade deal with China'?",
                "chinese": "新闻标题\"快乐夫妇？美国与中国的'第一阶段'贸易协议\"使用了以下哪种修辞手法？",
                "options": ["Pun（双关语）", "Personification（拟人）", "Parody（仿拟）", "Metaphor（隐喻）"],
                "answer": 3,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "What can \"Downing Street\" and \"White House\" refer to?",
                "chinese": "\"唐宁街\"和\"白宫\"可以指代什么？",
                "options": ["British Prime Minister and American President.（英国首相和美国总统）", "British government and American government.（英国政府和美国政府）", "London and Washington D. C.（伦敦和华盛顿特区）", "British Parliament and American Congress.（英国议会和美国国会）"],
                "answer": 1,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "Which one is NOT among the strengths of online news?",
                "chinese": "以下哪项不属于网络新闻的优势？",
                "options": ["You don't have to pay for the news anymore.（你不再需要为新闻付费。）", "Interaction between news reporters and news receivers become fast and easy.（新闻记者与受众之间的互动变得快速便捷）", "News travels without delay（新闻传播无延迟）", "Everyone can be a news reporter（人人都可以成为新闻记者）"],
                "answer": 0,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "Today's news reports usually have a strong visual and emotion impact on their readers with a lot of pictures for the print news and videos for the internet news, which is termed as the characteristics of _______.",
                "chinese": "如今的新闻报道通常通过大量图片（印刷媒体）和视频（网络媒体）对读者产生强烈的视觉和情感冲击，这被称为_______的特征。",
                "options": ["immediacy（即时性）", "multimediality（多媒体性）", "interactivity（互动性）", "hypertextuality（超文本性）"],
                "answer": 1,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "There are four main ways to obtain first-hand news abroad. They are news websites, ___, newsletters, and news apps.",
                "chinese": "获取海外一手新闻的四种主要方式包括：新闻网站、___、新闻通讯和新闻应用程序。",
                "options": ["Twitter（推特）", "Facebook（脸书）", "VPN（虚拟专用网络）", "newspaper websites（报纸网站）"],
                "answer": 3,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "Everyday we spent a lot of time catching up with the latest happening, yet our knowledge of the world remains fragmented. It is due to the _______ —— one of the negative sides of new media.",
                "chinese": "我们每天花费大量时间追踪最新事件，但对世界的认知仍然碎片化。这是由于新媒体的_______——其负面影响之一。",
                "options": ["lack of credibility（可信度缺失）", "digital divide（数字鸿沟）", "ethical issue（伦理问题）", "information overload（信息过载）"],
                "answer": 3,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "Among the types of media, _____ is booming in these 2 decades into the 21st century.",
                "chinese": "在各类媒体中，_____在过去二十年的21世纪蓬勃发展。",
                "options": ["gossip news（八卦新闻）", "internet news（网络新闻）", "broadcast news（广播新闻）", "Print news（印刷媒体）"],
                "answer": 1,
                "category": "新闻修辞与媒介特征"
            },
            {
                "question": "Which of the following rhetorical devices is NOT used in the headline \"China Puts up a Green Wall to US Trash\"?",
                "chinese": "以下哪种修辞手法未用于标题\"中国筑起绿色长城阻挡美国垃圾\"？",
                "options": ["Metaphor（隐喻）", "Parody（仿拟）", "Metonymy（借代）", "Personification（拟人）"],
                "answer": 2,
                "category": "新闻修辞与媒介特征"
            }
        ]
        
        # Chapter 16-18 选择题
        chapter_16_18_questions = [
            {
                "question": "At one point, McCandless ventures west away from the forest, but turns around because _______.",
                "chinese": "克里斯一度离开森林向西探险，但因_______而折返。",
                "options": ["He forgets the map（他忘了带地图）", "He doesn't have the right clothing to trek in that direction（他没有适合该方向徒步的衣物）", "He forgets the compass（他忘了带指南针）", "He gets bogged down by the terrain's thawing muck（他因冻土融化形成的泥沼而陷入困境）"],
                "answer": 3,
                "category": "Chapter 16"
            },
            {
                "question": "In June, McCandless shoots a moose. He feels ______.",
                "chinese": "六月，克里斯射杀了一头驼鹿。他感到______。",
                "options": ["All of the above（以上皆是）", "traumatized（创伤）", "proud at first（起初感到自豪）", "regretful（后悔）"],
                "answer": 0,
                "category": "Chapter 16"
            },
            {
                "question": "Gaylord Stuckey warns McCandless that ______.",
                "chinese": "盖洛德·斯塔基警告克里斯______。",
                "options": ["There will be few plants and berries to eat（可食用的植物和浆果很少）", "A storm front is approaching quickly（一场风暴即将迅速逼近）", "Both A and B（A和B都对）", "The snow is still thick（积雪仍然很厚）"],
                "answer": 2,
                "category": "Chapter 16"
            },
            {
                "question": "What prevents McCandless from leaving the wilderness on his first attempt?",
                "chinese": "是什么阻止了克里斯第一次尝试离开荒野？",
                "options": ["He decides he can't handle readjusting to society（他觉得自己无法重新适应社会）", "He gets too weak from food poisoning（他因食物中毒而过于虚弱）", "The Teklanika River is uncrossable（特克莱尼卡河无法渡过）", "He can't find his way（他找不到路）"],
                "answer": 2,
                "category": "Chapter 16"
            },
            {
                "question": "What do we know McCandless comes to regret deeply?",
                "chinese": "我们知道克里斯深感后悔的是什么？",
                "options": ["Killing the moose（射杀驼鹿）", "Not telling his parents where he is（未告知父母自己的行踪）", "Not bringing more food with him into the wilderness（未带足够食物进入荒野）", "Trying to shoot a bear with his small gun（试图用小枪射击熊）"],
                "answer": 0,
                "category": "Chapter 16"
            },
            {
                "question": "When Alex catches a ride with Gaylord Stuckey to Fairbanks, Alex expresses _______.",
                "chinese": "当亚历克斯搭盖洛德·斯塔基的便车去费尔班克斯时，他表达了_______。",
                "options": ["His desire to return home and plans for a reconciliation with the family（他想回家并与家人和解的计划）", "His opinion about the government and its corruption（他对政府及其腐败的看法）", "His fondness for his college days and reminisces about the past（他对大学时光的怀念）", "His father's past infidelities and his excitement about living alone in the woods（他父亲过去的出轨行为及对独居森林的兴奋）"],
                "answer": 3,
                "category": "Chapter 16"
            },
            {
                "question": "Chris is unable to cross the Teklenika river because ______.",
                "chinese": "克里斯无法渡过特克莱尼卡河是因为______。",
                "options": ["He doesn't know the way to get back to the river（他不知道返回河流的路）", "The water is too high from melting snow（融雪导致水位过高）", "He cannot swim（他不会游泳）", "His boots drag him down（他的靴子拖慢了他）"],
                "answer": 1,
                "category": "Chapter 16"
            },
            {
                "question": "One of the purchases McCandless makes prior to entering the forest is ______.",
                "chinese": "克里斯进入森林前购买的物品之一是______。",
                "options": ["A guide to edible plants（可食用植物指南）", "A diary（日记本）", "The latest guide to survival in the Alaskan bush（阿拉斯加丛林生存最新指南）", "A backpacker's stove（背包客炉具）"],
                "answer": 0,
                "category": "Chapter 16"
            },
            {
                "question": "Two of the hunters who discovered McCandless' body believed that the large animal he shot was a ______.",
                "chinese": "发现麦坎德莱斯尸体的两名猎人认为他射杀的大型动物是______。",
                "options": ["grizzly（灰熊）", "moose（驼鹿）", "caribou（北美驯鹿）", "bear（熊）"],
                "answer": 2,
                "category": "Chapter 17"
            },
            {
                "question": "Krakauer is reminded of British explorer, Sir John Franklin, ______.",
                "chinese": "克拉考尔想起了英国探险家约翰·富兰克林爵士，______。",
                "options": ["who worked tirelessly along the side of Krakauer reconstructing the McCandless trip（他与克拉考尔一起不知疲倦地重建麦坎德莱斯的旅程）", "whose arrogance in the face of harsh conditions led to the demise of 140 souls（他在恶劣条件下的傲慢导致了140人的死亡）", "who was a map maker pioneer（他是地图制作的先驱）", "who lived through the harshest of conditions（他经历了最恶劣的条件）"],
                "answer": 1,
                "category": "Chapter 17"
            },
            {
                "question": "Krakauer and his two friends discover a _______ which helps them to cross the Teklanika river.",
                "chinese": "克拉考尔和他的两位朋友发现了一个_______，帮助他们渡过了特克拉克尼卡河。",
                "options": ["trail around the river（绕河的小路）", "low point in the river（河流的低洼处）", "cable（缆绳）", "bridge（桥梁）"],
                "answer": 2,
                "category": "Chapter 17"
            },
            {
                "question": "_______ is in the throat of the canyon?",
                "chinese": "_______位于峡谷的咽喉处？",
                "options": ["A gauging station（测量站）", "A tourist center（旅游中心）", "A cottage（小屋）", "A hut（棚屋）"],
                "answer": 0,
                "category": "Chapter 17"
            },
            {
                "question": "They crossed the Teklanika River _______.",
                "chinese": "他们_______渡过了特克拉克尼卡河。",
                "options": ["by car（乘车）", "by jumping（跳跃）", "by airplane（乘飞机）", "by aluminum tram（乘坐铝制缆车）"],
                "answer": 3,
                "category": "Chapter 17"
            },
            {
                "question": "Krakauer and his friends talk late into the night about McCandless, but refuse to ______.",
                "chinese": "克拉考尔和他的朋友们深夜谈论麦坎德莱斯，但拒绝______。",
                "options": ["sleep in the bus（睡在巴士里）", "drink any alcohol（喝酒）", "talk ill of the dead（说死者坏话）", "eat anything（吃东西）"],
                "answer": 0,
                "category": "Chapter 17"
            },
            {
                "question": "The author states that he has _______ that enables him to cross the raging river that McCandless did not have.",
                "chinese": "作者表示他拥有_______，这使他能够渡过麦坎德莱斯无法渡过的汹涌河流。",
                "options": ["cable（缆绳）", "basket（篮子）", "knife（刀）", "a topographic map（地形图）"],
                "answer": 3,
                "category": "Chapter 17"
            },
            {
                "question": "If McCandless had a ______, he may have lived.",
                "chinese": "如果麦坎德莱斯有______，他可能还活着。",
                "options": ["gun of large calibra（大口径枪支）", "bottle of aspirin（一瓶阿司匹林）", "detailed map of the area（该地区的详细地图）", "pair of boots that fit right（一双合脚的靴子）"],
                "answer": 2,
                "category": "Chapter 17"
            },
            {
                "question": "In the end, Chris was unable to ______.",
                "chinese": "最终，克里斯无法______。",
                "options": ["see and hear（看不见也听不见）", "walk（行走）", "hear（听见）", "see（看见）"],
                "answer": 1,
                "category": "Chapter 18"
            },
            {
                "question": "The author begins each chapter with a quote because ______.",
                "chinese": "作者在每章开头引用名言是因为______。",
                "options": ["Sets a mood, foreshadowing, favorite quotes of Chris, specific background information about Chris.（营造氛围、埋下伏笔、引用克里斯喜爱的名言、提供关于克里斯的具体背景信息。）", "The author just wanted to fill up the space.（作者只是为了填满空间。）", "There is no information about Chris.（没有关于克里斯的信息。）", "The author did it for fun.（作者这样做是为了好玩。）"],
                "answer": 0,
                "category": "Chapter 18"
            },
            {
                "question": "What is the purpose of the story?",
                "chinese": "这个故事的目的是什么？",
                "options": ["To inform（告知）", "To persuade（说服）", "To entertain（娱乐）", "To wonder（引发思考）"],
                "answer": 3,
                "category": "Chapter 18"
            },
            {
                "question": "What does Krakauer think actually killed Chris?",
                "chinese": "克拉考尔认为究竟是什么导致了克里斯的死亡？",
                "options": ["The mold on wild potato seeds he was eating.（他食用的野生马铃薯种子上的霉菌。）", "Tainted canned goods he found in the bus.（他在巴士里发现的变质罐头食品。）", "Choking on rabbit bones.（被兔子骨头噎住。）", "Poisonous leaves he was reduced to eating.（被迫食用的有毒树叶。）"],
                "answer": 0,
                "category": "Chapter 18"
            },
            {
                "question": "Krakauer assumes that the potato seeds were mistaken for ______.",
                "chinese": "克拉考尔认为克里斯误将马铃薯种子认成了______。",
                "options": ["a sweet pea plant（甜豌豆植物）", "a poison berry（有毒浆果）", "none of the above（以上都不是）", "hemlock（毒芹）"],
                "answer": 0,
                "category": "Chapter 18"
            }
        ]
        
        # Chapter 1-5 选择题
        chapter_1_5_questions = [
            {
                "question": "Which of the following is NOT a reason why the couple that first came upon the bus in Into the Wild did not want to look inside?",
                "chinese": "以下哪一项不是最初发现《荒野生存》中巴士的那对夫妇不想往里看的原因？",
                "options": ["They found McCandless's S.O.S. note.（他们发现了麦坎德莱斯的求救信。）", "There were animals scavenging around the site.（有动物在现场食腐。）", "They were too upset by both the smell and the note（他们对气味和纸条都感到非常不安）", "There were animals scavenging around the site.（有动物在现场食腐。）"],
                "answer": 3,
                "category": "Chapter 1-2"
            },
            {
                "question": "By immediately establishing the fact that Chris McCandless died in the wilderness of Alaska, his decomposed body found months after his death, what tone does Krakauer set up for the reader?",
                "chinese": "通过立即确定克里斯·麦坎德莱斯在阿拉斯加荒野中死亡的事实，他的尸体在他死后数月被发现，克拉考尔为读者设定了什么样的基调？",
                "options": ["Hopeful（充满希望的）", "Curious（好奇的）", "Cheerful（愉快的）", "Ominous（不祥的）"],
                "answer": 3,
                "category": "Chapter 1-2"
            },
            {
                "question": "According to the explanation in the book Into the Wild, why was there a bus near the Stampede Trail in the Alaskan Wilderness?",
                "chinese": "根据《荒野生存》一书中的解释，为什么阿拉斯加荒野中的奔腾小径附近会有一辆巴士？",
                "options": ["The bus had been a shelter for construction workers and was then left as a shelter for hunters.（这辆巴士曾是建筑工人的庇护所，后来被留作猎人的庇护所。）", "McCandless drove the bus there, but it broke down.（麦坎德莱斯把巴士开到那里，但车坏了。）", "None of the answers are correct.（所有答案都不正确。）", "The Stampede Trail had been turned into a road and the bus had broken down on the side of the road long ago.（奔腾小径曾被改造成公路，很久以前巴士就在路边抛锚了。）"],
                "answer": 0,
                "category": "Chapter 1-2"
            },
            {
                "question": "In what season does McCandless go into the wilderness?",
                "chinese": "麦坎德莱斯是在哪个季节进入荒野的？",
                "options": ["Winter（冬季）", "Fall（秋季）", "Spring（春季）", "Summer（夏季）"],
                "answer": 2,
                "category": "Chapter 1-2"
            },
            {
                "question": "What kind of vehicle does Christopher McCandless live in during his stay in Denali National Park?",
                "chinese": "克里斯托弗·麦坎德莱斯在德纳利国家公园逗留期间住在什么样的交通工具里？",
                "options": ["A motorhome（房车）", "A railroad car（火车车厢）", "A tent（帐篷）", "A bus（巴士）"],
                "answer": 3,
                "category": "Chapter 1-2"
            },
            {
                "question": "What is Christopher McCandless doing when he is first introduced to the reader?",
                "chinese": "当克里斯托弗·麦坎德莱斯第一次被介绍给读者时，他在做什么？",
                "options": ["Reading（阅读）", "Hunting a moose（猎驼鹿）", "Hitchhiking（搭便车）", "Writing in his diary（写日记）"],
                "answer": 2,
                "category": "Chapter 1-2"
            },
            {
                "question": "How did Christopher McCandless arrive to the \"Stampede Trail\"?",
                "chinese": "克里斯托弗·麦坎德莱斯是如何到达\"奔腾小径\"的？",
                "options": ["He took a cab to the trail（他乘出租车到达小径）", "He took a bus that dropped him off at the trail（他乘公共汽车在小径下车）", "He hitchhiked his way to the trail（他搭便车到达小径）", "He had a backpacking guide lead him the way to the trail（他让一个背包向导带他去了小径）"],
                "answer": 2,
                "category": "Chapter 1-2"
            },
            {
                "question": "How does Christopher McCandless die in the wild?",
                "chinese": "克里斯托弗·麦坎德莱斯是如何在荒野中死去的？",
                "options": ["Hypothermia（体温过低）", "Suicide（自杀）", "Food poisoning（食物中毒）", "Starvation（饥饿）"],
                "answer": 3,
                "category": "Chapter 1-2"
            },
            {
                "question": "In Into the Wild, why is it surprising that six people came upon the abandoned bus on September 6, 1992?",
                "chinese": "在《荒野生存》中，为什么1992年9月6日有六个人来到那辆废弃的巴士上令人惊讶？",
                "options": ["No one had come upon it for at least the two and a half weeks prior.（在此之前的至少两个半星期里，没有人来过这里。）", "The six people were from three separate parties.（这六个人来自三个不同的团体。）", "It is difficult to reach.（这个地方很难到达。）", "All of the answers are correct.（所有答案都正确。）"],
                "answer": 3,
                "category": "Chapter 1-2"
            },
            {
                "question": "What is the destination of Christopher McCandless's canoe trip down the Colorado River?",
                "chinese": "克里斯托弗·麦坎德莱斯沿科罗拉多河划独木舟旅行的目的地是哪里？",
                "options": ["Fairbanks, Alaska（阿拉斯加费尔班克斯）", "The Grand Canyon（大峡谷）", "His parents' home（他父母的家）", "Mexico（墨西哥）"],
                "answer": 3,
                "category": "Chapter 3-4"
            },
            {
                "question": "Before leaving Carthage, McCandless gives his employer a gift. What is it?",
                "chinese": "离开卡瑟斯前，麦坎德莱斯送给雇主什么礼物？",
                "options": ["A picture of himself（一张自己的照片）", "A travel journal（一本旅行日记）", "A copy of War and Peace（一本《战争与和平》）", "A leather belt he made（一条自制的皮带）"],
                "answer": 2,
                "category": "Chapter 3-4"
            },
            {
                "question": "Once Chris reaches the Colorado River, how does he get to Mexico?",
                "chinese": "克里斯到达科罗拉多河后，如何前往墨西哥？",
                "options": ["he hitchhikes（搭便车）", "Canoe（独木舟）", "train（火车）", "bus（公共汽车）"],
                "answer": 1,
                "category": "Chapter 3-4"
            },
            {
                "question": "Chris McCandless worked in Carthage, South Dakota _______.",
                "chinese": "克里斯·麦坎德莱斯在南达科他州卡瑟斯市从事什么工作？",
                "options": ["cleaning barns（打扫谷仓）", "working in a grain elevator（在谷物升降机工作）", "herd cattle（放牛）", "milking cows（挤牛奶）"],
                "answer": 1,
                "category": "Chapter 3-4"
            },
            {
                "question": "In what way the trip down the Colorado River contributed to the ensuing Alaska adventure?",
                "chinese": "沿科罗拉多河的旅行如何影响了后续的阿拉斯加冒险？",
                "options": ["Alex always could get help from local people（亚历克斯总能得到当地人的帮助）", "Alex can live without ID（亚历克斯可以无身份证明生活）", "Alex learned how to make out the direction（亚历克斯学会了辨别方向）", "Alex was convinced that he could survive on meager rations of food（亚历克斯确信自己可以靠少量食物生存）"],
                "answer": 3,
                "category": "Chapter 3-4"
            },
            {
                "question": "Chris McCandless changed his name to ______.",
                "chinese": "克里斯·麦坎德莱斯改名为______。",
                "options": ["Alexander Supertramp（亚历山大·超级流浪汉）", "Henry David Thoreau（亨利·戴维·梭罗）", "Wayne Westerberg（韦恩·韦斯特伯格）", "Jim Gallien（吉姆·加利恩）"],
                "answer": 0,
                "category": "Chapter 3-4"
            },
            {
                "question": "Why did Chris like Carthage?",
                "chinese": "克里斯为什么喜欢卡瑟斯？",
                "options": ["Life was simple（生活简单）", "No one talked with him（没人跟他说话）", "It reminded him of his parent's home（这让他想起父母的家）", "It was rainy（那里多雨）"],
                "answer": 0,
                "category": "Chapter 3-4"
            },
            {
                "question": "What did McCandless do that he felt Thoreau and Tolstoy would take pride in?",
                "chinese": "麦坎德莱斯做了什么事情，他认为梭罗和托尔斯泰会为此感到自豪？",
                "options": ["Burned all his paper currency（烧掉所有纸币）", "Rowed the canoe down the Colorado River（划独木舟沿科罗拉多河而下）", "Resumed his odyssey on foot（徒步继续他的旅程）", "Abandoned his car（遗弃他的汽车）"],
                "answer": 0,
                "category": "Chapter 3-4"
            },
            {
                "question": "McCandless did the following to prepare for his great Alaskan adventure except _______",
                "chinese": "克里斯·麦坎德莱斯为他的阿拉斯加大冒险做了以下准备，除了_______",
                "options": ["learning about backcountry survival strategies（学习野外生存策略）", "saving money（存钱）", "taking all that Burres offered（接受伯雷斯提供的一切）", "calisthenics（健美操）"],
                "answer": 2,
                "category": "Chapter 5"
            },
            {
                "question": "McCandless accepted _______ from Jan when he left Slabs.",
                "chinese": "克里斯·麦坎德莱斯离开斯莱布斯时接受了简的_______",
                "options": ["some knives（一些刀具）", "a little money（一点钱）", "warm clothing（保暖衣物）", "long underwear（长内衣）"],
                "answer": 0,
                "category": "Chapter 5"
            },
            {
                "question": "In first several weeks in Bullhead City, where did McCandless live?",
                "chinese": "在布尔黑德市的最初几周，麦坎德莱斯住在哪里？",
                "options": ["on a trailer（在拖车上）", "in the street（在街上）", "in an asylum（在精神病院）", "in the desert（在沙漠里）"],
                "answer": 3,
                "category": "Chapter 5"
            },
            {
                "question": "All of the following works of Jack London trigger McCandless's dream of Alaska except _______.",
                "chinese": "以下杰克·伦敦的哪些作品激发了麦坎德莱斯对阿拉斯加的梦想，除了_______。",
                "options": ["White Fang（《白牙》）", "The Call of the Wild（《野性的呼唤》）", "An Odyssey of the North（《北方的奥德赛》）", "The Adventures of Huckleberry Finn（《哈克贝利·费恩历险记》）"],
                "answer": 3,
                "category": "Chapter 5"
            },
            {
                "question": "When McCandless worked in the MacDonald, how did the assistant manager George Dreeszen think about him?",
                "chinese": "当麦坎德莱斯在麦克唐纳餐厅工作时，助理经理乔治·德里森对他有什么看法？",
                "options": ["dependable（可靠的）", "sly（狡猾的）", "diligent（勤奋的）", "lazy（懒惰的）"],
                "answer": 0,
                "category": "Chapter 5"
            },
            {
                "question": "How long did McCandless stay in Bullhead City?",
                "chinese": "麦坎德莱斯在布尔黑德市待了多久？",
                "options": ["one year（一年）", "two months（两个月）", "one month（一个月）", "two weeks（两周）"],
                "answer": 1,
                "category": "Chapter 5"
            },
            {
                "question": "According to Charlie, the old man offering a trailer stay, McCandless had a lot of ______.",
                "chinese": "据提供拖车住宿的老人查理说，麦坎德莱斯有很多______。",
                "options": ["complexes（情结）", "horrors（恐怖）", "worries（担忧）", "anxieties（焦虑）"],
                "answer": 0,
                "category": "Chapter 5"
            },
            {
                "question": "Who was McCandless' favorite writer?",
                "chinese": "谁是麦坎德莱斯最喜欢的作家？",
                "options": ["H. G. Wells（H.G.威尔斯）", "Jack London（杰克·伦敦）", "Mark Twain（马克·吐温）", "Dickens（狄更斯）"],
                "answer": 1,
                "category": "Chapter 5"
            },
            {
                "question": "How did MaCandless break Tracy's heart?",
                "chinese": "麦坎德莱斯是如何伤透特蕾西的心的？",
                "options": ["He played with her and abandoned her.", "He treated her coldly.", "He rebuffed Tracy's advances.", "He was aware that Tracy had a crush on him."],
                "answer": 2,
                "category": "Chapter 5"
            },
            {
                "question": "McCandless talked with people around him about the following except _______",
                "chinese": "麦坎德莱斯与周围的人谈论了以下内容，除了_______",
                "options": ["nature（自然）", "his family（他的家庭）", "books（书籍）", "his great Alaskan odyssey（他的阿拉斯加大冒险）"],
                "answer": 1,
                "category": "Chapter 5"
            },
            {
                "question": "McCandless did all the following things to Jan Burres except ______.",
                "chinese": "麦坎德莱斯对简·伯雷斯做了以下所有事情，除了______",
                "options": ["helping her with housework（帮她做家务）", "making her mad（惹她生气）", "arguing with her（与她争论）", "teasing her（逗她）"],
                "answer": 0,
                "category": "Chapter 5"
            },
            {
                "question": "McCandless was big on the following authors except _______.",
                "chinese": "麦坎德莱斯非常喜欢以下作家，除了_______",
                "options": ["Dickens（狄更斯）", "Jack London（杰克·伦敦）", "T. S. Eliot（T.S.艾略特）", "H. G. Wells（H.G.威尔斯）"],
                "answer": 2,
                "category": "Chapter 5"
            }
        ]
        chapter_10_13_additional_questions = [
            {
                "question": "How did Carine react to the news that Chris was dead?",
                "chinese": "卡琳对克里斯去世的消息有何反应？",
                "options": ["she absolutely refused to believe it and denied it for days and days, until the dental records confirmed his identity（她坚决不相信，否认多日，直到牙科记录确认身份）", "she screamed and cried hysterically for hours and refused to be comforted（她歇斯底里地尖叫哭泣数小时，拒绝被安慰）", "she was so calm that people worried that she didn't understand what was happening（她过于平静，人们担心她无法理解发生的事情）", "she fainted and had to be taken to the hospital（她晕倒并被送往医院）"],
                "answer": 1,
                "category": "Chapter 10+13"
            },
            {
                "question": "Why does Chris's sister regret that her parents didn't allow Chris to take their dog Buckley along on his adventure?",
                "chinese": "为什么克里斯的姐姐后悔父母没有让他们的狗巴克利陪克里斯一起冒险？",
                "options": ["at least then Chris wouldn't have been alone（至少克里斯不会孤单）", "things may have turned out differently if he'd had the dog along because he wouldn't have done anything to put the dog in danger（如果巴克利在场，情况可能会不同，因为克里斯不会做任何危及狗的事情）", "Chris might have been able to get the dog to go find help after he was too weak to go himself（克里斯虚弱到无法行动时，或许能派狗去寻求帮助）", "she thinks the dog would have enjoyed it（她认为狗会喜欢这次冒险）"],
                "answer": 1,
                "category": "Chapter 10+13"
            },
            {
                "question": "What name was printed on the box of Chris's ashes?",
                "chinese": "克里斯骨灰盒上印的是什么名字？",
                "options": ["the name he had given to many of the people he had met: Alexander McCandless（他给许多遇见的人起的名字：亚历山大·麦坎德莱斯）", "the pseudonym he had used to refer to himself: Alexander Supertramp（他用来指代自己的化名：亚历山大·超级流浪汉）", "his name with the wrong middle initial: Christopher R. McCandless（名字中间字母错误的本名：克里斯托弗·R·麦坎德莱斯）", "his real name: Christopher J. McCandless（他的真实姓名：克里斯托弗·J·麦坎德莱斯）"],
                "answer": 2,
                "category": "Chapter 10+13"
            },
            {
                "question": "What quality of Chris's does Carine not share?",
                "chinese": "卡琳不具备克里斯的哪种特质？",
                "options": ["Distaste for wealth（厌恶财富）", "High-achiever（成就导向）", "Having had a bad relationship with their parents（与父母关系不佳）", "Intensity（强烈个性）"],
                "answer": 0,
                "category": "Chapter 10+13"
            },
            {
                "question": "How were authorities eventually able to positively identify the hiker as Chris McCandless?",
                "chinese": "当局最终如何确认这名徒步旅行者是克里斯·麦坎德莱斯？",
                "options": ["Wayne Westerberg flew to Alaska to identify the body.（韦恩·韦斯特伯格飞往阿拉斯加辨认遗体）", "Chris's half-brother identified the body.（克里斯同父异母的兄弟辨认了遗体）", "Wayne Westerberg provided a social security number, which checked out as belonging to an individual from Virginia.（韦恩·韦斯特伯格提供了社会保障号码，经核实属于弗吉尼亚州居民）", "Gallien contacted the authorities.（加利恩联系了当局）"],
                "answer": 2,
                "category": "Chapter 10+13"
            },
            {
                "question": "Who told Carine the news that Chris was dead?",
                "chinese": "谁告诉卡琳克里斯去世的消息？",
                "options": ["her husband（她的丈夫）", "her mom（她的母亲）", "her dad（她的父亲）", "her half-brother Sam（她的同父异母兄弟萨姆）"],
                "answer": 0,
                "category": "Chapter 10+13"
            },
            {
                "question": "Chris's parents had moved, but his step-brother was contacted. After he positively identified Chris, what did he do?",
                "chinese": "克里斯的父母已搬家，但联系到了他的继兄。继兄确认身份后做了什么？",
                "options": ["Flew to Alaska to claim to body.（飞往阿拉斯加认领遗体）", "Told his wife that he always knew Chris would end that way.（告诉妻子他早就知道克里斯会落得如此下场）", "Drove to Maryland to inform Chris's parents.（驱车前往马里兰州通知克里斯的父母）", "Contacted Gallien to get more information.（联系加利恩获取更多信息）"],
                "answer": 2,
                "category": "Chapter 10+13"
            },
            {
                "question": "Why didn't the authority contact Chris's parents in the first place?",
                "chinese": "当局为何最初未联系克里斯的父母？",
                "options": ["They didn't have a telephone.（他们没有电话）", "They would be too sad to get the news.（他们得知消息会过于悲伤）", "They moved to another state.（他们搬到了另一个州）", "They were not at home.（他们不在家）"],
                "answer": 2,
                "category": "Chapter 10+13"
            },
            {
                "question": "Who was the first family member to be notified of Chris's death?",
                "chinese": "谁是第一个得知克里斯去世消息的家庭成员？",
                "options": ["His brother, Sam（他的兄弟萨姆）", "His father, Walter（他的父亲沃尔特）", "His sister, Carine（他的姐姐卡琳）", "His mother, Billie（他的母亲比莉）"],
                "answer": 0,
                "category": "Chapter 10+13"
            },
            {
                "question": "Who had a strong appetite for food after Chris's death out of anxiety?",
                "chinese": "谁因焦虑在克里斯去世后暴饮暴食？",
                "options": ["his mother（他的母亲）", "his father（他的父亲）", "his sister（他的姐姐）", "his dog（他的狗）"],
                "answer": 1,
                "category": "Chapter 10+13"
            },
            {
                "question": "Which family members flew to Alaska to pick up Chris's remains and belongings?",
                "chinese": "哪些家庭成员飞往阿拉斯加认领克里斯的遗体和物品？",
                "options": ["Chris' parents（克里斯的父母）", "the entire family: Chris' parents, Carine, and all the half-siblings（全家：克里斯的父母、卡琳及所有同父异母/同母异父的兄弟姐妹）", "Carine and her half-brother Sam（卡琳和她的同父异母兄弟萨姆）", "Carine and her husband（卡琳和她的丈夫）"],
                "answer": 2,
                "category": "Chapter 10+13"
            },
            {
                "question": "What did Chris's friends on road do when they first heard about the unidentified hiker found in Alaska?",
                "chinese": "克里斯在路上结识的朋友最初得知阿拉斯加发现无名徒步者时做了什么？",
                "options": ["They flew to Alaska to identify the body.（他们飞往阿拉斯加辨认遗体）", "They did nothing.（他们什么也没做）", "They tried to notify the Alaska State Troopers, but the authorities didn't believe them at first because of all the responses from the public.（他们试图通知阿拉斯加州警，但因公众反馈过多，当局最初未采信）", "They notified Chris's family and friends.（他们通知了克里斯的家人和朋友）"],
                "answer": 2,
                "category": "Chapter 10+13"
            }
        ]
        chapter_11_12_questions = [
            {
                "question": "What secret did Chris discover about his father while visiting California?",
                "chinese": "克里斯在加州探访时发现了关于他父亲的什么秘密？",
                "options": ["His father had some other children with his first wife.（他父亲和第一任妻子还有其他孩子）", "His parents were not married.（他的父母没有结婚）", "His father had a previous marriage.（他父亲有过一段婚姻）", "His father had a double life in two families.（他父亲在两个家庭中过着双重生活）"],
                "answer": 3,
                "category": "Chapter 11-12"
            },
            {
                "question": "At Chris's high school graduation party, how did Chris behave towards his dad?",
                "chinese": "在克里斯的高中毕业派对上，他对父亲的态度如何？",
                "options": ["he insulted his dad and treated him like he was not as smart as Chris（他侮辱父亲，认为父亲不如自己聪明）", "he was rude and wouldn't even speak to him（他很粗鲁，甚至不愿和父亲说话）", "he told his dad he was grateful for all the things his dad had done for him（他告诉父亲感激父亲为他所做的一切）", "he told his dad that he wasn't planning on going to college（他告诉父亲不打算上大学）"],
                "answer": 2,
                "category": "Chapter 11-12"
            },
            {
                "question": "Which of the following is NOT McCandless's reaction towards this huge discovery of Walt's secret?",
                "chinese": "以下哪项不是麦坎德莱斯对发现父亲秘密的反应？",
                "options": ["He confronted them with the discovery angrily.（他愤怒地与父母对质这个发现）", "He harbored his resentment, letting the bad feelings build and build（他怀恨在心，让负面情绪不断累积）", "He made it a secret and expressed his rage in silence and withdrawal（他将此作为秘密，以沉默和疏远表达愤怒）", "His relationship with his parents deteriorated（他与父母的关系恶化）"],
                "answer": 0,
                "category": "Chapter 11-12"
            },
            {
                "question": "During the summer between his junior and senior years of college, where did Chris travel?",
                "chinese": "在大学三年级和四年级之间的暑假，克里斯去了哪里旅行？",
                "options": ["Uganda（乌干达）", "Alaska（阿拉斯加）", "Arizona（亚利桑那州）", "Guatemala（危地马拉）"],
                "answer": 1,
                "category": "Chapter 11-12"
            },
            {
                "question": "Which of Chris's relatives was a woodsman and part-time hunting guide, which likely left an impression on Chris and encouraged his love of the outdoors?",
                "chinese": "克里斯的哪位亲戚是樵夫兼兼职狩猎向导，这可能给克里斯留下了深刻印象并培养了他对户外活动的热爱？",
                "options": ["his brother, Sam（他的兄弟山姆）", "his grandfather, Loren（他的祖父洛伦）", "his cousin, Jason（他的表弟杰森）", "his father, Walt（他的父亲沃尔特）"],
                "answer": 1,
                "category": "Chapter 11-12"
            },
            {
                "question": "What caused Chris, a talented French-horn player, to quit the band?",
                "chinese": "是什么原因导致有才华的法国号手克里斯退出乐队？",
                "options": ["he traded his French horn for money to buy his car（他用法国号换钱买车）", "his sister Carine played better than he did and was selected first chair（他的姐姐卡琳演奏得比他好，被选为首席）", "he gave his French horn to a homeless person（他把法国号给了一个无家可归的人）", "he kept ditching practice to go on hikes in the woods（他不断逃掉练习去森林远足）"],
                "answer": 1,
                "category": "Chapter 11-12"
            },
            {
                "question": "What did Chris do when his father asked about the computer program Chris wrote?",
                "chinese": "当父亲询问克里斯编写的计算机程序时，他做了什么？",
                "options": ["He became very angry.（他变得非常生气）", "He kept silent.（他保持沉默）", "He shared his thoughts eagerly.（他急切地分享自己的想法）", "He refused to talk about it.（他拒绝谈论此事）"],
                "answer": 3,
                "category": "Chapter 11-12"
            },
            {
                "question": "What musical skill did Chris and his father have in common?",
                "chinese": "克里斯和他父亲有什么共同的乐器技能？",
                "options": ["playing drums（打鼓）", "singing（唱歌）", "playing French horn（吹法国号）", "playing piano（弹钢琴）"],
                "answer": 3,
                "category": "Chapter 11-12"
            },
            {
                "question": "What strange past time did Chris develop in high school and invite his friends to participate in?",
                "chinese": "克里斯在高中时养成了什么奇怪的消遣习惯，并邀请朋友一起参与？",
                "options": ["he'd break into rich people's houses and steal money to give to the poor（他会闯入富人家偷钱给穷人）", "he'd ditch school to go hiking and mountain climbing（他会逃课去徒步和登山）", "he go around the bad parts of town, talking to the prostitutes and homeless people and taking them food（他会到镇上的不良区域，与妓女和无家可归者交谈并给他们带食物）", "he'd try to sneak in and break up parties his classmates were attending（他会试图溜进去打断同学们参加的派对）"],
                "answer": 2,
                "category": "Chapter 11-12"
            },
            {
                "question": "What was Christopher McCandless's leadership role at Emory University?",
                "chinese": "克里斯托弗·麦坎德莱斯在埃默里大学的领导职位是什么？",
                "options": ["Cross-country captain（越野队长）", "Head of fraternity（兄弟会主席）", "Student newspaper assistant editor（学生报纸助理编辑）", "Football captain（足球队队长）"],
                "answer": 2,
                "category": "Chapter 11-12"
            },
            {
                "question": "Why was it ironic that Chris believed wealth was \"shameful, corrupting, and inherently evil\"?",
                "chinese": "为什么克里斯认为财富\"可耻、腐蚀性强且本质邪恶\"具有讽刺意味？",
                "options": ["because he spent so much money himself, buying things that he wanted（因为他自己花了很多钱买想要的东西）", "because he was always encouraging others to go to college so they could get better jobs to make more money（因为他总是鼓励别人上大学，以便找到更好的工作赚更多钱）", "because he loved to ski and go on cruises, which were expensive activities（因为他喜欢滑雪和乘船游览，这些都是昂贵的活动）", "because he had always been very good and very successful at making money, even as a kid（因为他从小就非常擅长赚钱且非常成功）"],
                "answer": 3,
                "category": "Chapter 11-12"
            },
            {
                "question": "What disturbing event happened to Chris's mom in July of 1992?",
                "chinese": "1992年7月，克里斯的母亲遭遇了什么令人不安的事件？",
                "options": ["She woke up in the middle of the night because she thought she heard Chris calling for help.（她半夜醒来，以为听到克里斯在呼救）", "She got a note from Wayne Westerberg in South Dakota that Chris was missing（她收到来自南达科他州的韦恩·韦斯特伯格的纸条，说克里斯失踪了）", "Her stepson Sam came to the house to tell her and Walt that Chris was dead（她的继子山姆来到家里告诉她和沃尔特克里斯已经去世）", "She picked up a hitchhiker because she thought he was Chris.（她搭载了一个搭便车的人，因为她以为那是克里斯）"],
                "answer": 0,
                "category": "Chapter 11-12"
            },
            {
                "question": "What job did Chris get during the summer between his sophomore and junior years of college?",
                "chinese": "在大学二年级和三年级之间的暑假，克里斯从事了什么工作？",
                "options": ["tour guide at a national park（国家公园导游）", "construction worker（建筑工人）", "computer programmer（计算机程序员）", "pizza delivery guy（披萨送货员）"],
                "answer": 3,
                "category": "Chapter 11-12"
            },
            {
                "question": "Which topic is not included in essays written by Chris for school papers?",
                "chinese": "克里斯为学校论文写的文章中不包括哪个主题？",
                "options": ["Expose affairs of famous stars（揭露明星的丑闻）", "Criticize the Japanese for hunting whales（批评日本人捕鲸）", "Urge vigilance against Soviet Union（呼吁警惕苏联）", "Satirize Jimmy Carter（讽刺吉米·卡特）"],
                "answer": 0,
                "category": "Chapter 11-12"
            }
        ]
        # Chapter 6-13 选择题
        chapter_6_13_questions = [
            {
                "question": "Why did Alex decide to go to San Diego?",
                "chinese": "亚历克斯为什么决定去圣地亚哥？",
                "options": ["To set up camp（建立营地）", "To express his love to the 17-year old girl（向17岁女孩表达爱意）", "To earn money for his Alaska trip.（为阿拉斯加之行赚钱。）", "To visit Jan and Bob（拜访简和鲍勃）"],
                "answer": 2,
                "category": "Chapter 6"
            },
            {
                "question": "How did Franz react when he discovered that McCandless died?",
                "chinese": "当弗朗茨发现麦坎德莱斯去世时，他有什么反应？",
                "options": ["Franz became an Atheist（弗朗茨成为了无神论者）", "Franz renounced the Lord（弗朗茨背弃了上帝）", "All of the Above（以上皆是）", "Franz withdrew his church membership（弗朗茨退出了教会）"],
                "answer": 2,
                "category": "Chapter 6"
            },
            {
                "question": "What happened to Franz's family?",
                "chinese": "弗朗茨的家庭发生了什么变故？",
                "options": ["He became an Atheist（他成为了无神论者）", "It's unknown.（情况未知）", "Both his wife and his only child left home（他的妻子和独子都离开了家）", "His wife and his only child were killed by a drunk driver in an automobile accident.（他的妻子和独子在一场车祸中被酒驾司机撞死。）"],
                "answer": 3,
                "category": "Chapter 6"
            },
            {
                "question": "In a letter written from McCandless to Franz, McCandless encourages Franz to ______.",
                "chinese": "在麦坎德莱斯写给弗朗茨的信中，他鼓励弗朗茨______。",
                "options": ["reconnect with his family and restore his relationship with his brother（与家人重新联系并修复与兄弟的关系）", "leave all of his possessions behind and to live life to the fullest（抛下所有财产，尽情享受生活）", "travel with McCandless to Alaska（与麦坎德莱斯一起前往阿拉斯加旅行）", "meet a wife and settle down（结婚并安定下来）"],
                "answer": 1,
                "category": "Chapter 6"
            },
            {
                "question": "How many Okinawan children did Franz take under his wing in total?",
                "chinese": "弗朗茨总共收养了多少名冲绳儿童？",
                "options": ["14（14名）", "2（2名）", "15（15名）", "5（5名）"],
                "answer": 0,
                "category": "Chapter 6"
            },
            {
                "question": "What did Chris make at Franz's house?",
                "chinese": "克里斯在弗朗茨家制作了什么？",
                "options": ["a machete, an Arctic parka, a collapsible fishing pole, and some other gear（一把弯刀、一件北极派克大衣、一根可折叠钓鱼竿和其他装备）", "a leather belt with a record of his wanderings（一条记录他流浪经历的皮带）", "a bottle of whiskey（一瓶威士忌）", "a portrait of Ron Franz（一幅罗恩·弗朗茨的肖像）"],
                "answer": 1,
                "category": "Chapter 6"
            },
            {
                "question": "Franz reaches out to the magazine, Outside, with a written letter. Why?",
                "chinese": "弗朗茨写信给《Outside》杂志的目的是什么？",
                "options": ["He wants to determine if there were any copyright infringements（他想确认是否存在版权侵权）", "He wants a copy of the magazine that ran the story of Chris McCandless（他想要一本刊登克里斯·麦坎德莱斯故事的杂志）", "He wants to get in contact with Jon Krakauer to interview him for an upcoming television series（他想联系乔恩·克拉考尔，为即将播出的电视纪录片接受采访）", "He wants to get in touch with the McCandless family（他想联系麦坎德莱斯家人）"],
                "answer": 1,
                "category": "Chapter 6"
            },
            {
                "question": "What did Franz offer to Chris? How did Chris feel about it?",
                "chinese": "弗朗茨向克里斯提出了什么？克里斯对此有何感受？",
                "options": ["Leather work. He learned how to make a belt.（皮革工艺。他学会了制作皮带）", "They were killed by a drunk driver in a car accident.（他们在一场车祸中被酒驾司机撞死）", "To be his grandson; he was uncomfortable with it.（认他作孙子；克里斯对此感到不适）", "He became an atheist.（他成为了无神论者）"],
                "answer": 2,
                "category": "Chapter 6"
            },
            {
                "question": "What does Chris do in the Anza-Borrego Desert State Park?",
                "chinese": "克里斯在安萨波列戈沙漠州立公园做了什么？",
                "options": ["Earns money（赚钱）", "Looks for his possessions（寻找他的物品）", "Works in a grain elevator（在谷物升降机工作）", "Sets up camp（建立营地）"],
                "answer": 3,
                "category": "Chapter 6"
            },
            {
                "question": "Why does Ronald Franz take Christopher McCandless into his home?",
                "chinese": "罗纳德·弗朗茨为什么收留克里斯托弗·麦坎德莱斯？",
                "options": ["McCandless has offered to work in exchange for lodging.（麦坎德莱斯提出以工作换取住宿）", "Franz's wife likes McCandless.（弗朗茨的妻子喜欢麦坎德莱斯）", "McCandless reminds Franz of his own son, who is dead.（麦坎德莱斯让弗朗茨想起了自己已故的儿子）", "McCandless persuades him that it is his moral duty.（麦坎德莱斯说服他这是自己的道德责任）"],
                "answer": 2,
                "category": "Chapter 6"
            },
            {
                "question": "Alex felt _______ when he left Carthage?",
                "chinese": "亚历克斯离开迦太基时感觉如何？",
                "options": ["eager（渴望的）", "excited（兴奋的）", "sad（悲伤的）", "light-hearted（轻松愉快的）"],
                "answer": 2,
                "category": "Chapter 7"
            },
            {
                "question": "Alex impressed the people of Carthage with _______ on his last night in town?",
                "chinese": "亚历克斯在迦太基的最后一晚用什么给当地人留下了深刻印象？",
                "options": ["talking of books（谈论书籍）", "rice cooking（煮饭）", "piano playing（弹钢琴）", "dancing（跳舞）"],
                "answer": 2,
                "category": "Chapter 7"
            },
            {
                "question": "How did Chris keep in touch with Jan and Bob?",
                "chinese": "克里斯是如何与简和鲍勃保持联系的？",
                "options": ["Phone Calls（电话）", "Snapchat（Snapchat应用）", "Letters and postcards（信件和明信片）", "Emails（电子邮件）"],
                "answer": 2,
                "category": "Chapter 7"
            },
            {
                "question": "Which of the following statement is TRUE?",
                "chinese": "以下哪项陈述是正确的？",
                "options": ["Alex had been driven by a variety of lust offered by women.（亚历克斯被女性提供的各种欲望所驱使）", "Alex had never had the idea of getting married or having a family.（亚历克斯从未有过结婚或组建家庭的想法）", "Alex was sexual innocent as a monk.（亚历克斯像僧侣一样在性方面纯洁无暇）", "Alex was sexually intimate with men rather than women.（亚历克斯与男性而非女性有性亲密关系）"],
                "answer": 2,
                "category": "Chapter 7"
            },
            {
                "question": "In Alex's mind, his parents were all but ______.",
                "chinese": "在亚历克斯看来，他的父母几乎都是______，除了...",
                "options": ["irrational（不理性的）", "oppressive（压迫性的）", "hypocritical（虚伪的）", "conservative（保守的）"],
                "answer": 3,
                "category": "Chapter 7"
            }
        ]
        
        # 判断题
        true_false_questions = [
            {
                "question": "An editorial is usually longer than an Op-ed.",
                "chinese": "社论通常比专栏评论更长。",
                "type": "true_false",
                "answer": False,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "News stories are basically divided into two types: hard news and soft news. The former generally refers to up-to-the-minute news and events that are reported immediately, while the latter is background information or human-interest stories.",
                "chinese": "新闻基本分为两类：硬新闻和软新闻。前者通常指即时报道的新闻事件，后者则是背景信息或人情味故事。",
                "type": "true_false",
                "answer": True,
                "category": "新闻体裁+新闻导语"
            },
            {
                "question": "Generally speaking, there are more active voice headlines than passive voice headlines.",
                "chinese": "一般来说，主动语态的标题比被动语态的标题更多。",
                "type": "true_false",
                "answer": True,
                "category": "新闻语法"
            },
            {
                "question": "Headlines are not full sentences with some function words omitted.",
                "chinese": "标题不是完整的句子，省略了一些功能词。",
                "type": "true_false",
                "answer": True,
                "category": "新闻语法"
            }
        ]
        
        # 转换为Question对象
        all_questions_data = (intro_questions + genre_questions + grammar_questions + 
                             vocabulary_questions + rhetoric_questions + 
                             chapter_16_18_questions + chapter_1_5_questions + 
                             chapter_6_13_questions + chapter_11_12_questions+chapter_10_13_additional_questions)
        
        for q_data in all_questions_data:
            questions.append(Question(
                question_type="multiple_choice",
                question_text=q_data["question"],
                chinese_text=q_data["chinese"],
                options=q_data["options"],
                correct_answer=q_data["answer"],
                category=q_data["category"]
            ))
        
        for q_data in true_false_questions:
            questions.append(Question(
                question_type="true_false",
                question_text=q_data["question"],
                chinese_text=q_data["chinese"],
                options=["正确 (True)", "错误 (False)"],
                correct_answer=0 if q_data["answer"] else 1,
                category=q_data["category"]
            ))
        
        return questions
    
    def setup_ui(self):
        """设置用户界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg='#f0f0f0')
        title_frame.pack(pady=int(15 * self.font_scale), fill='x')
        
        title_label = tk.Label(title_frame, text="SCAU大学英语IV（阅读）刷题软件——山田凉出品！！", 
                              font=("微软雅黑", self.get_font_size(24), "bold"), 
                              bg='#f0f0f0', fg='#2c3e50')
        title_label.pack()
        
        # 控制面板
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(pady=int(10 * self.font_scale), fill='x')
        
        # 分类选择框架
        category_frame = tk.LabelFrame(control_frame, text="题目分类选择", 
                                      font=("微软雅黑", self.get_font_size(12), "bold"),
                                      bg='#f0f0f0', fg='#2c3e50')
        category_frame.pack(side='left', padx=int(10 * self.font_scale), pady=int(5 * self.font_scale))
        
        # 获取所有分类
        self.categories = list(set(q.category for q in self.all_questions))
        self.categories.sort()
        
        # 分类控制按钮框架
        button_control_frame = tk.Frame(category_frame, bg='#f0f0f0')
        button_control_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, int(5 * self.font_scale)))
        
        # 全选按钮
        self.select_all_button = tk.Button(button_control_frame, text="全选", 
                                          font=("微软雅黑", self.get_font_size(9)), 
                                          command=self.select_all_categories,
                                          bg='#27ae60', fg='white', 
                                          padx=int(8 * self.font_scale), pady=int(2 * self.font_scale))
        self.select_all_button.pack(side='left', padx=(0, int(5 * self.font_scale)))
        
        # 全不选按钮
        self.select_none_button = tk.Button(button_control_frame, text="全不选", 
                                           font=("微软雅黑", self.get_font_size(9)), 
                                           command=self.select_none_categories,
                                           bg='#e74c3c', fg='white', 
                                           padx=int(8 * self.font_scale), pady=int(2 * self.font_scale))
        self.select_none_button.pack(side='left')
        
        # 分类复选框
        self.category_vars = {}
        for i, category in enumerate(self.categories):
            var = tk.BooleanVar(value=True)  # 默认全选
            self.category_vars[category] = var
            self.selected_categories.add(category)
            
            cb = tk.Checkbutton(category_frame, text=category, variable=var,
                               font=("微软雅黑", self.get_font_size(10)),
                               bg='#f0f0f0', fg='#2c3e50',
                               command=self.update_question_filter)
            
            # 计算行列位置（每行3个，从第二行开始）
            row = (i // 3) + 1  # +1 是因为第一行被按钮占用了
            col = i % 3
            cb.grid(row=row, column=col, sticky='w', padx=int(5 * self.font_scale))
        
        # 模式控制框架
        mode_frame = tk.LabelFrame(control_frame, text="练习模式", 
                                  font=("微软雅黑", self.get_font_size(12), "bold"),
                                  bg='#f0f0f0', fg='#2c3e50')
        mode_frame.pack(side='left', padx=int(10 * self.font_scale), pady=int(5 * self.font_scale))
        
        # 全部题目按钮
        self.all_mode_button = tk.Button(mode_frame, text="全部题目", 
                                        font=("微软雅黑", self.get_font_size(11)), 
                                        command=self.switch_to_all_mode,
                                        bg='#3498db', fg='white', 
                                        padx=int(15 * self.font_scale), pady=int(5 * self.font_scale))
        self.all_mode_button.pack(side='top', pady=int(2 * self.font_scale))
        
        # 错题模式按钮
        self.wrong_mode_button = tk.Button(mode_frame, text=f"错题重练 ({len(self.wrong_questions)})", 
                                          font=("微软雅黑", self.get_font_size(11)), 
                                          command=self.switch_to_wrong_mode,
                                          bg='#e67e22', fg='white', 
                                          padx=int(15 * self.font_scale), pady=int(5 * self.font_scale))
        self.wrong_mode_button.pack(side='top', pady=int(2 * self.font_scale))
        
        # 清空错题按钮
        self.clear_wrong_button = tk.Button(mode_frame, text="清空错题", 
                                           font=("微软雅黑", self.get_font_size(11)), 
                                           command=self.clear_wrong_questions,
                                           bg='#95a5a6', fg='white', 
                                           padx=int(15 * self.font_scale), pady=int(5 * self.font_scale))
        self.clear_wrong_button.pack(side='top', pady=int(2 * self.font_scale))
        
        # 进度信息
        self.progress_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.progress_frame.pack(pady=int(8 * self.font_scale), fill='x')
        
        self.progress_label = tk.Label(self.progress_frame, text="", 
                                      font=("微软雅黑", self.get_font_size(13)), 
                                      bg='#f0f0f0', fg='#34495e')
        self.progress_label.pack()
        
        # 创建主内容区域（带滚动条）
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(pady=int(10 * self.font_scale), padx=int(20 * self.font_scale), 
                       fill='both', expand=True)
        
        # 创建Canvas和Scrollbar
        self.canvas = tk.Canvas(main_frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#f0f0f0')
        
        # 配置滚动
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 题目显示区域（放在scrollable_frame中）
        self.question_frame = tk.LabelFrame(self.scrollable_frame, text="题目", 
                                           font=("微软雅黑", self.get_font_size(14), "bold"), 
                                           bg='#ecf0f1', fg='#2c3e50', 
                                           padx=int(20 * self.font_scale), 
                                           pady=int(15 * self.font_scale))
        self.question_frame.pack(pady=int(10 * self.font_scale), 
                                fill='both', expand=True)
        
        # 英文题目 - 使用Text widget以便自动换行
        self.question_text = tk.Text(self.question_frame, 
                                    font=("Arial", self.get_font_size(13)), 
                                    bg='#ecf0f1', fg='#2c3e50',
                                    wrap='word', height=3, 
                                    relief='flat', borderwidth=0,
                                    state='disabled', cursor='arrow')
        self.question_text.pack(fill='x', pady=(0, int(12 * self.font_scale)))
        
        # 中文翻译 - 使用Text widget以便自动换行
        self.chinese_text = tk.Text(self.question_frame, 
                                   font=("微软雅黑", self.get_font_size(12)), 
                                   bg='#ecf0f1', fg='#7f8c8d',
                                   wrap='word', height=2, 
                                   relief='flat', borderwidth=0,
                                   state='disabled', cursor='arrow')
        self.chinese_text.pack(fill='x', pady=(0, int(18 * self.font_scale)))
        
        # 选项区域
        self.options_frame = tk.Frame(self.question_frame, bg='#ecf0f1')
        self.options_frame.pack(fill='both', expand=True)
        
        self.option_buttons = []
        
        # 答案反馈区域
        self.feedback_frame = tk.Frame(self.question_frame, bg='#ecf0f1')
        self.feedback_frame.pack(fill='x', pady=(int(15 * self.font_scale), 0))
        
        self.feedback_text = tk.Text(self.feedback_frame, 
                                    font=("微软雅黑", self.get_font_size(14), "bold"), 
                                    bg='#ecf0f1', height=2,
                                    wrap='word', relief='flat', borderwidth=0,
                                    state='disabled', cursor='arrow')
        self.feedback_text.pack(fill='x')
        
        # 按钮区域（固定在底部）
        self.button_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.button_frame.pack(side='bottom', pady=int(15 * self.font_scale), fill='x')
        
        # 创建按钮容器，居中显示
        button_container = tk.Frame(self.button_frame, bg='#f0f0f0')
        button_container.pack()
        
        # 按钮样式参数
        button_font = ("微软雅黑", self.get_font_size(12))
        button_padx = int(20 * self.font_scale)
        button_pady = int(8 * self.font_scale)
        button_spacing = int(10 * self.font_scale)
        
        # 上一题按钮
        self.prev_button = tk.Button(button_container, text="上一题", 
                                    font=button_font, 
                                    command=self.prev_question,
                                    bg='#95a5a6', fg='white', 
                                    padx=button_padx, pady=button_pady)
        self.prev_button.pack(side='left', padx=button_spacing)
        
        # 下一题按钮
        self.next_button = tk.Button(button_container, text="下一题", 
                                    font=button_font, 
                                    command=self.next_question,
                                    bg='#3498db', fg='white', 
                                    padx=button_padx, pady=button_pady)
        self.next_button.pack(side='left', padx=button_spacing)
        
        # 随机题目按钮
        self.random_button = tk.Button(button_container, text="随机题目", 
                                      font=button_font, 
                                      command=self.random_question,
                                      bg='#e74c3c', fg='white', 
                                      padx=button_padx, pady=button_pady)
        self.random_button.pack(side='left', padx=button_spacing)
        
        # 重置当前题按钮
        self.reset_button = tk.Button(button_container, text="重置当前题", 
                                     font=button_font, 
                                     command=self.reset_current_question,
                                     bg='#f39c12', fg='white', 
                                     padx=button_padx, pady=button_pady)
        self.reset_button.pack(side='left', padx=button_spacing)
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self._on_window_configure)
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_window_configure(self, event):
        """窗口大小变化时更新Canvas宽度"""  
        if event.widget == self.root:
            # 更新Canvas的宽度以匹配窗口宽度
            canvas_width = self.root.winfo_width() - 60  # 减去padding和scrollbar宽度
            self.canvas.itemconfig(self.canvas.find_all()[0], width=canvas_width)
            
            # 更新文本组件的换行宽度
            self._update_text_wraplength()
    
    def _update_text_wraplength(self):
        """更新文本组件的换行宽度"""
        # 计算可用宽度
        available_width = self.root.winfo_width() - 120  # 减去各种padding
        if available_width > 200:  # 确保有最小宽度
            # 更新题目和翻译文本的换行宽度
            char_width = 8  # 估算字符宽度
            wrap_length = max(50, available_width // char_width)
            
            # 由于Text widget使用字符数而不是像素，我们需要估算
            self.question_text.config(width=wrap_length)
            self.chinese_text.config(width=wrap_length)
            self.feedback_text.config(width=wrap_length)
    
    def update_question_filter(self):
        """更新题目筛选"""
        if self.is_wrong_question_mode:
            return  # 错题模式下不响应分类筛选
        
        # 更新选择的分类
        self.selected_categories.clear()
        for category, var in self.category_vars.items():
            if var.get():
                self.selected_categories.add(category)
        
        # 筛选题目
        if self.selected_categories:
            self.current_questions = [q for q in self.all_questions 
                                    if q.category in self.selected_categories]
        else:
            self.current_questions = self.all_questions.copy()
        
        # 重置到第一题
        self.current_question_index = 0
        if self.current_questions:
            self.load_question()
        else:
            self.show_no_questions_message()
    
    def switch_to_all_mode(self):
        """切换到全部题目模式"""
        self.is_wrong_question_mode = False
        self.update_question_filter()  # 应用分类筛选
        self.update_mode_buttons()
    
    def switch_to_wrong_mode(self):
        """切换到错题模式"""
        if not self.wrong_questions:
            messagebox.showinfo("提示", "当前没有错题！\n请先答错一些题目。")
            return
        
        self.is_wrong_question_mode = True
        self.current_questions = self.wrong_questions.copy()
        self.current_question_index = 0
        self.load_question()
        self.update_mode_buttons()
    
    def clear_wrong_questions(self):
        """清空错题列表"""
        if not self.wrong_questions:
            messagebox.showinfo("提示", "当前没有错题！")
            return
        
        result = messagebox.askyesno("确认", f"确定要清空所有 {len(self.wrong_questions)} 道错题吗？")
        if result:
            self.wrong_questions.clear()
            self.update_mode_buttons()
            if self.is_wrong_question_mode:
                self.switch_to_all_mode()
            messagebox.showinfo("成功", "错题列表已清空！")
    
    def update_mode_buttons(self):
        """更新模式按钮状态"""
        # 更新错题按钮文字
        self.wrong_mode_button.config(text=f"错题重练 ({len(self.wrong_questions)})")
        
        # 更新按钮颜色以显示当前模式
        if self.is_wrong_question_mode:
            self.all_mode_button.config(bg='#bdc3c7')
            self.wrong_mode_button.config(bg='#e67e22')
        else:
            self.all_mode_button.config(bg='#3498db')
            self.wrong_mode_button.config(bg='#bdc3c7')
        
        # 更新错题按钮状态
        if len(self.wrong_questions) == 0:
            self.wrong_mode_button.config(state='disabled')
            self.clear_wrong_button.config(state='disabled')
        else:
            self.wrong_mode_button.config(state='normal')
            self.clear_wrong_button.config(state='normal')
    
    def show_no_questions_message(self):
        """显示没有题目的消息"""
        self.progress_label.config(text="没有符合条件的题目，请重新选择分类。")
        
        # 清空题目显示区域
        self.question_text.config(state='normal')
        self.question_text.delete('1.0', tk.END)
        self.question_text.insert('1.0', "没有符合条件的题目")
        self.question_text.config(state='disabled')
        
        self.chinese_text.config(state='normal')
        self.chinese_text.delete('1.0', tk.END)
        self.chinese_text.insert('1.0', "请重新选择题目分类")
        self.chinese_text.config(state='disabled')
        
        # 清除选项
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.option_buttons.clear()
        
        # 禁用导航按钮
        self.prev_button.config(state='disabled')
        self.next_button.config(state='disabled')
        self.random_button.config(state='disabled')
        self.reset_button.config(state='disabled')
    
    def load_question(self):
        """加载当前题目"""
        if not self.current_questions:
            self.show_no_questions_message()
            return
        
        current_q = self.current_questions[self.current_question_index]
        self.has_answered = False
        
        # 更新进度信息
        mode_text = "错题模式" if self.is_wrong_question_mode else "全部题目"
        self.progress_label.config(
            text=f"第 {self.current_question_index + 1} 题 / 共 {len(self.current_questions)} 题  |  分类: {current_q.category}  |  模式: {mode_text}"
        )
        
        # 更新题目文本
        self.question_text.config(state='normal')
        self.question_text.delete('1.0', tk.END)
        self.question_text.insert('1.0', current_q.question_text)
        self.question_text.config(state='disabled')
        
        # 更新中文翻译
        self.chinese_text.config(state='normal')
        self.chinese_text.delete('1.0', tk.END)
        self.chinese_text.insert('1.0', f"中文翻译: {current_q.chinese_text}")
        self.chinese_text.config(state='disabled')
        
        # 清除之前的选项和反馈
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.option_buttons.clear()
        
        self.feedback_text.config(state='normal')
        self.feedback_text.delete('1.0', tk.END)
        self.feedback_text.config(state='disabled')
        
        # 创建新的选项按钮
        for i, option in enumerate(current_q.options):
            btn = tk.Button(self.options_frame, text=f"{chr(65+i)}. {option}",
                           font=("微软雅黑", self.get_font_size(12)), 
                           bg='#bdc3c7', fg='black',
                           anchor='w', pady=int(8 * self.font_scale),
                           wraplength=int(800 * self.font_scale),  # 添加文字换行
                           justify='left',
                           command=lambda idx=i: self.select_option(idx))
            btn.pack(fill='x', pady=int(4 * self.font_scale))
            self.option_buttons.append(btn)
        
        # 更新按钮状态
        self.prev_button.config(state='normal' if self.current_question_index > 0 else 'disabled')
        self.next_button.config(state='normal' if self.current_question_index < len(self.current_questions) - 1 else 'disabled')
        self.random_button.config(state='normal')
        self.reset_button.config(state='normal')
        
        # 滚动到顶部
        self.canvas.yview_moveto(0)
        
        # 更新文本换行
        self.root.after(100, self._update_text_wraplength)
    
    def select_option(self, selected_index):
        """选择选项并立即显示结果"""
        if self.has_answered:
            return
        
        self.has_answered = True
        current_q = self.current_questions[self.current_question_index]
        correct_index = current_q.correct_answer
        is_correct = selected_index == correct_index
        
        # 更新所有选项按钮的颜色
        for i, btn in enumerate(self.option_buttons):
            if i == correct_index:
                btn.config(bg='#2ecc71', fg='white')  # 正确答案显示绿色
            elif i == selected_index and i != correct_index:
                btn.config(bg='#e74c3c', fg='white')  # 错误选择显示红色
            else:
                btn.config(bg='#ecf0f1', fg='#7f8c8d')  # 其他选项显示灰色
            
            # 禁用所有按钮
            btn.config(state='disabled')
        
        # 显示反馈信息
        if is_correct:
            feedback_text = "✅ 回答正确！"
            feedback_color = '#27ae60'
        else:
            feedback_text = f"❌ 回答错误！正确答案是 {chr(65+correct_index)}. {current_q.options[correct_index]}"
            feedback_color = '#e74c3c'
            
            # 添加到错题列表（避免重复）
            if current_q not in self.wrong_questions:
                self.wrong_questions.append(current_q)
                self.update_mode_buttons()
        
        self.feedback_text.config(state='normal', fg=feedback_color)
        self.feedback_text.delete('1.0', tk.END)
        self.feedback_text.insert('1.0', feedback_text)
        self.feedback_text.config(state='disabled')
        
        # 如果回答正确，延迟0.5秒后自动跳到下一题
        if is_correct:
            self.root.after(500, self.auto_next_question)
    
    def auto_next_question(self):
        """自动跳转到下一题（仅在回答正确时调用）"""
        if self.current_question_index < len(self.current_questions) - 1:
            self.next_question()
        else:
            # 如果已经是最后一题，显示完成提示
            self.feedback_text.config(state='normal', fg='#8e44ad')
            current_text = self.feedback_text.get('1.0', tk.END).strip()
            self.feedback_text.delete('1.0', tk.END)
            self.feedback_text.insert('1.0', current_text + " 🎉 已完成所有题目！")
            self.feedback_text.config(state='disabled')

    def select_all_categories(self):
        """全选所有分类"""
        for var in self.category_vars.values():
            var.set(True)
        self.update_question_filter()
    
    def select_none_categories(self):
        """取消选择所有分类"""
        for var in self.category_vars.values():
            var.set(False)
        self.update_question_filter()
    
    def reset_current_question(self):
        """重置当前题目"""
        self.load_question()
    
    def next_question(self):
        """下一题"""
        if self.current_question_index < len(self.current_questions) - 1:
            self.current_question_index += 1
            self.load_question()
    
    def prev_question(self):
        """上一题"""
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.load_question()
    
    def random_question(self):
        """随机题目"""
        if self.current_questions:
            self.current_question_index = random.randint(0, len(self.current_questions) - 1)
            self.load_question()
    
    def select_all_categories(self):
        """全选分类"""
        for var in self.category_vars.values():
            var.set(True)
        self.update_question_filter()
    
    def select_none_categories(self):
        """全不选分类"""
        for var in self.category_vars.values():
            var.set(False)
        self.update_question_filter()

def main():
    """主函数"""
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()