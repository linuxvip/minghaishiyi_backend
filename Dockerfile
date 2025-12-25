FROM docker.m.daocloud.io/library/python:3.12-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    DJANGO_SETTINGS_MODULE=minghaishiyi.settings

# 设置工作目录
WORKDIR /app

# 替换 Debian 源为阿里云，安装系统依赖
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list.d/aliyun.list \
    && echo "deb http://mirrors.aliyun.com/debian trixie-updates main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list\
    && echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list


RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      default-libmysqlclient-dev \
      pkg-config \
 && rm -rf /var/lib/apt/lists/*

# pip 国内源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
 && pip config set global.trusted-host mirrors.aliyun.com

# 复制 requirements 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 运行 Gunicorn
CMD ["gunicorn", "minghaishiyi.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

