from django.apps import AppConfig

class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        pass  # ここでapi.signalsのインポートを削除しました
