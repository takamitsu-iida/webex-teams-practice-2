#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
"""Bot for Webex Teams

- Define decorator for bot
- Show/Create/Delete webhook for Webex Teams

Links:
  - user account: https://developer.webex.com/
  - webhook api: https://developer.webex.com/docs/api/v1/webhooks
  - buttons and cards: https://developer.webex.com/docs/api/guides/cards
"""

import json
import logging
import os
import sys

import requests
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)

class Bot:

  TIMEOUT = (10.0, 30.0)  # (connect timeout, read timeout)

  def __init__(self, bot_name=None):

    bot_name = os.getenv('bot_name') if bot_name is None else bot_name
    if bot_name is None or bot_name.strip() == '':
      sys.exit("please set environment variable 'bot_name' before run this script")
    self.bot_name = bot_name

    self._bot_id = None  # get_bot_id() set this value and returns it

    self.auth_token = self.get_auth_token(bot_name=bot_name)
    if self.auth_token is None:
      sys.exit("failed to get authentication token for {}".format(bot_name))

    self.headers = {
      'Authorization': "Bearer {}".format(self.auth_token),
      'content-type': "application/json"
    }

    # functions with decorator will be stored in this dict object
    self.on_message_functions = {}
    self.on_command_functions = {}


  def on_message(self, message_text):
    """Decorator for the on_message

    Arguments:
        message_text {str} -- the message text correspond to the function

    Returns:
        [func] -- decorator function
    """
    def decorator(func):
      self.on_message_functions[message_text] = func
    return decorator


  def on_command(self, command=None):
    """Decorator for the on_command

    Arguments:
        command {str} -- the command text correspond to the function
        plugin

    Returns:
        [func] -- decorator function
    """
    def decorator(func):
      self.on_command_functions[command] = func
    return decorator


  @staticmethod
  def get_auth_token(bot_name=None):
    """Get authentication token by bot name.

    first, try to get token from environment variable,
    then read from file ~/.{{ bot name }}

    Keyword Arguments:
        bot_name {str} -- name of the bot (default: {None})

    Returns:
        str -- authentication token if found else None
    """

    # 1st get token from environment: bot_token
    token = os.getenv('bot_token')
    if token:
      return token

    # 2nd get from ~/.{{ bot_name }}
    file_name = '~/.{}'.format(bot_name)
    file_path = os.path.expanduser(file_name)
    if not os.path.isfile(file_path):
      logger.info('%s is not found', file_name)
      return None
    try:
      with open(file_path, mode='r') as f:
        return f.read().strip()
    except IOError as e:
      logger.exception(e)

    return None


  def _requests_get_as_json(self, api_path=None):
    """Send get method to api_path and return json data

    Arguments:
        api_path {str} -- api path, fqdn

    Returns:
        dict -- json data, or None
    """
    get_result = None
    try:
      get_result = requests.get(api_path, headers=self.headers, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if get_result is None:
      return None

    if get_result.ok:
      logger.info("get success: %s", api_path)
      return get_result.json()

    logger.error("failed to get: %s", api_path)
    logger.error(get_result.text)

    return None


  def _requests_get_pagination_as_items(self, api_path=None, params=None):
    """Get all items with pagination

    pagination is not tested well.
    see, https://developer.webex.com/docs/api/basics/pagination

    in requests module, 'next' url could be retrieved easily
    response.links['next']['url']

    Arguments:
        api_path {str} -- api path fqdn

    Keyword Arguments:
        params {dict} -- get request params (default: {None})

    Returns:
        list -- a list contains all items
    """
    result_list = []

    get_result = None
    try:
      get_result = requests.get(api_path, headers=self.headers, params=params, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if get_result is None:
      return []

    if not get_result.ok:
      logger.error("failed to get: %s", api_path)
      logger.error(get_result.text)
      return []

    logger.info("get success: %s", api_path)
    items = get_result.json().get('items')
    if items:
      result_list.extend(items)
    else:
      return []

    while 'next' in get_result.links.keys():
      get_result = None
      try:
        get_result = requests.get(api_path, headers=self.headers, params=params, timeout=self.TIMEOUT, verify=False)
      except requests.exceptions.RequestException as e:
        logger.exception(e)

      if get_result is None:
        return []

      if get_result.ok:
        logger.info("get success: %s", api_path)
        items = get_result.json().get('items')
        if items:
          result_list.extend(items)
      else:
        logger.error("failed to get: %s", api_path)
        logger.error(get_result.text)
        return []

    return result_list


  def _requests_delete_as_bool(self, api_path=None):
    """Send delete method to api_path and return True if success

    Arguments:
        api_path {str} -- api path, fqdn

    Returns:
        bool -- True if success
    """
    delete_result = None
    try:
      delete_result = requests.delete(api_path, headers=self.headers, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if delete_result is None:
      return False

    if delete_result.ok:
      logger.info("delete success: %s", api_path)
      return True

    logger.error("failed to delete: %s", api_path)
    logger.error(delete_result.text)
    return False


  def _requests_post_as_json(self, api_path=None, payload=None):
    post_result = None
    try:
      post_result = requests.post(api_path, json=payload, headers=self.headers, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if post_result is None:
      return None

    if post_result.ok:
      logger.info("post success: %s", api_path)
      return post_result.json()

    logger.error("failed to post: %s", api_path)
    logger.error(post_result.text)

    return None


  def get_me(self):
    """Get my own details

    GET /v1/people/me
    https://developer.webex.com/docs/api/v1/people/get-my-own-details

    Returns:
        dict -- information about this bot obtained from rest api, or None
    """
    api_path = 'https://api.ciscospark.com/v1/people/me'
    return self._requests_get_as_json(api_path=api_path)


  def get_bot_id(self):
    """Get a identifier for this bot

    Returns:
        str -- a unique identifier for this bot
    """
    if self._bot_id:
      return self._bot_id
    me = self.get_me()
    if not me:
      return None
    self._bot_id = me.get('id')
    return self._bot_id


  def get_people_by_email(self, email=None):
    """Get people in your organization by email attribute

    GET /v1/people
    https://developer.webex.com/docs/api/v1/people/list-people

    Keyword Arguments:
        email {str} -- get people with this email address (default: {None})

    Returns:
        list -- list of person objects
    """
    if email is None:
      return []

    api_path = 'https://api.ciscospark.com/v1/people'

    params = {
      "email": email
    }

    return self._requests_get_pagination_as_items(api_path=api_path, params=params)


  def get_person_details(self, person_id=None):
    """Get details for a person by person_id

    GET /v1/people/{personId}
    https://developer.webex.com/docs/api/v1/people/get-person-details

    Keyword Arguments:
        person_id {str} -- a unique identifier for the person (default: {None})

    Returns:
        dict -- object for the person, or None
    """
    if person_id is None:
      return None
    api_path = 'https://api.ciscospark.com/v1/people/{}'.format(person_id)
    return self._requests_get_as_json(api_path=api_path)


  def get_rooms(self):
    """Get rooms to which the authenticated user belongs

    GET /v1/rooms
    https://developer.webex.com/docs/api/v1/rooms/list-rooms

    Returns:
        list -- list of the rooms
    """
    api_path = 'https://api.ciscospark.com/v1/rooms'
    return self._requests_get_pagination_as_items(api_path=api_path)


  def get_room_details(self, room_id=None):
    """Get room details

    GET /v1/rooms/{roomId}
    https://developer.webex.com/docs/api/v1/rooms/get-room-details

    Keyword Arguments:
      room_id {str} -- The unique identifier for the room (default: {None})

    Returns:
      dict -- a object for the room
    """
    if room_id is None:
      return None
    api_path = 'https://api.ciscospark.com/v1/rooms/{}'.format(room_id)
    return self._requests_get_as_json(api_path=api_path)


  def delete_room(self, room_id=None):
    """Deletes a room, by ID

    DELETE /v1/rooms/{roomId}
    https://developer.webex.com/docs/api/v1/rooms/delete-a-room

    Keyword Arguments:
        room_id {str} -- The unique identifier for the room. (default: {None})

    Returns:
        bool -- True if success
    """
    if room_id is None:
      return False
    api_path = 'https://api.ciscospark.com/v1/rooms/{}'.format(room_id)
    return self._requests_delete_as_bool(api_path=api_path)


  def get_message_detail(self, message_id=None):
    """Get details for a message, by message_id.

    GET /v1/messages/{messageId}
    https://developer.webex.com/docs/api/v1/messages/get-message-details

    Keyword Arguments:
        message_id {str} -- the unique identifier for the message (default: {None})

    Returns:
        dict -- the object for the message
    """
    if message_id is None:
      return None
    api_path = 'https://api.ciscospark.com/v1/messages/{}'.format(message_id)
    return self._requests_get_as_json(api_path=api_path)


  def get_message_text(self, message_id=None):
    """Same as get_message_detail() but returns text only

    Keyword Arguments:
        message_id {str} -- the unique identifier for the message (default: {None})

    Returns:
        str -- the message text
    """
    json_data = self.get_message_detail(message_id=message_id)
    if json_data is None:
      return None
    return json_data.get('text')


  def send_message(self, text=None, room_id=None, to_person_id=None, to_person_email=None, attachments=None):
    """Create a message

    POST /v1/messages
    https://developer.webex.com/docs/api/v1/messages/create-a-message

    Keyword Arguments:
        text {str} -- The message, in plain text (default: {None})
        room_id {str} -- The room ID of the message (default: {None})
        to_person_id {str} -- The person ID of the recipient when sending a private 1:1 message. (default: {None})
        to_person_email {str} -- The email address of the recipient when sending a private 1:1 message. (default: {None})
        attachments {list} -- Content attachments to attach to the message. (default: {None})

    Returns:
        dict -- post response, or None
    """
    if not any([room_id, to_person_id, to_person_email]):
      return None

    payload = {
      'text': text
    }

    if room_id is not None:
      payload.update({'roomId': room_id})

    if to_person_id is not None:
      payload.update({'toPersonId': to_person_id})

    if to_person_email is not None:
      payload.update({'toPersonEmail': to_person_email})

    if attachments is not None and isinstance(attachments, list):
      payload.update({'attachments': attachments})

    api_path = 'https://api.ciscospark.com/v1/messages/'
    return self._requests_post_as_json(api_path=api_path, payload=payload)


  def get_attachment(self, attachment_id=None):
    """Get attachment action details

    GET /v1/attachment/actions/{id}
    https://developer.webex.com/docs/api/v1/attachment-actions/get-attachment-action-details

    Keyword Arguments:
        attachment_id {str} -- a unique identifier for the attachment action (default: {None})

    Returns:
        dict -- a object for the attachment
    """
    if attachment_id is None:
      return None
    api_path = 'https://api.ciscospark.com/v1/attachment/actions/{}'.format(attachment_id)
    return self._requests_get_as_json(api_path=api_path)


  def get_webhooks(self, webhook_name=None):
    # GET /v1/webhooks
    # https://developer.webex.com/docs/api/v1/webhooks/list-webhooks
    name = webhook_name
    if name is None:
      name = self.bot_name

    api_path = 'https://api.ciscospark.com/v1/webhooks'

    get_result = None
    try:
      get_result = requests.get(api_path, headers=self.headers, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if get_result is None:
      return []

    if get_result.ok:
      data = get_result.json()
      webhooks = data.get('items') if data else []
      if name is None:
        return webhooks
      return list(filter(lambda  x: x.get('name') == name, webhooks))

    logger.error("failed to get: %s", api_path)
    logger.error(get_result.text)
    return []


  def has_webhooks(self, webhook_name=None):
    name = webhook_name
    if name is None:
      name = self.bot_name
    webhooks = self.get_webhooks(name)
    if webhooks is None:
      return False
    if len(webhooks) > 0:
      return True
    return False


  def show_webhooks(self, webhook_name=None):
    name = webhook_name
    if name is None:
      name = self.bot_name
    webhooks = self.get_webhooks(webhook_name=name)
    for w in webhooks:
      print(json.dumps(w, ensure_ascii=False, indent=2))


  def delete_webhook(self, webhook_id=None):
    """Delete webhook by id

    DELETE /v1/webhooks/{webhookId}
    https://developer.webex.com/docs/api/v1/webhooks/delete-a-webhook

    Keyword Arguments:
        webhook_id {str} -- id to be deleted (default: {None})

    Returns:
        bool -- True if successfully deleted
    """
    if not id:
      return False
    api_path = 'https://api.ciscospark.com/v1/webhooks/{}'.format(webhook_id)
    return self._requests_delete_as_bool(api_path=api_path)


  def delete_webhooks(self):
    self.delete_webhooks_by_name(webhook_name=self.bot_name)


  def delete_webhooks_by_name(self, webhook_name=None):
    name = webhook_name
    if name is None:
      name = self.bot_name
    webhooks = self.get_webhooks(webhook_name=name)
    for webhook_id in [w.get('id') for w in webhooks]:
      self.delete_webhook(webhook_id=webhook_id)


  def regist_webhook(self, webhook_name=None, target_url=None):
    # POST /v1/webhooks
    # https://developer.webex.com/docs/api/v1/webhooks/create-a-webhook
    name = webhook_name
    if name is None:
      name = self.bot_name

    # delete same name webhooks, if any
    self.delete_webhooks_by_name(webhook_name=name)

    api_path = 'https://api.ciscospark.com/v1/webhooks'

    payload = {
      'resource': "messages",
      'event': "all",
      'targetUrl': target_url,
      'name': name
    }

    post_result = self._requests_post_as_json(api_path=api_path, payload=payload)
    if post_result is None:
      logger.error('Failed to regist webhook for message')
      return

    logger.info('Success to regist webhook for message')

    # regist one more webhook for attachment

    payload = {
      'resource': "attachmentActions",
      'event': "all",
      'targetUrl': target_url,
      'name': name
    }

    post_result = self._requests_post_as_json(api_path=api_path, payload=payload)
    if post_result is None:
      logger.error('Failed to regist webhook for attachment action')
      return

    logger.info('Success to regist webhook for attachment action')


  def update_webhook(self, webhook_id=None, webhook_name=None, target_url=None):
    # PUT /v1/webhooks/{webhookId}
    # https://developer.webex.com/docs/api/v1/webhooks/update-a-webhook
    api_path = 'https://api.ciscospark.com/v1/webhooks/{}'.format(webhook_id)

    payload = {
      'name': webhook_name,
      'targetUrl': target_url,
      'status': 'active'
    }

    put_result = None
    try:
      put_result = requests.put(api_path, json=payload, headers=self.headers, timeout=self.TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
      logger.exception(e)

    if put_result is None:
      return None

    if put_result.ok:
      logger.info('Webhook update successfuly')
      return put_result.json()

    logger.error("failed to put: %s", api_path)
    logger.error(put_result.text)
    return None


if __name__ == '__main__':

  import argparse

  logging.basicConfig(level=logging.INFO)

  def test_decorator():
    # pylint: disable=unused-variable

    bot = Bot()

    @bot.on_message('hi')
    def on_message_hi(room_id=None):
      print('My room_id is {}'.format(room_id))

    @bot.on_message('*')
    def on_message_default(room_id=None):
      print(room_id)

    # Python起動時にデコレータが付与されている関数は回収されて辞書型に格納される
    # 上の２つの関数は辞書型に格納されているはず
    print(bot.on_message_functions.keys())

    # その辞書型を使えば任意のタイミングでデコレータの付いた関数を実行できる
    message = 'hi'
    if message in bot.on_message_functions:
      func = bot.on_message_functions.get('hi')
      func(room_id="1")
    return 0

  # sys.exit(test_decorator())


  def main():
    parser = argparse.ArgumentParser(description='webex teams bot related operations.')
    parser.add_argument('bot_name', help='name of the bot')
    parser.add_argument('-d', '--delete', action='store_true', default=False, help='Delete all webhooks')
    parser.add_argument('-l', '--list', action='store_true', default=False, help='List all webhooks')
    parser.add_argument('-r', '--room', action='store_true', default=False, help='List rooms')
    parser.add_argument('-m', '--me', action='store_true', default=False, help='show my info')
    args = parser.parse_args()

    bot = Bot(bot_name=args.bot_name)

    if args.list:
      bot.show_webhooks()

    elif args.delete:
      webhooks = bot.get_webhooks()
      for webhook_id in [w.get('id') for w in webhooks]:
        result = bot.delete_webhook(webhook_id=webhook_id)
        if result is not None and result.ok:
          print("{} : {}".format(webhook_id, "successfuly deleted"))
        else:
          print("{} : {}".format(webhook_id, "delete failed"))

    elif args.room:
      rooms = bot.get_rooms()
      print(json.dumps(rooms, ensure_ascii=False, indent=2))

    elif args.me:
      me = bot.get_me()
      print(json.dumps(me, ensure_ascii=False, indent=2))

    return 0

  sys.exit(main())
