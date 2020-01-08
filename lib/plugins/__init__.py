#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import importlib.util
import logging
import os
import sys
from pathlib import Path


logger = logging.getLogger(__name__)

def here(path=''):
  return os.path.abspath(os.path.join(os.path.dirname(__file__), path))


def load_module(module_name, module_path):
  # pylint: disable=broad-except
  try:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
  except Exception as e:
    logger.error("failed to load module: %s", module_name)
    logger.exception(str(e))
  return None


def load_plugins(base_path):
  result_list = []
  p = Path(base_path)
  if not p.exists() or not p.is_dir():
    return result_list

  for path in p.glob('*.py'):
    module_name = Path(path).stem
    if module_name == '__init__':
      continue
    module = load_module(module_name, path)
    if module is None:
      continue
    dir_list = dir(module)
    if 'plugin_props' in dir_list:  # only accept module which has plugin_props()
      result_list.append(module)

  return result_list


def create_plugin_map(module_list):
  result_map = {
    '/': send_help
  }
  for module in module_list:
    props = module.plugin_props()
    for prop in props:
      command = prop.get('command')
      func = prop.get('func')
      result_map[command] = func
  return result_map


def create_help_list(module_list):
  result_list = []
  for module in module_list:
    props = module.plugin_props()
    for prop in props:
      command = prop.get('command')
      descr = prop.get('description')
      result_list.append('\n  '.join([command, descr]) + '\n')
  return result_list


def send_help(bot=None, room_id=None, args=None):
  # pylint: disable=unused-argument
  if not all([bot, room_id]):
    return
  bot.send_message(room_id=room_id, text='\n'.join(_plugin_help_list))

#
#
#

plugin_dir = here('.')

_plugin_list = load_plugins(plugin_dir)
_plugin_help_list = create_help_list(_plugin_list)
_plugin_map = create_plugin_map(_plugin_list)


def get_plugin_map(reload=False):
  """get plugin map, key=commnad, value=function"""
  # pylint: disable=global-statement
  global _plugin_map
  if reload is False:
    return _plugin_map

  global _plugin_list
  global _plugin_help_list
  _plugin_list = load_plugins(plugin_dir)
  _plugin_help_list = create_help_list(_plugin_list)
  _plugin_map = create_plugin_map(_plugin_list)
  return _plugin_map


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    print(_plugin_map)
    return 0

  sys.exit(main())
