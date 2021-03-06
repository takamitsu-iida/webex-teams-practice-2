#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import json
import logging
import os
import sys

from jinja2 import Environment, FileSystemLoader

import redis

import requests
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)

def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

if not here('./lib') in sys.path:
  sys.path.append(here('./lib'))

from botscript import bot, redis_url

# name and directory path of this application
app_name = os.path.splitext(os.path.basename(__file__))[0]
app_home = here('.')
conf_dir = os.path.join(app_home, 'conf')
data_dir = os.path.join(app_home, 'data')
card_dir = os.path.join(app_home, 'static', 'cards')


def send_text(text=None, to_person_email=None):
  kwargs = {}
  if text:
    kwargs.update({'text': text})
  if to_person_email:
    kwargs.update({'to_person_email': to_person_email})
  bot.send_message(**kwargs)


def send_card(text=None, card_name=None, to_person_email=None):
  kwargs = {}
  if text:
    kwargs.update({'text': text})

  if to_person_email:
    kwargs.update({'to_person_email': to_person_email})

  contents = get_card_content(card_name)
  if contents is None:
    return None
  kwargs.update({'attachments': [contents]})

  return bot.send_message(**kwargs)


def send_image(text=None, image_filename=None, to_person_email=None):
  return bot.send_image(text=text, image_filename=image_filename, to_person_email=to_person_email)


def store_message(send_result):
  if send_result is not None:
    if 'attachments' in send_result:
      del send_result['attachments']
    # print(json.dumps(send_result, ensure_ascii=False, indent=2))

    message_id = send_result.get('id')

    conn = redis.StrictRedis.from_url(redis_url, decode_responses=True)

    # store as hash
    conn.hmset(message_id, send_result)
    conn.expire(message_id, 600)  # time to live is 10 min


def show_redis_message_list():
  conn = redis.StrictRedis.from_url(redis_url, decode_responses=True)

  # show keys in db
  keys = conn.keys(pattern='*')
  for k in keys:
    print(k)

  # show values in db
  for k in keys:
    data = conn.hgetall(k)
    print(json.dumps(data, ensure_ascii=False, indent=2))


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


def send_weather_card(to_person_email=None):
  kwargs = {
    'text': "weather",
    'to_person_email': to_person_email
  }

  contents = get_weather_card()
  if contents is None:
    return
  kwargs.update({'attachments': [contents]})

  bot.send_message(**kwargs)


def get_weather_card():
  env = Environment(loader=FileSystemLoader(card_dir))
  template = env.get_template('weather.j2')

  data = get_weather_data()
  if data is None:
    return None

  rendered = template.render(data)
  content = json.loads(rendered)

  return {
    'contentType': "application/vnd.microsoft.card.adaptive",
    'content': content
  }


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

    to_person_email = os.environ.get('to_person_email')
    if to_person_email is None:
      sys.exit('failed to read to_person_email from os.environ')

    # send_text(text='はい！', to_person_email=to_person_email)
    # send_card(text='INPUT CARD', card_name='command.json', to_person_email=to_person_email)

    # send_result = send_card(text='CHOICE CARD', card_name='choice.json', to_person_email=to_person_email)
    # store_message(send_result)
    # show_redis_message_list()

    send_image(text='image', image_filename='/Users/iida/python/CF-F10/test/Sortable-master/st/face-01.jpg', to_person_email=to_person_email)

    # print(json.dumps(get_weather(), ensure_ascii=False, indent=2))
    # send_weather_card(to_person_email=to_person_email)

    return 0

  sys.exit(main())
