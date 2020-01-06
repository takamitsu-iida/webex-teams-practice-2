#!/usr/bin/env python
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
  p = Path(base_path)
  if not p.exists() or not p.is_dir():
    return {}

  result_list = []
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


def create_map(module_list):
  result_map = {}
  for module in module_list:
    props = module.plugin_props()
    for prop in props:
      command = prop.get('command')
      func = prop.get('func')
      result_map[command] = func
  return result_map


plugin_dir = here('.')

plugin_list = load_plugins(plugin_dir)

plugin_map = create_map(plugin_list)


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    print(plugin_map)

    return 0

  sys.exit(main())
