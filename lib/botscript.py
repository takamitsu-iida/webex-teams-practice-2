#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, unused-argument

import logging
import os

from teams.v1.bot import Bot

logger = logging.getLogger(__name__)

# create Bot class instance
bot = Bot()

# redis parameter, see ./conf/6399.conf
redis_port = 6399
redis_url = os.environ.get('bot_redis_url') if os.environ.get('bot_redis_url') is not None else 'redis://localhost:{}'.format(str(redis_port))


@bot.on_message('あ')
def respond_to_a(room_id=None):
  bot.send_message(room_id=room_id, text='あいうえお')


@bot.on_message('*')
def default_response(room_id=None):
  bot.send_message(room_id=room_id, text="Sorry, could not understand that")
