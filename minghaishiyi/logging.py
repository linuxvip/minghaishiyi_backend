import logging
import logging.config
import os

# 日志目录路径
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

# 创建日志目录
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志配置
LOGGING_CONFIG = None
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'api_error': {
            'format': '%(asctime)s - %(levelname)s - %(pathname)s - %(funcName)s - %(lineno)d - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'standard'
        },
        'api_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'api_errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'api_error',
            'encoding': 'utf-8'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'api_errors': {
            'handlers': ['api_errors', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'minghub': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# 应用日志配置
logging.config.dictConfig(LOGGING)