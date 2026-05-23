# 命海拾遗

八字命例数据管理系统。存储、查询、管理中国传统八字（四柱）命理案例，附 CLI 工具用于从微信公众号文章抓取并提取命例数据。

## 技术栈

- **Python 3.12** / **Django 6.0** / **Django REST Framework 3.15**
- **MySQL 8.0**
- **Gunicorn** + **Docker** 生产部署
- **drf-yasg** Swagger / ReDoc API 文档

## 项目结构

```
minghaishiyi_backend/
├── minghaishiyi/              # Django 项目配置
│   ├── settings.py            # 全局配置（数据库、DRF、国际化）
│   ├── urls.py                # 根路由
│   ├── wsgi.py                # Gunicorn 入口
│   └── logging.py             # 日志配置
├── minghub/                   # 主应用
│   ├── models.py              # DestinyCase 数据模型
│   ├── views.py               # ViewSet + Serializer + Filter
│   ├── admin.py               # Django Admin 配置
│   ├── exceptions.py          # 自定义异常处理
│   └── management/commands/
│       └── import_excel.py    # Excel 批量导入命令
├── cli/                       # CLI 爬虫工具
│   ├── main.py                # 微信文章抓取 + DeepSeek 提取
│   └── urls.txt               # 待抓取文章 URL
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 快速开始

### 环境要求

- Python 3.12
- MySQL 8.0

### 本地运行

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制 .env.example 为 .env 并填写）
cp .env.example .env

# 执行数据库迁移
python manage.py migrate

# 启动开发服务器
python manage.py runserver
```

### Docker 部署

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
```

访问：
- 管理后台：`http://localhost:8000/admin/`
- API 文档：`http://localhost:8000/swagger/`

## API 接口

### 命例数据 `/api/destiny-cases/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/destiny-cases/` | 列表查询（支持分页、过滤） |
| GET | `/api/destiny-cases/{id}/` | 单条详情 |
| POST | `/api/destiny-cases/` | 新增命例（需密码验证） |

**过滤参数**（均支持模糊匹配）：

`gender` `year_ganzhi` `month_ganzhi` `day_ganzhi` `hour_ganzhi` `source` `label`

**分页参数**：`page`（默认 1）、`page_size`（默认 20，最大 100）

### 新增命例

```
POST /api/destiny-cases/
Content-Type: application/json

{
    "passwd": "minghaishiyi",
    "source": "铁口擂台",
    "gender": 1,
    "year_ganzhi": "庚午",
    "month_ganzhi": "戊寅",
    "day_ganzhi": "己丑",
    "hour_ganzhi": "辛未",
    "feedback": "...",
    "label": "..."
}
```

## 数据模型

### DestinyCase

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | CharField | 命例来源 |
| `gender` | SmallIntegerField | 1=乾造（男），0=坤造（女） |
| `year_ganzhi` | CharField | 年柱（如 庚午） |
| `month_ganzhi` | CharField | 月柱（如 戊寅） |
| `day_ganzhi` | CharField | 日柱（如 己丑） |
| `hour_ganzhi` | CharField | 时柱（如 辛未） |
| `feedback` | TextField | 命例反馈（可选） |
| `original_url` | URLField | 原文链接（可选） |
| `label` | CharField | 标签（可选） |

## CLI 工具

`cli/main.py` 独立于 Web 应用运行，用于从微信公众号文章批量提取命例：

```bash
# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY=your-key

# 编辑 urls.txt 放入微信文章链接，然后运行
python cli/main.py
```

结果保存到 `cli/cases.csv`。

## Excel 批量导入

```bash
# 将 Excel 文件放在 mingdata/命海拾遗-命例库.xlsx，然后运行
python manage.py import_excel
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Django 密钥 | — |
| `DEBUG` | 调试模式 | True |
| `DB_ENGINE` | 数据库引擎 | django.db.backends.mysql |
| `DB_NAME` | 数据库名 | minghaishiyi |
| `DB_USER` | 数据库用户 | root |
| `DB_PASSWORD` | 数据库密码 | — |
| `DB_HOST` | 数据库主机 | 1.1.1.1 |
| `DB_PORT` | 数据库端口 | 3306 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（CLI） | — |

## 许可证

MIT License
