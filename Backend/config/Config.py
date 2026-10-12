"""Point d'entrée historique de la configuration.

`Config` est l'instance de `Settings` (voir `config/settings.py`) : l'import ne
fait plus aucun effet de bord et n'échoue plus si une clé est absente.
"""

from config.settings import Settings, get_settings

Config: Settings = get_settings()


class SPEAKER_TYPES:
    USER = "user"
    BOT = "bot"
