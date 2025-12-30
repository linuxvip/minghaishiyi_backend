import os
import json
import time
import logging
import csv
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from openai import OpenAI


# ==================== 配置区域 ====================

# 1. API 配置
DEEPSEEK_API_KEY = "sk-5c65faaab92d4b1f930cac6dcf6e292b"  # 替换为你的 API Key
DEEPSEEK_API_URL = "https://api.deepseek.com"

# 2. 文件配置
INPUT_FILE = "urls.txt"      # 存放链接的文件，每行一个 URL
OUTPUT_FILE = "cases.csv"    # 命例输出文件路径
SOURCE_NAME = "铁口擂台"      # 数据来源名称

# 3. 日志配置
LOG_LEVEL = logging.INFO
LOG_FILE = "app.log"


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
                model="deepseek-chat",
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


# ==================== 主程序 ====================

def main():
    setup_logging()
    logging.info("=" * 50)
    logging.info("微信文章命理信息提取工具启动")
    
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
