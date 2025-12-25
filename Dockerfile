# 使用官方Python 3.12镜像作为基础镜像
FROM python:3.12-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off

# 创建并设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt文件并安装Python依赖
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

# 复制整个项目文件
COPY . .

# 设置Django环境变量
ENV DJANGO_SETTINGS_MODULE=minghaishiyi.settings

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 暴露端口
EXPOSE 8000

# 运行Gunicorn服务器
CMD ["gunicorn", "minghaishiyi.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]