# 命海拾遗API后端

## 项目介绍

命海拾遗API后端是一个基于Django REST Framework开发的命例数据管理系统，提供命例数据的查询、过滤和搜索功能。

## 技术栈

- **Python 3.12**
- **Django 6.0**
- **Django REST Framework**
- **MySQL 8.0**
- **Django Filter**
- **DRF YASG (Swagger文档)**
- **Docker** (可选)
- **Gunicorn** (生产环境)

## 项目结构

```
minghaishiyi/
├── minghaishiyi/          # 项目配置目录
│   ├── __init__.py
│   ├── settings.py        # Django配置文件
│   ├── urls.py            # 项目URL配置
│   ├── wsgi.py            # WSGI入口
│   └── logging.py         # 日志配置
├── minghub/               # 主应用目录
│   ├── __init__.py
│   ├── models.py          # 数据模型
│   ├── views.py           # 视图函数
│   ├── urls.py            # 应用URL配置
│   ├── serializers.py     # 序列化器
│   ├── exceptions.py      # 异常处理
│   └── migrations/        # 数据库迁移文件
├── manage.py              # Django管理脚本
├── requirements.txt       # 项目依赖
├── Dockerfile             # Docker配置
└── docker-compose.yml     # Docker Compose配置
```

## 安装和运行

### 环境要求

- Python 3.12
- MySQL 8.0

### 安装步骤

1. **克隆项目**

   ```bash
git clone <项目地址>
cd minghaishiyi
```

2. **创建虚拟环境**

   ```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**

   ```bash
pip install -r requirements.txt
```

4. **配置数据库**

   在 `minghaishiyi/settings.py` 中配置数据库连接：

   ```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'minghaishiyi',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

5. **执行数据库迁移**

   ```bash
python manage.py migrate
```

6. **导入数据** (可选)

   ```bash
python manage.py loaddata <data_file>
```

7. **运行开发服务器**

   ```bash
python manage.py runserver
```

   访问 `http://localhost:8000` 查看应用

### 生产环境部署

#### 使用Gunicorn

```bash
gunicorn minghaishiyi.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

#### 使用Docker

1. **构建并运行容器**

   ```bash
docker-compose up -d
```

2. **执行数据库迁移**

   ```bash
docker-compose exec web python manage.py migrate
```

3. **创建超级用户** (可选)

   ```bash
docker-compose exec web python manage.py createsuperuser
```

## API文档

项目集成了Swagger文档，访问以下地址查看API接口：

- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`

## API接口

### 命例数据接口

#### 获取命例列表

```
GET /api/destiny-cases/
```

**参数：**
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 20, 最大: 100)
- `search`: 搜索关键词 (支持年、月、日、时干支，来源，标签，反馈)
- `source`: 来源过滤
- `gender`: 性别过滤
- `year_ganzhi`: 年干支过滤
- `month_ganzhi`: 月干支过滤
- `day_ganzhi`: 日干支过滤
- `hour_ganzhi`: 时干支过滤
- `label`: 标签过滤

#### 获取单个命例

```
GET /api/destiny-cases/<id>/
```

## 异常处理

系统实现了统一的异常处理机制，主要处理404错误，返回格式如下：

```json
{
    "status": "error",
    "code": "not_found",
    "message": "请求的资源不存在"
}
```

## 日志配置

项目使用Django的日志系统，日志文件位于 `logs/` 目录下：
- `django.log`: Django系统日志
- `api_errors.log`: API错误日志

## 注意事项

1. 首次运行前请确保已正确配置数据库连接
2. 生产环境建议使用Gunicorn或其他WSGI服务器，不要使用Django开发服务器
3. 定期备份数据库
4. 根据实际需求调整日志级别和保留策略

## 许可证

MIT License