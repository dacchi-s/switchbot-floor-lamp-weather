#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script controls a SwitchBot RGBICWW Floor Lamp based on the weather forecast
from Tsukumijima's weather API. It changes the lamp's RGB color or color temperature
depending on the highest chance of rain during the day (morning to night).

Settings:
- USE_COLOR_TEMPERATURE = 0 : Use RGB color mapping (default colors kept)
- USE_COLOR_TEMPERATURE = 1 : Use color temperature mapping (0% = 2700K warm, 100% = 6500K cool)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from typing import Tuple, Optional, Dict

import requests
from dotenv import load_dotenv

# ------------------------------
# Logging configuration
# ------------------------------
# Format the log output with time, module name, and message
formatter = "[%(levelname)-8s] %(asctime)s %(name)-12s %(message)s"
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger("switchbot-floor-lamp")

# ------------------------------
# Load environment variables
# ------------------------------
# This loads .env file variables into the environment
load_dotenv()

ACCESS_TOKEN = os.environ["SWITCHBOT_ACCESS_TOKEN"]
SECRET = os.environ["SWITCHBOT_SECRET"]
DEVICE_ID = os.environ["SWITCHBOT_FLOOR_LAMP_DEVICE_ID"]  # Floor Lamp device ID
CITY_CODE = os.environ["WEATHER_CITY_CODE"]               # Example: 130010 = Tokyo (Tokyo area)

# Enable color temperature mode if set to 1/true in .env
USE_COLOR_TEMPERATURE = os.getenv("USE_COLOR_TEMPERATURE", "0").lower() in ("1", "true", "t", "yes", "y")

API_BASE_URL = "https://api.switch-bot.com"
WEATHER_URL = "https://weather.tsukumijima.net/api/forecast/city"
HTTP_TIMEOUT = 10  # seconds

# ------------------------------
# Weather API helpers
# ------------------------------
def _to_int_pct(s: str) -> int:
    """Convert a string like '40%' to an integer. Return 0 if empty or invalid."""
    return int(re.sub(r"\D", "", s or "") or 0)

def get_today_rain_percent_max_all(city_code: str) -> int:
    """
    Get the maximum rain chance (%) for today from the morning to night periods:
    T06_12, T12_18, T18_24. Excludes T00_06 (midnight to early morning).
    Returns 0 if there is an error.
    """
    url = f"{WEATHER_URL}/{city_code}"
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rain: Dict[str, str] = data["forecasts"][0]["chanceOfRain"]  # 0 = today
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return 0

    # Extract each time range's rain chance
    slots = {
        "T06_12": _to_int_pct(rain.get("T06_12", "")),
        "T12_18": _to_int_pct(rain.get("T12_18", "")),
        "T18_24": _to_int_pct(rain.get("T18_24", "")),
    }
    # Get the maximum value among the selected slots
    val = max(slots.values())
    logger.info(f"[max_daylight] slots={slots} -> use {val}%")
    return val

# ------------------------------
# SwitchBot authentication & command sending
# ------------------------------
def generate_sign(token: str, secret: str, nonce: Optional[str] = None) -> Tuple[str, str, str]:
    """Generate authentication signature for SwitchBot API v1.1"""
    if nonce is None:
        nonce = str(uuid.uuid4())
    t = str(int(round(time.time() * 1000)))
    msg = f"{token}{t}{nonce}".encode("utf-8")
    secret_bytes = secret.encode("utf-8")
    sign = base64.b64encode(hmac.new(secret_bytes, msg=msg, digestmod=hashlib.sha256).digest()).decode("utf-8")
    return t, sign, nonce

def post_command(
    device_id: str,
    command: str,
    parameter: str = "default",
    command_type: str = "command",
) -> Optional[dict]:
    """
    Send a command to the specified SwitchBot device.
    Logs the result and returns the JSON response (None if request fails).
    """
    t, sign, nonce = generate_sign(ACCESS_TOKEN, SECRET)
    headers = {
        "Content-Type": "application/json; charset=utf8",
        "Authorization": ACCESS_TOKEN,
        "t": t,
        "sign": sign,
        "nonce": nonce,
    }
    url = f"{API_BASE_URL}/v1.1/devices/{device_id}/commands"
    body = {"command": command, "parameter": parameter, "commandType": command_type}
    data = json.dumps(body)

    try:
        logger.info(f"POST {url} {data}")
        r = requests.post(url, data=data, headers=headers, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        if payload.get("statusCode") != 100:
            logger.error(f"SwitchBot error: {payload}")
        else:
            logger.info(f"SwitchBot OK: {payload}")
        return payload
    except requests.exceptions.RequestException as e:
        logger.error(f"SwitchBot request error: {e}")
        return None

# ------------------------------
# Floor Lamp control functions
# ------------------------------
def clamp_brightness(brightness: int) -> int:
    """Ensure brightness is between 1 and 100."""
    try:
        b = int(brightness)
    except Exception:
        b = 100
    return max(1, min(100, b))

def set_lamp_rgb(device_id: str, color: Tuple[int, int, int], brightness: int = 100):
    """
    Turn on the Floor Lamp in RGB mode.
    - color: tuple (R, G, B) values from 0–255
    - brightness: integer from 1–100
    """
    (r, g, b) = [max(0, min(255, int(v))) for v in color]
    brightness = clamp_brightness(brightness)

    post_command(device_id, "setBrightness", str(brightness))
    post_command(device_id, "setColor", f"{r}:{g}:{b}")
    post_command(device_id, "turnOn")

def set_lamp_ct(device_id: str, color_temperature: int, brightness: int = 100):
    """
    Turn on the Floor Lamp in color temperature mode.
    - color_temperature: integer from 2700–6500 Kelvin
    - brightness: integer from 1–100
    """
    ct = max(2700, min(6500, int(color_temperature)))
    brightness = clamp_brightness(brightness)

    post_command(device_id, "setBrightness", str(brightness))
    post_command(device_id, "setColorTemperature", str(ct))
    post_command(device_id, "turnOn")

# ------------------------------
# Mapping: rain % -> RGB or CT
# ------------------------------
def map_rain_to_rgb(rain: int) -> Tuple[int, int, int]:
    """
    Map rain chance (%) to an RGB color.
      0%      -> Orange (255,127,0)
      ≤20%    -> Yellow (255,255,0)
      ≤40%    -> Light Green (127,255,0)
      ≤60%    -> Cyan (0,255,255)
      ≤80%    -> Blue (0,127,255)
      >80%    -> Dark Blue (0,0,255)
    """
    if rain == 0:
        return (255, 127, 0)
    if rain <= 20:
        return (255, 255, 0)
    if rain <= 40:
        return (127, 255, 0)
    if rain <= 60:
        return (0, 255, 255)
    if rain <= 80:
        return (0, 127, 255)
    return (0, 0, 255)

def map_rain_to_ct(rain: int) -> int:
    """
    Map rain chance (%) to a color temperature (Kelvin).
      0% -> 2700K (warm)
      100% -> 6500K (cool)
    """
    rain = max(0, min(100, int(rain)))
    ct_min, ct_max = 2700, 6500
    return int(ct_min + (ct_max - ct_min) * (rain / 100.0))

# ------------------------------
# Main execution
# ------------------------------
def main() -> bool:
    # Get today's maximum rain chance for daylight hours
    rain = get_today_rain_percent_max_all(CITY_CODE)
    logger.info(f"Rain chance used: {rain}%")

    brightness = 100  # Fixed brightness; can be changed if needed

    if USE_COLOR_TEMPERATURE:
        # Use color temperature mode
        ct = map_rain_to_ct(rain)
        logger.info(f"Set CT: {ct}K, Brightness: {brightness}")
        set_lamp_ct(DEVICE_ID, ct, brightness=brightness)
    else:
        # Use RGB color mode
        rgb = map_rain_to_rgb(rain)
        logger.info(f"Set RGB: {rgb}, Brightness: {brightness}")
        set_lamp_rgb(DEVICE_ID, rgb, brightness=brightness)

    return True

if __name__ == "__main__":
    main()
