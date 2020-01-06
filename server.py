#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import logging
import os
import subprocess
import sys

# decode/encode iso8601 datetime format
import dateutil.parser
import pytz

# redis client for python
import redis

from flask import Flask, request


def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

if not here('./lib') in sys.path:
  sys.path.append(here('./lib'))

# this is ./lib/teams/v1/bot.py Bot class instance
from botscript import bot, redis_port, redis_url

# this is lib/plugins/__init__.py
from plugins import plugin_map

DEBUG = True

if DEBUG:
  import json

# name and directory path of this application
app_name = os.path.splitext(os.path.basename(__file__))[0]
app_home = here('.')
conf_dir = os.path.join(app_home, 'conf')
data_dir = os.path.join(app_home, 'data')

# logging
logging.basicConfig()
logger = logging.getLogger(app_name)
logger.setLevel(logging.INFO)

app = Flask(app_name)

@app.route('/', methods=['POST'])
def webhook():

  # get the json data from request
  data = request.get_json().get('data')

  # print(json.dumps(data, ensure_ascii=False, indent=2))

  # in case of message
  # {
  #   "id": "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvM2YxMDk5ZjAtMjk3MC0xMWVhLWIwNzktYjk5NDQzYThkODJj",
  #   "roomId": "Y2lzY29zcGFyazovL3VzL1JPT00vNDQ4NWM5ZmUtMDNkYy0zNWVjLTlhZTctNmY4MThiZGM3NGQw",
  #   "roomType": "direct",
  #   "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS80MjgyYjBmNC03NGMxLTRjMTctYmZhYS1jYWM4ZTU4MGY1MDE",
  #   "personEmail": "takamitsu.iida@gmail.com",
  #   "created": "2019-12-28T12:47:45.935Z"
  # }

  # in case of submit
  # {
  #   "id": "Y2lzY29zcGFyazovL3VzL0FUVEFDSE1FTlRfQUNUSU9OLzIwNTZkMjcwLTJhY2ItMTFlYS04MGJhLTNkMDE1ODc2MTM4NQ",
  #   "type": "submit",
  #   "messageId": "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvZGMzY2JkNzAtMmFjYS0xMWVhLWE4YjAtZmZmYjVlZTYyMjMx",
  #   "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS80MjgyYjBmNC03NGMxLTRjMTctYmZhYS1jYWM4ZTU4MGY1MDE",
  #   "roomId": "Y2lzY29zcGFyazovL3VzL1JPT00vNDQ4NWM5ZmUtMDNkYy0zNWVjLTlhZTctNmY4MThiZGM3NGQw",
  #   "created": "2019-12-30T06:10:49.751Z"
  # }

  if 'created' not in data:
    logger.info("receive data: this is not created event ... ignoring it")
    return 'OK'

  if 'type' in data and data.get('type') == 'submit':
    logger.info("submit received")
    on_receive_submit(data)
    return 'OK'

  person_id = data.get('personId', '')
  if person_id == bot.get_bot_id():
    logger.info("receive data: my own message ... ignoring it")
    return 'OK'

  on_receive_message(data)
  return 'OK'


def on_receive_submit(data):
  attachment_id = data.get('id')
  attachment_data = bot.get_attachment(attachment_id=attachment_id)
  if not attachment_data:
    logger.error("failed to retreive submit data")
    return

  # message_id is the matching key against adaptive cards sent before
  message_id = attachment_data.get('messageId')

  # person_id is the person who submitted the data
  person_id = attachment_data.get('personId')
  # room_id = attachment_data.get('roomId')

  if DEBUG:
    print('server.py: on_receive_submit()')
    print('data')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print('\n')
    print('attachment_data')
    print(json.dumps(attachment_data, ensure_ascii=False, indent=2))

  conn = redis.StrictRedis.from_url(redis_url, decode_responses=True)
  redis_data = conn.hgetall(message_id)
  if redis_data:
    print("data found in redis")
    if redis_data.get('submitted_by') is None:
      conn.hset(message_id, 'submitted_by', person_id)
    else:
      print("already submitted by {}".format(redis_data.get('submitted_by')))
  else:
    print("no data found in redis")

  if 'created' in attachment_data:
    created = from_iso8601(attachment_data.get('created'))
    print(created)


def on_receive_message(data):
  message_id = data.get('id')
  room_id = data.get('roomId')

  # retreive the message contents
  message = bot.get_message_text(message_id=message_id)
  if message is None:
    logger.error("failed to retreive message: %s", message_id)
    return

  # debug
  if DEBUG:
    print('*'*10)
    print(message)
    print('*'*10)

  message = message.strip()
  if message == '':
    return

  mention = '@{} '.format(bot.bot_name)
  if message.startswith(mention):
    message = message.replace(mention, '')

  # command match
  if message.startswith('/'):
    parts = message.split()
    cmd = parts[0]
    args = parts[1:]
    if cmd in plugin_map:
      func = plugin_map.get(cmd)
    else:
      func = plugin_map.get('/')  # default is '/'
    func(bot=bot, room_id=room_id, args=args)

  # message match
  elif message in bot.on_message_functions:
    func = bot.on_message_functions.get(message)
    func(room_id=room_id)

  # unknown message
  elif message not in bot.on_message_functions:
    func = bot.on_message_functions.get('*')
    func(room_id=room_id)



def from_iso8601(iso_str=None):
  iso_date = dateutil.parser.parse(iso_str)
  if not iso_date.tzinfo:
    utc = pytz.utc
    iso_date = utc.localize(iso_date)
  return iso_date


# redis_port is defined in ./lib/botscript.py
def is_redis_server_running():
  return subprocess.run(['redis-cli', '-p', str(redis_port), 'ping'], check=False, stdout=subprocess.DEVNULL).returncode == 0


def shutdown_redis_server():
  subprocess.call(['redis-cli', '-p', str(redis_port), 'shutdown', 'save'])


def run_redis_server(config_path):
  if is_redis_server_running() is False:
    subprocess.Popen(['redis-server', config_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':

  assert bot.has_webhooks(), sys.exit("no webhook found for this bot. please run webhook.py --start")

  redis_config_file = '6399.conf'
  redis_config_path = os.path.join(conf_dir, redis_config_file)
  run_redis_server(redis_config_path)

  app.run(host='0.0.0.0', port=5000, use_reloader=True, debug=True)

  # or use following command for production environment
  # gunicorn -c ./conf/gunicorn.conf.py server:app
