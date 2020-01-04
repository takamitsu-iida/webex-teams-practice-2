#!/usr/bin/env python
# pylint: disable=missing-docstring

import logging
import os
import sys
from subprocess import run, Popen, DEVNULL
from time import sleep

import redis

logger = logging.getLogger(__name__)

def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

if not here('./lib') in sys.path:
  sys.path.append(here('./lib'))

# name and directory path of this application
app_name = os.path.splitext(os.path.basename(__file__))[0]
app_home = here('.')
conf_dir = os.path.join(app_home, 'conf')
data_dir = os.path.join(app_home, 'data')

def is_redis_server_running(port=6380):  # use port 6380 in this app, default is 6379
  return run(['redis-cli', '-p', str(port), 'ping'], check=False, stdout=DEVNULL, stderr=DEVNULL).returncode == 0

def shutdown_redis_server(port=6380):
  run(['redis-cli', '-p', str(port), 'shutdown', 'save'], check=False, stdout=DEVNULL, stderr=DEVNULL)

def run_redis_server(config_path):
  if is_redis_server_running() is False:
    proc = Popen(['redis-server', config_path], stdout=DEVNULL, stderr=DEVNULL)
    while is_redis_server_running(port=6380) is not True:
      if proc.poll() is not None:  # redis-server is stopped abrutly
        break
      sleep(0.5)


class RedisTemporaryInstance:

  def __init__(self, port_number=6380):
    self.port_number = port_number
    port = str(port_number)
    cmd_server = "redis-server --port {}".format(port)
    cmd_ping = "redis-cli -p {} ping".format(port)
    cmd_shutdown = "redis-cli -p {} shutdown save".format(port)
    self.cmd_server_list = cmd_server.split()
    self.cmd_ping_list = cmd_ping.split()
    self.cmd_shutdown_list = cmd_shutdown.split()

  def __enter__(self):
    # run redis-server in background
    proc = Popen(self.cmd_server_list, stdout=DEVNULL, stderr=DEVNULL)
    # check if redis-server is ready
    while run(self.cmd_ping_list, check=False, stdout=DEVNULL, stderr=DEVNULL).returncode != 0:
      if proc.poll() is not None:
        break
      sleep(0.5)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    run(self.cmd_shutdown_list, check=False, stdout=DEVNULL, stderr=DEVNULL)


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  redis_port = 6380
  redis_url = os.environ.get('REDIS_URL') if os.environ.get('REDIS_URL') is not None else 'redis://localhost:{}'.format(str(redis_port))

  def main():

    with RedisTemporaryInstance(port_number=redis_port):
      # conn = redis.StrictRedis(host='localhost', port=redis_port, db=redis_index, decode_responses=True)
      conn = redis.StrictRedis.from_url(redis_url, decode_responses=True)

      # キーの一覧を表示
      print(conn.keys(pattern='*'))

      # 値のset, ex=10 で10秒後には消えている
      conn.set('key01', 'value01', ex=10)

      # 値のget
      value = conn.get('key01')

      print(type(value))
      # <class 'bytes'>

      print(str(value, encoding='utf-8'))
      # 'value01'

      # 末尾へ"A", "B", "C"の順で追加
      conn.rpush('key02', 'A')  # 1
      conn.rpush('key02', 'B')  # 2
      conn.rpush('key02', 'C')  # 3

      # 先頭へ"Z"を追加
      conn.lpush('key02', 'Z')  # 4

      # 先頭から2つを参照
      conn.lrange('key02', 0, 1)  # [b'Z', b'A']

      # 先頭から4つを参照
      conn.lrange('key02', 0, 3) # [b'Z', b'A', b'B', b'C']

      # 先頭から1つを取り出す (取り出された"Z"は削除されます)
      conn.lpop('key02')  # b'Z'
      conn.lrange('key02', 0, 2)  # [b'A', b'B', b'C']

      # 末尾から1つを取り出す (取り出された"C"は削除されます)
      conn.rpop('key02')  # b'C'
      conn.lrange('key02', 0, 1)  # [b'A', b'B']

      # ハッシュ型の追加
      conn.hset('rect1', 'width', '10.0')
      conn.hset('rect1', 'height', '15.0')

      # ハッシュ型の参照
      conn.hget('rect1', 'width')  # b'10.0'

      # キーに紐づくすべての値をdict型で返す
      conn.hgetall('rect1')  # {b'width': b'10.0', b'height': b'15.0'}

      # dict型で追加
      conn.hmset('rect2', {'width':'7.5', 'height':'12.5'})
      conn.hgetall('rect2')  # {b'width': b'7.5', b'height': b'12.5'}

    return 0


  sys.exit(main())
