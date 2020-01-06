#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import json
import logging
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader

import requests
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


def plugin_props():
  return [
    {
      'name': "tenki",
      'description': "send weather forecast",
      'command': '/tenki',
      'func': plugin_main
    },
    {
      'name': "weather",
      'description': "alias of tenki",
      'command': '/weather',
      'func': plugin_main
    }
  ]


def plugin_main(bot=None, room_id=None, args=None):
  if not all([bot, room_id]):
    return

  city_name = '横浜'
  city_code = '140010'

  if args is not None and len(args) > 0:
    city_map = get_city_map()
    if args[0] in city_map:
      city_name = args[0]
      city_code = city_map.get(args[0])
    elif args[0] == 'list':
      msg = '\n'.join(city_map.keys())
      print(msg)
      bot.send_message(room_id=room_id, text=msg)
      return

  bot.send_message(room_id=room_id, text="{}の天気をお調べします。".format(city_name))

  data = get_weather_data(city_code=city_code)

  description = get_weather_description(data)
  if description:
    bot.send_message(room_id=room_id, text=description)

  card = get_weather_card(data)
  if card:
    kwargs = {
      'text': "weather",
      'room_id': room_id,
      'attachments': [card]
    }
    bot.send_message(**kwargs)


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
  descr = weather_data.get('description')
  descr = descr.replace('\n\n', '\n')
  return descr


def get_weather_data(city_code=None):
  """get weather information as json data.

  http://weather.livedoor.com/weather_hacks/webservice

  """
  # pylint: disable=broad-except

  if city_code is None:
    city_code = '140010'  # yokohama

  api_path = 'http://weather.livedoor.com/forecast/webservice/json/v1?city={}'.format(city_code)

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

def get_city_map():
  # http://weather.livedoor.com/forecast/rss/primary_area.xml
  rss = '''
    <city title="稚内" id="011000" source="http://weather.livedoor.com/forecast/rss/area/011000.xml"/>
    <city title="旭川" id="012010" source="http://weather.livedoor.com/forecast/rss/area/012010.xml"/>
    <city title="留萌" id="012020" source="http://weather.livedoor.com/forecast/rss/area/012020.xml"/>
    <city title="網走" id="013010" source="http://weather.livedoor.com/forecast/rss/area/013010.xml"/>
    <city title="北見" id="013020" source="http://weather.livedoor.com/forecast/rss/area/013020.xml"/>
    <city title="紋別" id="013030" source="http://weather.livedoor.com/forecast/rss/area/013030.xml"/>
    <city title="根室" id="014010" source="http://weather.livedoor.com/forecast/rss/area/014010.xml"/>
    <city title="釧路" id="014020" source="http://weather.livedoor.com/forecast/rss/area/014020.xml"/>
    <city title="帯広" id="014030" source="http://weather.livedoor.com/forecast/rss/area/014030.xml"/>
    <city title="室蘭" id="015010" source="http://weather.livedoor.com/forecast/rss/area/015010.xml"/>
    <city title="浦河" id="015020" source="http://weather.livedoor.com/forecast/rss/area/015020.xml"/>
    <city title="札幌" id="016010" source="http://weather.livedoor.com/forecast/rss/area/016010.xml"/>
    <city title="岩見沢" id="016020" source="http://weather.livedoor.com/forecast/rss/area/016020.xml"/>
    <city title="倶知安" id="016030" source="http://weather.livedoor.com/forecast/rss/area/016030.xml"/>
    <city title="函館" id="017010" source="http://weather.livedoor.com/forecast/rss/area/017010.xml"/>
    <city title="江差" id="017020" source="http://weather.livedoor.com/forecast/rss/area/017020.xml"/>
    <city title="青森" id="020010" source="http://weather.livedoor.com/forecast/rss/area/020010.xml"/>
    <city title="むつ" id="020020" source="http://weather.livedoor.com/forecast/rss/area/020020.xml"/>
    <city title="八戸" id="020030" source="http://weather.livedoor.com/forecast/rss/area/020030.xml"/>
    <city title="盛岡" id="030010" source="http://weather.livedoor.com/forecast/rss/area/030010.xml"/>
    <city title="宮古" id="030020" source="http://weather.livedoor.com/forecast/rss/area/030020.xml"/>
    <city title="大船渡" id="030030" source="http://weather.livedoor.com/forecast/rss/area/030030.xml"/>
    <city title="仙台" id="040010" source="http://weather.livedoor.com/forecast/rss/area/040010.xml"/>
    <city title="白石" id="040020" source="http://weather.livedoor.com/forecast/rss/area/040020.xml"/>
    <city title="秋田" id="050010" source="http://weather.livedoor.com/forecast/rss/area/050010.xml"/>
    <city title="横手" id="050020" source="http://weather.livedoor.com/forecast/rss/area/050020.xml"/>
    <city title="山形" id="060010" source="http://weather.livedoor.com/forecast/rss/area/060010.xml"/>
    <city title="米沢" id="060020" source="http://weather.livedoor.com/forecast/rss/area/060020.xml"/>
    <city title="酒田" id="060030" source="http://weather.livedoor.com/forecast/rss/area/060030.xml"/>
    <city title="新庄" id="060040" source="http://weather.livedoor.com/forecast/rss/area/060040.xml"/>
    <city title="福島" id="070010" source="http://weather.livedoor.com/forecast/rss/area/070010.xml"/>
    <city title="小名浜" id="070020" source="http://weather.livedoor.com/forecast/rss/area/070020.xml"/>
    <city title="若松" id="070030" source="http://weather.livedoor.com/forecast/rss/area/070030.xml"/>
    <city title="水戸" id="080010" source="http://weather.livedoor.com/forecast/rss/area/080010.xml"/>
    <city title="土浦" id="080020" source="http://weather.livedoor.com/forecast/rss/area/080020.xml"/>
    <city title="宇都宮" id="090010" source="http://weather.livedoor.com/forecast/rss/area/090010.xml"/>
    <city title="大田原" id="090020" source="http://weather.livedoor.com/forecast/rss/area/090020.xml"/>
    <city title="前橋" id="100010" source="http://weather.livedoor.com/forecast/rss/area/100010.xml"/>
    <city title="みなかみ" id="100020" source="http://weather.livedoor.com/forecast/rss/area/100020.xml"/>
    <city title="さいたま" id="110010" source="http://weather.livedoor.com/forecast/rss/area/110010.xml"/>
    <city title="熊谷" id="110020" source="http://weather.livedoor.com/forecast/rss/area/110020.xml"/>
    <city title="秩父" id="110030" source="http://weather.livedoor.com/forecast/rss/area/110030.xml"/>
    <city title="千葉" id="120010" source="http://weather.livedoor.com/forecast/rss/area/120010.xml"/>
    <city title="銚子" id="120020" source="http://weather.livedoor.com/forecast/rss/area/120020.xml"/>
    <city title="館山" id="120030" source="http://weather.livedoor.com/forecast/rss/area/120030.xml"/>
    <city title="東京" id="130010" source="http://weather.livedoor.com/forecast/rss/area/130010.xml"/>
    <city title="大島" id="130020" source="http://weather.livedoor.com/forecast/rss/area/130020.xml"/>
    <city title="八丈島" id="130030" source="http://weather.livedoor.com/forecast/rss/area/130030.xml"/>
    <city title="父島" id="130040" source="http://weather.livedoor.com/forecast/rss/area/130040.xml"/>
    <city title="横浜" id="140010" source="http://weather.livedoor.com/forecast/rss/area/140010.xml"/>
    <city title="小田原" id="140020" source="http://weather.livedoor.com/forecast/rss/area/140020.xml"/>
    <city title="新潟" id="150010" source="http://weather.livedoor.com/forecast/rss/area/150010.xml"/>
    <city title="長岡" id="150020" source="http://weather.livedoor.com/forecast/rss/area/150020.xml"/>
    <city title="高田" id="150030" source="http://weather.livedoor.com/forecast/rss/area/150030.xml"/>
    <city title="相川" id="150040" source="http://weather.livedoor.com/forecast/rss/area/150040.xml"/>
    <city title="富山" id="160010" source="http://weather.livedoor.com/forecast/rss/area/160010.xml"/>
    <city title="伏木" id="160020" source="http://weather.livedoor.com/forecast/rss/area/160020.xml"/>
    <city title="金沢" id="170010" source="http://weather.livedoor.com/forecast/rss/area/170010.xml"/>
    <city title="輪島" id="170020" source="http://weather.livedoor.com/forecast/rss/area/170020.xml"/>
    <city title="福井" id="180010" source="http://weather.livedoor.com/forecast/rss/area/180010.xml"/>
    <city title="敦賀" id="180020" source="http://weather.livedoor.com/forecast/rss/area/180020.xml"/>
    <city title="甲府" id="190010" source="http://weather.livedoor.com/forecast/rss/area/190010.xml"/>
    <city title="河口湖" id="190020" source="http://weather.livedoor.com/forecast/rss/area/190020.xml"/>
    <city title="長野" id="200010" source="http://weather.livedoor.com/forecast/rss/area/200010.xml"/>
    <city title="松本" id="200020" source="http://weather.livedoor.com/forecast/rss/area/200020.xml"/>
    <city title="飯田" id="200030" source="http://weather.livedoor.com/forecast/rss/area/200030.xml"/>
    <city title="岐阜" id="210010" source="http://weather.livedoor.com/forecast/rss/area/210010.xml"/>
    <city title="高山" id="210020" source="http://weather.livedoor.com/forecast/rss/area/210020.xml"/>
    <city title="静岡" id="220010" source="http://weather.livedoor.com/forecast/rss/area/220010.xml"/>
    <city title="網代" id="220020" source="http://weather.livedoor.com/forecast/rss/area/220020.xml"/>
    <city title="三島" id="220030" source="http://weather.livedoor.com/forecast/rss/area/220030.xml"/>
    <city title="浜松" id="220040" source="http://weather.livedoor.com/forecast/rss/area/220040.xml"/>
    <city title="名古屋" id="230010" source="http://weather.livedoor.com/forecast/rss/area/230010.xml"/>
    <city title="豊橋" id="230020" source="http://weather.livedoor.com/forecast/rss/area/230020.xml"/>
    <city title="津" id="240010" source="http://weather.livedoor.com/forecast/rss/area/240010.xml"/>
    <city title="尾鷲" id="240020" source="http://weather.livedoor.com/forecast/rss/area/240020.xml"/>
    <city title="大津" id="250010" source="http://weather.livedoor.com/forecast/rss/area/250010.xml"/>
    <city title="彦根" id="250020" source="http://weather.livedoor.com/forecast/rss/area/250020.xml"/>
    <city title="京都" id="260010" source="http://weather.livedoor.com/forecast/rss/area/260010.xml"/>
    <city title="舞鶴" id="260020" source="http://weather.livedoor.com/forecast/rss/area/260020.xml"/>
    <city title="大阪" id="270000" source="http://weather.livedoor.com/forecast/rss/area/270000.xml"/>
    <city title="神戸" id="280010" source="http://weather.livedoor.com/forecast/rss/area/280010.xml"/>
    <city title="豊岡" id="280020" source="http://weather.livedoor.com/forecast/rss/area/280020.xml"/>
    <city title="奈良" id="290010" source="http://weather.livedoor.com/forecast/rss/area/290010.xml"/>
    <city title="風屋" id="290020" source="http://weather.livedoor.com/forecast/rss/area/290020.xml"/>
    <city title="和歌山" id="300010" source="http://weather.livedoor.com/forecast/rss/area/300010.xml"/>
    <city title="潮岬" id="300020" source="http://weather.livedoor.com/forecast/rss/area/300020.xml"/>
    <city title="鳥取" id="310010" source="http://weather.livedoor.com/forecast/rss/area/310010.xml"/>
    <city title="米子" id="310020" source="http://weather.livedoor.com/forecast/rss/area/310020.xml"/>
    <city title="松江" id="320010" source="http://weather.livedoor.com/forecast/rss/area/320010.xml"/>
    <city title="浜田" id="320020" source="http://weather.livedoor.com/forecast/rss/area/320020.xml"/>
    <city title="西郷" id="320030" source="http://weather.livedoor.com/forecast/rss/area/320030.xml"/>
    <city title="岡山" id="330010" source="http://weather.livedoor.com/forecast/rss/area/330010.xml"/>
    <city title="津山" id="330020" source="http://weather.livedoor.com/forecast/rss/area/330020.xml"/>
    <city title="広島" id="340010" source="http://weather.livedoor.com/forecast/rss/area/340010.xml"/>
    <city title="庄原" id="340020" source="http://weather.livedoor.com/forecast/rss/area/340020.xml"/>
    <city title="下関" id="350010" source="http://weather.livedoor.com/forecast/rss/area/350010.xml"/>
    <city title="山口" id="350020" source="http://weather.livedoor.com/forecast/rss/area/350020.xml"/>
    <city title="柳井" id="350030" source="http://weather.livedoor.com/forecast/rss/area/350030.xml"/>
    <city title="萩" id="350040" source="http://weather.livedoor.com/forecast/rss/area/350040.xml"/>
    <city title="徳島" id="360010" source="http://weather.livedoor.com/forecast/rss/area/360010.xml"/>
    <city title="日和佐" id="360020" source="http://weather.livedoor.com/forecast/rss/area/360020.xml"/>
    <city title="高松" id="370000" source="http://weather.livedoor.com/forecast/rss/area/370000.xml"/>
    <city title="松山" id="380010" source="http://weather.livedoor.com/forecast/rss/area/380010.xml"/>
    <city title="新居浜" id="380020" source="http://weather.livedoor.com/forecast/rss/area/380020.xml"/>
    <city title="宇和島" id="380030" source="http://weather.livedoor.com/forecast/rss/area/380030.xml"/>
    <city title="高知" id="390010" source="http://weather.livedoor.com/forecast/rss/area/390010.xml"/>
    <city title="室戸岬" id="390020" source="http://weather.livedoor.com/forecast/rss/area/390020.xml"/>
    <city title="清水" id="390030" source="http://weather.livedoor.com/forecast/rss/area/390030.xml"/>
    <city title="福岡" id="400010" source="http://weather.livedoor.com/forecast/rss/area/400010.xml"/>
    <city title="八幡" id="400020" source="http://weather.livedoor.com/forecast/rss/area/400020.xml"/>
    <city title="飯塚" id="400030" source="http://weather.livedoor.com/forecast/rss/area/400030.xml"/>
    <city title="久留米" id="400040" source="http://weather.livedoor.com/forecast/rss/area/400040.xml"/>
    <city title="佐賀" id="410010" source="http://weather.livedoor.com/forecast/rss/area/410010.xml"/>
    <city title="伊万里" id="410020" source="http://weather.livedoor.com/forecast/rss/area/410020.xml"/>
    <city title="長崎" id="420010" source="http://weather.livedoor.com/forecast/rss/area/420010.xml"/>
    <city title="佐世保" id="420020" source="http://weather.livedoor.com/forecast/rss/area/420020.xml"/>
    <city title="厳原" id="420030" source="http://weather.livedoor.com/forecast/rss/area/420030.xml"/>
    <city title="福江" id="420040" source="http://weather.livedoor.com/forecast/rss/area/420040.xml"/>
    <city title="熊本" id="430010" source="http://weather.livedoor.com/forecast/rss/area/430010.xml"/>
    <city title="阿蘇乙姫" id="430020" source="http://weather.livedoor.com/forecast/rss/area/430020.xml"/>
    <city title="牛深" id="430030" source="http://weather.livedoor.com/forecast/rss/area/430030.xml"/>
    <city title="人吉" id="430040" source="http://weather.livedoor.com/forecast/rss/area/430040.xml"/>
    <city title="大分" id="440010" source="http://weather.livedoor.com/forecast/rss/area/440010.xml"/>
    <city title="中津" id="440020" source="http://weather.livedoor.com/forecast/rss/area/440020.xml"/>
    <city title="日田" id="440030" source="http://weather.livedoor.com/forecast/rss/area/440030.xml"/>
    <city title="佐伯" id="440040" source="http://weather.livedoor.com/forecast/rss/area/440040.xml"/>
    <city title="宮崎" id="450010" source="http://weather.livedoor.com/forecast/rss/area/450010.xml"/>
    <city title="延岡" id="450020" source="http://weather.livedoor.com/forecast/rss/area/450020.xml"/>
    <city title="都城" id="450030" source="http://weather.livedoor.com/forecast/rss/area/450030.xml"/>
    <city title="高千穂" id="450040" source="http://weather.livedoor.com/forecast/rss/area/450040.xml"/>
    <city title="鹿児島" id="460010" source="http://weather.livedoor.com/forecast/rss/area/460010.xml"/>
    <city title="鹿屋" id="460020" source="http://weather.livedoor.com/forecast/rss/area/460020.xml"/>
    <city title="種子島" id="460030" source="http://weather.livedoor.com/forecast/rss/area/460030.xml"/>
    <city title="名瀬" id="460040" source="http://weather.livedoor.com/forecast/rss/area/460040.xml"/>
    <city title="那覇" id="471010" source="http://weather.livedoor.com/forecast/rss/area/471010.xml"/>
    <city title="名護" id="471020" source="http://weather.livedoor.com/forecast/rss/area/471020.xml"/>
    <city title="久米島" id="471030" source="http://weather.livedoor.com/forecast/rss/area/471030.xml"/>
    <city title="南大東" id="472000" source="http://weather.livedoor.com/forecast/rss/area/472000.xml"/>
    <city title="宮古島" id="473000" source="http://weather.livedoor.com/forecast/rss/area/473000.xml"/>
    <city title="石垣島" id="474010" source="http://weather.livedoor.com/forecast/rss/area/474010.xml"/>
    <city title="与那国島" id="474020" source="http://weather.livedoor.com/forecast/rss/area/474020.xml"/>
  '''
  result_map = {}
  pattern = re.compile(r'.*\<city title=\"(\S+)\"\sid=\"(\d+)\"\s.*')
  for line in rss.splitlines():
    match = pattern.match(line)
    if match and len(match.groups()) > 1:
      city = match.group(1)
      cord = match.group(2)
      result_map[city] = cord
  return result_map


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    # print(json.dumps(get_weather_data(), ensure_ascii=False, indent=2))
    print(get_city_map())
    return 0

  sys.exit(main())
