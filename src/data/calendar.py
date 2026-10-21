"""Calendario de mercado y manejo estricto de zona horaria America/New_York (ET).
Excluye feriados y días de cierre anticipado (sesión < 16:00 ET).
"""
from __future__ import annotations

import logging
from typing import List, Tuple
import pandas as pd
import pandas_market_calendars as mcal

logger = logging.getLogger(__name__)

TIMEZONE_ET = "America/New_York"
CALENDAR_NAME = "XNYS"  # Regular NYSE/CME equity index session


def get_market_sessions(start_date: str, end_date: str) -> Tuple[pd.DatetimeIndex, List[str]]:
    """Obtiene las fechas de sesiones hábiles normales (excluyendo feriados y cierres anticipados).
    
    Returns:
        valid_sessions: DatetimeIndex de fechas 'YYYY-MM-DD' en formato Timestamp UTC sin hora.
        excluded_early_closes: Lista de fechas excluidas por cierre anticipado.
    """
    nyse = mcal.get_calendar(CALENDAR_NAME)
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    
    # Identificar cierres anticipados: la hora de cierre normal es 16:00 ET (20:00 o 21:00 UTC)
    # Convertimos la columna market_close a America/New_York y verificamos si cierra antes de las 16:00 ET
    close_et = schedule["market_close"].dt.tz_convert(TIMEZONE_ET)
    
    # Cierre normal: hora == 16 y minuto == 0
    is_normal_close = (close_et.dt.hour == 16) & (close_et.dt.minute == 0)
    
    early_closes = schedule[~is_normal_close]
    excluded_dates = [d.strftime("%Y-%m-%d") for d in early_closes.index]
    
    normal_schedule = schedule[is_normal_close]
    valid_sessions = normal_schedule.index
    
    logger.info(
        f"Calendario {CALENDAR_NAME} ({start_date} a {end_date}): "
        f"{len(valid_sessions)} sesiones normales, {len(excluded_dates)} cierres anticipados excluidos."
    )
    return valid_sessions, excluded_dates


def utc_to_et(series_or_index: pd.DatetimeIndex | pd.Series) -> pd.DatetimeIndex | pd.Series:
    """Convierte timestamps UTC a America/New_York con manejo exacto de horario de verano (DST)."""
    if isinstance(series_or_index, pd.DatetimeIndex):
        if series_or_index.tz is None:
            return series_or_index.tz_localize("UTC").tz_convert(TIMEZONE_ET)
        return series_or_index.tz_convert(TIMEZONE_ET)
    elif isinstance(series_or_index, pd.Series):
        if series_or_index.dt.tz is None:
            return series_or_index.dt.tz_localize("UTC").dt.tz_convert(TIMEZONE_ET)
        return series_or_index.dt.tz_convert(TIMEZONE_ET)
    raise TypeError("Se esperaba pd.DatetimeIndex o pd.Series con datetimes.")
