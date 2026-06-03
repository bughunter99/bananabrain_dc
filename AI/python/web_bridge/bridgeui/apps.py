from django.apps import AppConfig
import os


class BridgeuiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bridgeui"

    def ready(self) -> None:
        if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
            from .bridge import bridge_service
            from brain import get_strategy_runtime

            bridge_service.start_listener()
            get_strategy_runtime(bridge_service).start()
