import os
import json
import time
import logging
import csv
import re
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from openai import OpenAI
from dotenv import dotenv_values

# ==================== 配置区域（从项目根目录 .env 文件读取） ====================

_cfg = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# 1. API 配置
DEEPSEEK_API_KEY = _cfg.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = _cfg.get("DEEPSEEK_API_URL", "https://api.deepseek.com")

# 命海拾遗API新增接口
MHSY_URL = _cfg.get("MHSY_URL", "")
MHSY_PASSWD = _cfg.get("MHSY_PASSWD", "minghaishiyi")

# 2. 文件配置
INPUT_FILE = _cfg.get("CLI_INPUT_FILE", "urls.txt")
OUTPUT_FILE = _cfg.get("CLI_OUTPUT_FILE", "cases.csv")
SOURCE_NAME = _cfg.get("CLI_SOURCE_NAME", "铁口擂台")

# 3. 日志配置
LOG_LEVEL = getattr(logging, _cfg.get("CLI_LOG_LEVEL", "INFO").upper(), logging.INFO)
LOG_FILE = _cfg.get("CLI_LOG_FILE", "app.log")

# 4. Label 提取配置
LABEL_API_DELAY = float(_cfg.get("CLI_LABEL_API_DELAY", "1.0"))
LABEL_MAX_RETRIES = int(_cfg.get("CLI_LABEL_MAX_RETRIES", "3"))

LABEL_SYSTEM_PROMPT = """你是一位专业的命理数据标注员。你需要从命理反馈文本中提取结构化标签，严格从指定的枚举值中选择，不要自由发挥。

请严格按照以下 JSON 格式和枚举值输出，不要输出任何其他内容：

{
  "出身": "枚举值：农村普通家庭 | 城市普通家庭 | 城市小康家庭 | 富裕家庭 | 单亲家庭 | 送养",
  "学历": "枚举值：小学 | 初中 | 高中 | 中专 | 技校 | 大专 | 本科 | 硕士 | 研究生 | 博士 | 博士后",
  "职业类别": "枚举值：公职 | 国企 | 医教金融 | 金融 | 经商 | 私企白领 | 自由职业",
  "职业细分": "自由文本，如'餐饮饭店'、'城管部门'、'护士'、'服装生意'",
  "婚姻状态": "枚举值：未婚 | 已婚(初婚) | 二婚 | 离异 | 丧偶 | 三婚及以上",
  "子女数量": 0或1或2或3或4,
  "子女构成": "枚举值：无 | 有子无女 | 有女无子 | 子女双全 | 多个",
  "财富层次": "枚举值：温饱 | 小康 | 小富 | 富裕 | 富贵 | 负债",
  "感情特征": ["枚举多选：感情不顺 | 多次分手/分合 | 出轨/婚外恋 | 靠异性供养 | 桃花旺盛 | 第三者关系 | 遇渣男/被骗 | 家暴 | 情感空白 | 不婚主义"]
}

提取规则：
1. 出身、学历、婚姻状态、子女、财富层次、职业 必须从原文对应字段提取，原文没有明确写则省略该键。
2. 【最高优先级】财富层次判断流程：
   - 在原文中找到"财富层次"和其后的冒号/分值
   - 提取冒号后面、分值提示后面的那个词（如"财富层次20分：小康"提取到的词就是"小康"）
   - 将这个词与枚举值做精确字符串匹配，原文写什么就输出什么，禁止同义替换
   - 重要：反馈中的"XX分"是文章评注的分值（如"20分"），跟财富等级高低无关。不要因为分值高就把"小康"改成"小富"！这两个是不同的独立概念
   - 如果提取到的词不在枚举值范围内 → 省略"财富层次"键
   - 示例："财富层次20分：小康" → 财富层次必须输出"小康"，严禁输出其他值
   - 严禁行为：根据文本中"买房""买车""收入高""年入百万"等描述去推断财富层次
3. 职业类别：参考原文"职业精准点射："来归类到枚举值中（如"经商-餐饮饭店"→类别"经商"，细分"餐饮饭店"）。如果原文只有"职业："而没有"职业精准点射："，则根据描述词照实归类，含混就不要提取。
4. 子女构成：原文"一个儿子"→"有子无女"；"一个女儿"→"有女无子"；"一儿一女"→"子女双全"；"无"→"无"。
5. 感情特征：从"流年点射"段落中提取，只提取文本明确体现的特征。原文字面没有匹配标签的，省略该字段而不要强行凑。
6. 婚姻状态：原文"一婚"→"已婚(初婚)"；"一婚离"→"离异"；"二婚离"→"离异"；"一婚丧夫"→"丧偶"。
7. 所有字段无法判断就省略，不要输出"不详"、null、空字符串。

输出前自检：
- 审视每个输出的key，问自己：原文中是否明确出现了这个字段的值？
- 特别检查"财富层次"：原文"财富层次："后面紧跟着的是否是枚举值之一？如果不是，立刻删除这个key。
- 财富层次复核（最严重的错误）：输出前，把原文"财富层次："后面紧跟的词和你的输出做逐字对比，两者必须完全一致。如果原文写的是"小康"，你必须输出"小康"，绝对不允许输出"小富"或其他词，否则立刻纠正。"""


# ==================== 工具函数 ====================

def build_label_user_prompt(feedback, year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi, gender):
    """构建标签提取的用户提示，附带强制逐字匹配指令"""
    gender_str = "男" if gender == 1 else "女"

    # 从 feedback 中提取财富层次原文，方便模型做精确匹配
    wealth_hint = ""
    m = re.search(r'财富层次\d*分?[：:]\s*(\S+)', feedback)
    if m:
        extracted_word = m.group(1)
        if extracted_word in ("温饱", "小康", "小富", "富裕", "富贵", "负债"):
            wealth_hint = (
                f"\n\n[强制指令] 原文明确出现了 财富层次={extracted_word}，"
                f"你必须输出 财富层次={extracted_word}，"
                f"绝对禁止改写为其他词。这是硬性约束。")

    return f"""请从以下命例反馈文本中提取结构化标签。

八字：{year_ganzhi} {month_ganzhi} {day_ganzhi} {hour_ganzhi}
性别：{gender_str}

反馈文本：
{feedback}{wealth_hint}

注意：反馈中"财富层次："字段后的内容请原样读取，如果后面紧跟的是"流年点射"或非枚举词汇，说明该项未填写，请省略财富层次。"""


# ==================== 核心类 ====================

class WeChatParser:
    """微信文章解析器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',       
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def fetch_article(self, url: str) -> Dict:
        """获取文章内容"""
        logging.info(f"正在获取文章: {url}")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # 提取标题
                title = soup.find('h1', {'id': 'activity-name'}) or \
                        soup.find('h1', {'class': 'title'}) or \
                        soup.find('title')
                title_text = title.get_text(strip=True) if title else "无标题"

                # 提取正文
                content_div = soup.find('div', {'id': 'js_content'}) or \
                              soup.find('div', {'class': 'rich_media_content'}) or \
                              soup.find('article')

                if content_div:
                    text = content_div.get_text(separator='\n', strip=True)
                else:
                    text = response.text

                return {
                    "url": url,
                    "title": title_text,
                    "text": text
                }

        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP 错误: {e}")
            return {}
        except Exception as e:
            logging.error(f"获取文章失败: {e}")
            return {}

    def summarize_article(self, article_text: str) -> List[Dict]:
        """使用 DeepSeek API 总结文章"""
        logging.info("开始调用 DeepSeek API 提取命例信息")
        try:
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_URL
                )
            system_prompt = """
            你是一个专业的命理资料整理助手。请从下文中提取所有的命例及其反馈。
            输出格式必须为严格的 JSON 数组。

            字段说明：
            1. "gender": 性别（男/女/未知）
            2. "year": 年柱（如：庚午）
            3. "month": 月柱（如：戊寅）
            4. "day": 日柱（如：己丑）
            5. "hour": 时柱（如：辛未）
            6. "feedback": 命主的真实反馈原话（必须保留原文，不做总结）
            """
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": article_text}
                ],
                response_format={'type': 'json_object'}
            )
            result = response.choices[0].message.content
            logging.info("API 调用成功")

            if result is None:
                logging.error("API 返回内容为空")
                return []
            cases = json.loads(result)
            if isinstance(cases, dict) and 'cases' in cases:
                cases = cases['cases']

            logging.info(f"提取到 {len(cases)} 条命例")
            return cases if isinstance(cases, list) else []
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解析失败: {e}")
            return []
        except Exception as e:
            logging.error(f"API 调用失败: {e}")
            return []

    def extract_labels(self, case: Dict) -> Dict:
        """从单条命例的 feedback 中提取结构化标签"""
        feedback = case.get("feedback", "")
        if not feedback:
            logging.info("  无 feedback，跳过标签提取")
            return {}

        year = case.get("year", "")
        month = case.get("month", "")
        day = case.get("day", "")
        hour = case.get("hour", "")
        gender = 1 if case.get("gender", "") == "男" else 0

        user_prompt = build_label_user_prompt(feedback, year, month, day, hour, gender)

        last_error = None
        for attempt in range(LABEL_MAX_RETRIES):
            try:
                client = OpenAI(
                    api_key=DEEPSEEK_API_KEY,
                    base_url=DEEPSEEK_API_URL
                )
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": LABEL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content is None:
                    raise RuntimeError("API 返回内容为空")

                content = re.sub(r"^```(?:json)?\s*", "", content.strip())
                content = re.sub(r"\s*```$", "", content)
                label = json.loads(content)

                # 校验
                if "感情特征" not in label:
                    label["感情特征"] = []
                if "职业细分" not in label:
                    label["职业细分"] = ""

                # 后校验：财富层次必须能在 feedback 中找到原文
                if "财富层次" in label:
                    wealth_word = label["财富层次"]
                    if wealth_word not in feedback:
                        logging.warning(f"  财富层次校验失败: '{wealth_word}' 在反馈中不存在，已删除该字段")
                        del label["财富层次"]

                logging.info(f"  标签提取成功: 出身={label.get('出身', '-')} 学历={label.get('学历', '-')} 职业={label.get('职业类别', '-')} 婚姻={label.get('婚姻状态', '-')} 财富={label.get('财富层次', '-')}")
                return label

            except Exception as e:
                last_error = e
                if attempt < LABEL_MAX_RETRIES - 1:
                    wait = (attempt + 1) * 5
                    logging.warning(f"  标签提取重试 ({attempt+1}/{LABEL_MAX_RETRIES})，等待 {wait}s: {e}")
                    time.sleep(wait)

        logging.error(f"  标签提取最终失败: {last_error}")
        return {}


# ==================== 工具函数 ====================

def setup_logging():
    """配置日志模块"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding='utf-8')
        ]
    )


def save_to_csv(results: List[Dict], output_file: str):
    """保存命例结果到 CSV 文件"""
    if not results:
        logging.warning("没有命例数据可保存")
        return

    fieldnames = ['来源', '性别', '年柱', '月柱', '日柱', '时柱', '反馈', '链接']

    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"命例已保存到: {output_file}")
    except Exception as e:
        logging.error(f"保存 CSV 失败: {e}")

def send_record_to_api(
    source, gender, year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi,
    feedback, label=None, passwd=None
):
    if passwd is None:
        passwd = MHSY_PASSWD
    if label is None:
        label = {}
    if isinstance(label, dict):
        label = json.dumps(label, ensure_ascii=False)
    record = {
        "source": source,
        "gender": gender,
        "year_ganzhi": year_ganzhi,
        "month_ganzhi": month_ganzhi,
        "day_ganzhi": day_ganzhi,
        "hour_ganzhi": hour_ganzhi,
        "feedback": feedback,
        "passwd": passwd,
        "label": label,
    }
    response = httpx.post(MHSY_URL, json=record)
    return response

# ==================== 主程序 ====================

def main():
    setup_logging()
    logging.info("=" * 50)
    logging.info("微信文章命理信息提取工具启动")

    if not DEEPSEEK_API_KEY:
        logging.error("未设置 DEEPSEEK_API_KEY 环境变量")
        return
    if not MHSY_URL:
        logging.error("未设置 MHSY_URL 环境变量")
        return

    # 检查输入文件
    if not os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "w") as f:
            f.write("# 在此粘贴微信链接，每行一个\n")
        logging.warning(f"输入文件 {INPUT_FILE} 不存在，已创建示例文件")
        logging.info(f"请在 {INPUT_FILE} 中放入链接后重新运行")
        return

    # 读取链接
    with open(INPUT_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        logging.warning("没有找到待处理的链接")
        return

    parser = WeChatParser()
    all_cases = []

    logging.info(f"开始处理，共 {len(urls)} 条链接...")

    for idx, url in enumerate(urls, 1):
        logging.info(f"进度: [{idx}/{len(urls)}] {url}")
        article_data = parser.fetch_article(url)
        if article_data:
            cases = parser.summarize_article(article_data["text"])
            for case in cases:
                # 提取结构化标签
                label = parser.extract_labels(case)
                time.sleep(LABEL_API_DELAY)

                # 提交api
                res = send_record_to_api(
                    source=SOURCE_NAME,
                    gender=1 if case.get("gender", "") == "男" else 0,
                    year_ganzhi=case.get("year", ""),
                    month_ganzhi=case.get("month", ""),
                    day_ganzhi=case.get("day", ""),
                    hour_ganzhi=case.get("hour", ""),
                    feedback=case.get("feedback", ""),
                    label=label,
                )
                if res.status_code == 201:
                    logging.info("命例库记录新增成功:{}-{} {} {} {}".format(
                        "乾造" if case.get("gender", "") == "男" else "坤造",
                        case.get("year", ""), case.get("month", ""), case.get("day", ""), case.get("hour", "")))
                else:
                    logging.error("命例库记录新增失败:{}-{} {} {} {}".format(
                        "乾造" if case.get("gender", "") == "男" else "坤造",
                        case.get("year", ""), case.get("month", ""), case.get("day", ""), case.get("hour", "")))

                case_record = {
                    "来源": SOURCE_NAME,
                    "性别": case.get("gender", ""),
                    "年柱": case.get("year", ""),
                    "月柱": case.get("month", ""),
                    "日柱": case.get("day", ""),
                    "时柱": case.get("hour", ""),
                    "反馈": case.get("feedback", ""),
                    "链接": url
                }
                all_cases.append(case_record)
            logging.debug(f"第 {idx} 条处理完成")

        # 频率控制，保护 API
        time.sleep(1)

    save_to_csv(all_cases, OUTPUT_FILE)
    logging.info("所有任务处理完成")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()