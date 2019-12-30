#!/usr/bin/env python
# pylint: disable=missing-docstring

import logging
import os
import sys

import dateutil.parser
import pytz

from flask import Flask, request

def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

if not here('./lib') in sys.path:
  sys.path.append(here('./lib'))

# this is ./lib/teams/v1/bot.py Bot class instance
# please see ./lib/botscript.py
from botscript import bot

DEBUG = True

if DEBUG:
  import json

# name of this application
app_name = os.path.splitext(os.path.basename(__file__))[0]

logger = logging.getLogger(app_name)
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

app = Flask(app_name)

@app.route('/', methods=['POST'])
def webhook():

  # get the json data from request
  json_data = request.get_json()
  data = json_data.get('data')

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

  person_id = data.get('personId', '')

  if 'type' in data and data.get('type') == 'submit':
    logger.info("submit received from %s", person_id)
    on_receive_submit(data)
    return "successfully receive submit"

  if person_id == bot.get_bot_id():
    logger.info("this message is my own ... ignoring it")
    return "this message is my own ... ignoring it"

  on_receive_message(data)
  return "successfully receive message"


def on_receive_submit(data):
  if DEBUG:
    print(json.dumps(data, ensure_ascii=False, indent=2))
  attachment_id = data.get('id')
  attachment_data = bot.get_attachment(attachment_id=attachment_id)
  if not attachment_data:
    logger.error("failed to retreive submit data")
    return

  if DEBUG:
    print(json.dumps(attachment_data, ensure_ascii=False, indent=2))


def on_receive_message(data):
  message_id = data.get('id')
  room_id = data.get('roomId')

  # retreive the message contents
  message = bot.get_message_text(message_id=message_id)
  if message is None:
    logger.error("failed to retreive message: %s", message_id)
    return

  # debug
  print(message)
  print('*'*10)

  if message.strip() != '' and message in bot.on_message_functions:
    func = bot.on_message_functions.get(message)
    func(room_id=room_id)

  elif message.strip() != '' and message not in bot.on_message_functions:
    func = bot.on_message_functions.get('*')
    func(room_id=room_id)


def from_iso8601(iso_str=None):
  iso_date = dateutil.parser.parse(iso_str)
  if not iso_date.tzinfo:
    utc = pytz.utc
    iso_date = utc.localize(iso_date)
  return iso_date


if __name__ == '__main__':

  app.run(host='127.0.0.1', port=5000, use_reloader=True, debug=True)
