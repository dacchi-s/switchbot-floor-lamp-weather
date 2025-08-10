# SwitchBot Floor Lamp Weather Controller

This Python script controls a **SwitchBot RGBICWW Floor Lamp** based on the daily weather forecast.  
It uses [Tsukumijima's weather API](https://github.com/tsukumijima/weather-api) to check the highest chance of rain during the day and adjusts the lamp's **RGB color** or **color temperature** accordingly.

## Features
- Gets today's rain forecast from **06:00 to 24:00** and selects the highest value.
- RGB mode: Changes lamp color according to rain chance (orange → yellow → green → cyan → blue).
- Color temperature mode: Adjusts between **2700K (warm)** and **6500K (cool)** depending on rain chance.
- Works with **SwitchBot API v1.1** authentication.

## Requirements
- Python 3.7+
- SwitchBot RGBICWW Floor Lamp
- [SwitchBot API token and secret](https://github.com/OpenWonderLabs/SwitchBotAPI)
- Tsukumijima weather city code (your region of interest)

## Installation
```bash
git clone https://github.com/yourusername/switchbot-floor-lamp-weather.git
cd switchbot-floor-lamp-weather
python3 -m venv iot
source iot/bin/activate
pip install --upgrade pip
pip install requests python-dotenv
```

## Configuration

Create a .env file in the same directory as the script:
```
SWITCHBOT_ACCESS_TOKEN=your_access_token
SWITCHBOT_SECRET=your_secret
SWITCHBOT_FLOOR_LAMP_DEVICE_ID=your_device_id
WEATHER_CITY_CODE=XXXXXX  # Set to your region of interest (City code from Tsukumijima API)
USE_COLOR_TEMPERATURE=0
# USE_COLOR_TEMPERATURE=0 → RGB mode (default)
# USE_COLOR_TEMPERATURE=1 → Color temperature mode
```

City Code Examples (Your Region of Interest)

Below are some example city codes from Tsukumijima Weather API.
Find the full list here: [City Code List](https://github.com/tsukumijima/weather-api).

| City / Area            | Code   |
|------------------------|--------|
| Tokyo (23 wards)       | 130010 |
| Tokyo (Tama area)      | 130020 |
| Sapporo                | 016010 |
| Sendai                 | 040010 |
| Niigata                | 150010 |
| Nagoya                 | 230010 |
| Osaka                  | 270000 |
| Kyoto                  | 260010 |
| Kobe                   | 280010 |
| Hiroshima              | 340010 |
| Fukuoka                | 400010 |
| Naha                   | 471010 |

Set the WEATHER_CITY_CODE in .env to the code for your location.

## Usage

Run manually:

python weather_floor_lamp.py

Run every day at 4:00 AM with cron:
```
crontab -e

Add:

0 4 * * * cd /path/to/project && /path/to/project/iot/bin/python weather_floor_lamp.py >> cron.log 2>&1
```

## Example RGB mapping

| Rain chance (%) | Color        |
|-----------------|--------------|
| 0               | Orange       |
| 1–20            | Yellow       |
| 21–40           | Light Green  |
| 41–60           | Cyan         |
| 61–80           | Blue         |
| 81–100          | Dark Blue    |

## References
[SwitchBot API Documentation](https://github.com/OpenWonderLabs/SwitchBotAPI)

[Tsukumijima Weather API](https://github.com/tsukumijima/weather-api)

[Zenn Article by tanny](https://zenn.dev/tanny/articles/808487545eb30f)
