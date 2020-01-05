#!/usr/bin/env python
# pylint: disable=missing-docstring

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from distutils.spawn import find_executable

import requests
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

if not here('./lib') in sys.path:
  sys.path.append(here('./lib'))

from botscript import bot

class Ngrok:

  # delay time in sec
  delay = 3

  # Popen object
  popen = None

  # pubilic url
  public_url = None


  def __init__(self, port=5000):
    """constructor for Ngrok class

    Keyword Arguments:
        port {int} -- internal port number (default: {5000})
    """
    self.port = port

    # check if ngrok is installed
    assert find_executable("ngrok"), "ngrok command must be installed, see https://ngrok.com/"

    self.ngrok_cmds = ["ngrok", "http", str(port), "-log=stdout"]

    self.pkill_cmds = ["pkill"]
    self.pkill_cmds.extend(self.ngrok_cmds)


  def pkill(self):
    """kill previous sessions of ngrok (if any)"""
    subprocess.Popen(self.pkill_cmds, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()


  def run_background(self):
    """run ngrok in background, using subprocess.Popen()"""

    # kill same port process, if any
    self.pkill()

    logger.info("start ngrok")

    # spawn ngrok in background
    # subprocess.call("ngrok http 5000 -log=stdout > /dev/null &", shell=True)
    self.popen = subprocess.Popen(self.ngrok_cmds, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Leaving some time to ngrok to open
    time.sleep(self.delay)

    result_code = self.popen.poll()
    if result_code is None:
      logger.info("ngrok is running successfuly")
      return True

    logger.error("ngrok terminated abruptly with code: %s", str(result_code))
    return False


  def get_info(self):
    """get info object from rest api"""
    # use ngrok management api
    api_path = 'http://127.0.0.1:4040/api/tunnels'
    get_result = None
    try:
      get_result = requests.get(api_path)
    except requests.exceptions.RequestException:
      return None

    if get_result and get_result.ok:
      return get_result.json()
    return None


  def get_public_url(self):
    """getter for public_url

    Returns:
        str -- public_url handled by ngrok
    """
    if self.public_url:
      # already exist
      return self.public_url

    data = self.get_info()
    if data is None:
      return None

    self.public_url = data['tunnels'][0]['public_url']

    return self.public_url


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    parser = argparse.ArgumentParser(description='operate ngrok and webhook for webex teams.')
    # webhook
    parser.add_argument('-r', '--regist', action='store_true', default=False, help='Regist webhook')
    parser.add_argument('-d', '--delete', action='store_true', default=False, help='Delete webhook')
    parser.add_argument('-u', '--update', action='store_true', default=False, help='Update disabled webhook')
    # ngrok
    parser.add_argument('-s', '--start', action='store_true', default=False, help='Start ngrok and regist webhook')
    parser.add_argument('-k', '--kill', action='store_true', default=False, help='Kill ngrok process and delete webhook')
    # list
    parser.add_argument('-l', '--list', action='store_true', default=False, help='List ngrok and webhook information')

    args = parser.parse_args()

    result_code = 0

    if args.regist:
      result_code = regist_webhook()
    elif args.delete:
      result_code = delete_webhook()
    elif args.update:
      result_code = update_webhook()
    elif args.start:
      result_code = start()
    elif args.kill:
      result_code = kill()
    elif args.list:
      result_code = list_info()

    return result_code


  def regist_webhook():
    webhook_url = os.environ.get('bot_webhook')
    if webhook_url is None or webhook_url.strip() == '':
      logger.error("failed to read environment variable 'bot_webhook', please set it before run this script")
      return -1

    bot.regist_webhook(target_url=webhook_url)

    return 0

  def delete_webhook():
    bot.delete_webhooks()
    return 0


  def update_webhook():
    webhooks = bot.get_webhooks()
    if not webhooks:
      print("no webhook found.")
      return 0

    for w in webhooks:
      status = w.get('status')
      if status != 'active':
        webhook_id = w.get('id')
        webhook_name = w.get('name')
        target_url = w.get('targetUrl')
        print("disabled webhook found: {}".format(webhook_id))
        bot.update_webhook(webhook_id=webhook_id, webhook_name=webhook_name, target_url=target_url)

    return 0


  def start():
    ngrok = Ngrok()
    ngrok_result = ngrok.run_background()
    if ngrok_result is False:
      logger.error("failed to run ngrok")
      return -1

    # get public_url opened by ngrok
    public_url = ngrok.get_public_url()

    # register webhook with the public url
    bot.regist_webhook(target_url=public_url)

    # show all webhooks
    logger.info("show all webhooks below")
    webhooks = bot.get_webhooks()
    for w in webhooks:
      print(json.dumps(w, ensure_ascii=False, indent=2))

    return 0


  def kill():
    ngrok = Ngrok()
    ngrok.pkill()
    bot.delete_webhooks()
    return 0


  def list_info():
    ngrok = Ngrok()
    info = ngrok.get_info()
    if info:
      print('ngrok is running')
      print(json.dumps(info, ensure_ascii=False, indent=2))
      print('')
    else:
      print('no ngrok found.')

    webhooks = bot.get_webhooks()
    if webhooks:
      print('webhook is registered')
      for w in webhooks:
        print(json.dumps(w, ensure_ascii=False, indent=2))
      print('')
    else:
      print('no webhook found.')

    return 0


  sys.exit(main())
