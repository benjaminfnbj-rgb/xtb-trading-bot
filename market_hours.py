from datetime import datetime, time
import pytz

UTC = pytz.utc

# Horaires d'ouverture des marchés (en UTC)
MARKET_HOURS = {
    "EURUSD": {
        "open":  time(22, 0),   # Dimanche 22h00 UTC
        "close": time(22, 0),   # Vendredi 22h00 UTC
    },
    "XAUUSD": {
        "open":  time(23, 0),   # Dimanche 23h00 UTC
        "close": time(21, 0),   # Vendredi 21h00 UTC
    }
}

def is_market_open(symbol: str) -> bool:
    """Retourne True si le marché est ouvert pour ce symbole."""
    now = datetime.now(UTC)
    weekday = now.weekday()  # 0=Lundi, 4=Vendredi, 5=Samedi, 6=Dimanche
    current_time = now.time().replace(tzinfo=None)

    # Samedi = toujours fermé
    if weekday == 5:
        return False

    hours = MARKET_HOURS.get(symbol)
    if not hours:
        return False

    if symbol == "EURUSD":
        # Fermé du Vendredi 22h00 au Dimanche 22h00
        if weekday == 4 and current_time >= hours["close"]:
            return False
        if weekday == 6 and current_time < hours["open"]:
            return False
        return True

    if symbol == "XAUUSD":
        # Fermé du Vendredi 21h00 au Dimanche 23h00
        if weekday == 4 and current_time >= hours["close"]:
            return False
        if weekday == 6 and current_time < hours["open"]:
            return False
        return True

    return False

def get_status_all() -> dict:
    """Retourne le statut ouvert/fermé de tous les marchés."""
    return {symbol: is_market_open(symbol) for symbol in MARKET_HOURS}
