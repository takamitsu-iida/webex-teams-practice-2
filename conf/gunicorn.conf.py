"""
gunicorn WSGI server configuration.

example
https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py

"""
# pylint: disable=missing-docstring

from multiprocessing import cpu_count

def max_workers():
  return cpu_count()

# default port number is 8000
bind = '127.0.0.1:5000'

backlog = 1024

max_requests = 1000
worker_class = 'gevent'
workers = max_workers()
