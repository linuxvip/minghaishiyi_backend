# ==================== 构建阶段 ====================
FROM docker.m.daocloud.io/library/python:3.12-slim AS builder

WORKDIR /app

# 替换 Debian 源为阿里云镜像
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list.d/aliyun.list \
    && echo "deb http://mirrors.aliyun.com/debian trixie-updates main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list \
    && echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list

# 复制 requirements.txt（在 pip install 之前）
COPY requirements.txt .

# 安装编译依赖 → pip install → 编译产物保留，其余丢弃
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip config set global.trusted-host mirrors.aliyun.com \
    && pip install --no-cache-dir --no-compile -r requirements.txt gunicorn \
    && apt-get purge -y build-essential default-libmysqlclient-dev pkg-config \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/local/lib/python3.12/site-packages -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.12/site-packages -name '*.pyc' -delete 2>/dev/null || true


# ==================== 运行阶段 ====================
FROM docker.m.daocloud.io/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=minghaishiyi.settings

WORKDIR /app

# 只安装运行时共享库（不含头文件和静态库）
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list.d/aliyun.list \
    && echo "deb http://mirrors.aliyun.com/debian trixie-updates main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list \
    && echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制编译好的 Python 包和 gunicorn 二进制
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# 复制项目文件（.dockerignore 生效）
COPY . .

# 复制并设置启动脚本权限
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 收集静态文件
RUN python manage.py collectstatic --noinput

EXPOSE 7777

CMD ["./entrypoint.sh"]