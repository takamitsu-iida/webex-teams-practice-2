#!/usr/bin/env python
# pylint: disable=missing-docstring

import json
import logging
import os
import sys

from jinja2 import Environment, FileSystemLoader

import requests
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


def plugin_prop():
  return {
    'name': "weather",
    'description': "create weather adaptive cards"
  }


def plugin_main():
  weather_data = get_weather_data()
  return {
    'card': get_weather_card(weather_data),
    'description': get_weather_description(weather_data)
  }


def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

# name and directory path of this application
app_name = os.path.splitext(os.path.basename(__file__))[0]
app_home = here('../..')
card_dir = os.path.join(app_home, 'static', 'cards')


def get_card_content(card_name):
  card_path = os.path.join(card_dir, card_name)
  if not os.path.isfile(card_path):
    logger.error("card file is not found: %s", card_path)
    return None
  try:
    with open(card_path) as f:
      card = json.load(f)
    return {
      'contentType': "application/vnd.microsoft.card.adaptive",
      'content': card
    }
  except (IOError, json.JSONDecodeError) as e:
    logger.exception(e)
  return None


def get_weather_card(weather_data):
  if not weather_data:
    return None

  env = Environment(loader=FileSystemLoader(card_dir))
  template = env.get_template('weather.j2')

  rendered = template.render(weather_data)
  content = json.loads(rendered)

  return {
    'contentType': "application/vnd.microsoft.card.adaptive",
    'content': content
  }


def get_weather_description(weather_data):
  if not weather_data:
    return None
  return weather_data.get('description')


def get_weather_data():
  """get weather information as json data.

  http://weather.livedoor.com/weather_hacks/webservice

  """
  # pylint: disable=broad-except

  city = '140010'  # Yokohama

  api_path = 'http://weather.livedoor.com/forecast/webservice/json/v1?city={}'.format(city)

  get_result = None
  try:
    get_result = requests.get(api_path)
  except Exception:
    pass

  if get_result is None or not get_result.ok:
    print("failed")
    return None

  json_data = get_result.json()
  # data structures are described in http://weather.livedoor.com/weather_hacks/webservice

  def normalize(fcst):
    r = {}
    r['dateLabel'] = fcst.get('dateLabel', '-')
    r['date'] = fcst.get('date', '1970-01-01')
    r['telop'] = fcst.get('telop', '-')
    temp = fcst.get('temperature', {})
    r['temp_min'] = '-' if temp is None or temp.get('min') is None else temp.get('min', {}).get('celsius', '-')
    r['temp_max'] = '-' if temp is None or temp.get('max') is None else temp.get('max', {}).get('celsius', '-')
    image = fcst.get('image', {})
    r['img_url'] = '' if image is None else image.get('url', '')
    r['img_title'] = '-' if image is None else image.get('title', '-')
    return r

  fcst_today = json_data.get('forecasts', [{}, {}])[0]
  fcst_today = normalize(fcst_today)
  fcst_tomorrow = json_data.get('forecasts', [{}, {}])[1]
  fcst_tomorrow = normalize(fcst_tomorrow)

  city = json_data.get('location', {}).get('city', '-')
  title = json_data.get('title', '-')
  description = json_data.get('description', {}).get('text', '-')

  return {
    'city': city,                # "横浜"
    'title': title,              # "神奈川県 横浜 の天気"
    'description': description,
    'today': fcst_today,
    'tomorrow': fcst_tomorrow
  }
  # {
  #   "city": "横浜",
  #   "title": "神奈川県 横浜 の天気",
  #   "description": " 関東の東海上を、気圧の谷が東へ進んでいます。...",
  #   "today": {
  #     "dateLabel": "今日",
  #     "date": "2019-12-31",
  #     "telop": "晴れ",
  #     "temp_min": "-",
  #     "temp_max": "18",
  #     "img_url": "http://weather.livedoor.com/img/icon/1.gif",
  #     "img_title": "晴れ"
  #   },
  #   "tomorrow": {
  #     "dateLabel": "明日",
  #     "date": "2020-01-01",
  #     "telop": "晴時々曇",
  #     "temp_min": "5",
  #     "temp_max": "11",
  #     "img_url": "http://weather.livedoor.com/img/icon/2.gif",
  #     "img_title": "晴時々曇"
  #   }
  # }


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    print(json.dumps(get_weather_data(), ensure_ascii=False, indent=2))
    return 0

  sys.exit(main())
