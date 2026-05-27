from django.apps import AppConfig


class MinghubConfig(AppConfig):
    name = 'minghub'

    def ready(self):
        import minghub.signals  # noqa
