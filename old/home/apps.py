from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
    
    def ready(self):
        """Start monitoring when Django starts"""
        # Only start in main process (not in reloader)
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from .telegram_monitor import start_monitoring
                start_monitoring()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to start monitoring: {e}")
