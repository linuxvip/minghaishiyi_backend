import json
import os
import re
import time
import logging

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from django.db import close_old_connections
from django.db.models import F
from django.core.cache import cache
from django.utils import timezone
from minghub.models import ProcessingTask, DestinyCase

logger = logging.getLogger(__name__)

LABEL_API_DELAY = float(os.getenv('CLI_LABEL_API_DELAY', '1.0'))
LABEL_MAX_RETRIES = int(os.getenv('CLI_LABEL_MAX_RETRIES', '3'))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

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


def _get_api_config():
    key = cache.get('deepseek_api_key') or ''
    url = cache.get('deepseek_api_url') or ''
    if not key or not url:
        from minghub.models import SystemConfig
        configs = {c.key: c.value for c in SystemConfig.objects.filter(key__in=['deepseek_api_key', 'deepseek_api_url'])}
        key = configs.get('deepseek_api_key', '')
        url = configs.get('deepseek_api_url', '')
        if key:
            cache.set('deepseek_api_key', key, 3600)
        if url:
            cache.set('deepseek_api_url', url, 3600)
    if not key:
        key = os.getenv('DEEPSEEK_API_KEY', '')
    if not url:
        url = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com')
    return key, url


def build_label_user_prompt(feedback, year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi, gender):
    gender_str = "男" if gender == 1 else "女"

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


def _do_log(task_id: int, message: str):
    try:
        task = ProcessingTask.objects.get(pk=task_id)
        task.log += message + '\n'
        task.save(update_fields=['log'])
    except Exception as e:
        logger.error(f"日志写入失败 (task={task_id}): {e}")


def _fetch_article(url: str):
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=HEADERS, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.find('h1', {'id': 'activity-name'}) or \
                    soup.find('h1', {'class': 'title'}) or \
                    soup.find('title')
            title_text = title.get_text(strip=True) if title else "无标题"

            content_div = soup.find('div', {'id': 'js_content'}) or \
                          soup.find('div', {'class': 'rich_media_content'}) or \
                          soup.find('article')
            if content_div:
                text = content_div.get_text(separator='\n', strip=True)
            else:
                text = response.text

            return {"title": title_text, "text": text}
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        return None


def _extract_cases(article_text: str):
    try:
        api_key, api_url = _get_api_config()
        client = OpenAI(api_key=api_key, base_url=api_url)
        system_prompt = """
        你是一个专业的命理资料整理助手。请从下文中提取所有的命例及其反馈。
        输出格式必须为严格的 JSON 数组。

        字段说明：
        1. "gender": 性别（男/女/未知）
        2. "year": 年柱（如：庚午）
        3. "month": 月柱（如：戊寅）
        4. "day": 日柱（如：己丑）
        5. "hour": 时柱（如：辛未）
        6. "feedback": 命主的完整反馈原文，必须包含出生地、各标签及分值（如出身、学历、职业、婚姻、子女、财富层次等）、流年点射等所有内容，必须完整保留原文，不省略、不截断、不做任何总结或摘要。
        """
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": article_text}
            ],
            response_format={'type': 'json_object'}
        )
        content = response.choices[0].message.content
        if content is None:
            return []

        cases = json.loads(content)
        if isinstance(cases, dict) and 'cases' in cases:
            cases = cases['cases']
        return cases if isinstance(cases, list) else []
    except Exception as e:
        logger.error(f"API 提取命例失败: {e}")
        return []


def _extract_labels(case: dict):
    feedback = case.get("feedback", "")
    if not feedback:
        return {}

    year = case.get("year", "")
    month = case.get("month", "")
    day = case.get("day", "")
    hour = case.get("hour", "")
    gender = 1 if case.get("gender", "") == "男" else 0

    user_prompt = build_label_user_prompt(feedback, year, month, day, hour, gender)

    for attempt in range(LABEL_MAX_RETRIES):
        try:
            api_key, api_url = _get_api_config()
            client = OpenAI(api_key=api_key, base_url=api_url)
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

            if "感情特征" not in label:
                label["感情特征"] = []
            if "职业细分" not in label:
                label["职业细分"] = ""

            if "财富层次" in label:
                wealth_word = label["财富层次"]
                if wealth_word not in feedback:
                    del label["财富层次"]

            return label

        except Exception as e:
            if attempt < LABEL_MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 5)

    return {}


def process_task(task_id: int):
    close_old_connections()

    try:
        task = ProcessingTask.objects.get(pk=task_id)
    except ProcessingTask.DoesNotExist:
        return

    try:
        urls = [u.strip() for u in task.url.split('\n') if u.strip()]
        _do_log(task_id, f"共 {len(urls)} 个链接待处理")

        total_cases = 0

        for i, url in enumerate(urls, 1):
            _do_log(task_id, f"[{i}/{len(urls)}] 开始处理: {url}")
            _do_log(task_id, "  正在获取文章...")

            article = _fetch_article(url)
            if article is None:
                _do_log(task_id, "  [失败] 无法获取文章内容")
                continue

            _do_log(task_id, f"  文章标题: {article['title']}, 正文 {len(article['text'])} 字符")
            _do_log(task_id, "  调用 DeepSeek 提取命例...")

            cases = _extract_cases(article['text'])
            _do_log(task_id, f"  提取到 {len(cases)} 条命例")

            for case in cases:
                label = _extract_labels(case)
                time.sleep(LABEL_API_DELAY)

                gender_val = case.get("gender", "")
                gender = 1 if gender_val == "男" else 0
                gender_label = "乾造" if gender == 1 else "坤造"
                year_str = case.get("year", "")
                month_str = case.get("month", "")
                day_str = case.get("day", "")
                hour_str = case.get("hour", "")
                feedback = case.get("feedback", "")

                if not year_str or not month_str or not day_str or not hour_str:
                    _do_log(task_id, f"    [跳过] 八字字段不完整: {gender_label} {year_str} {month_str} {day_str} {hour_str}")
                    continue

                try:
                    DestinyCase.objects.create(
                        source=task.source_name,
                        gender=gender,
                        year_ganzhi=year_str,
                        month_ganzhi=month_str,
                        day_ganzhi=day_str,
                        hour_ganzhi=hour_str,
                        feedback=feedback,
                        original_url=url,
                        label=json.dumps(label, ensure_ascii=False) if label else None,
                    )
                    total_cases += 1
                    _do_log(task_id, f"    {gender_label} {year_str} {month_str} {day_str} {hour_str} 入库成功")
                except Exception as e:
                    _do_log(task_id, f"    {gender_label} {year_str} {month_str} {day_str} {hour_str} 入库失败: {e}")

            time.sleep(1)

        _do_log(task_id, f"处理完成，共入库 {total_cases} 条命例")

        task.status = 'done'
        task.cases_created = total_cases
        task.updated_at = timezone.now()
        task.save(update_fields=['status', 'cases_created', 'updated_at'])

    except Exception as e:
        logger.error(f"process_task 异常 (task={task_id}): {e}")
        try:
            task.refresh_from_db()
            task.status = 'failed'
            task.error_message = str(e)[:1000]
            task.updated_at = timezone.now()
            task.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception:
            pass
