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

  result = {}
  for path in p.glob('*.py'):
    module_name = Path(path).stem
    if module_name == '__init__':
      continue
    module = load_module(module_name, path)
    if module is None:
      continue
    dir_list = dir(module)
    if 'plugin_main' in dir_list and 'plugin_prop' in dir_list:
      # accept module which has plugin_init() and plugin_prop() function
      result[module_name] = module

  return result


plugin_dir = here('.')

plugin_map = load_plugins(plugin_dir)


if __name__ == '__main__':

  logging.basicConfig(level=logging.INFO)

  def main():
    for key in plugin_map:
      module = plugin_map.get(key)
      prop = module.plugin_prop()
      print('{}: {}'.format(key, prop.get('description')))

    return 0

  sys.exit(main())
