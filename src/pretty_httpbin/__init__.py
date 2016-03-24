__import__("pkg_resources").declare_namespace(__name__)

import sys
import flask
import requests
import traceback
from functools import wraps
from StringIO import StringIO

from httpbin import app
from httpie import core, cli
from httpie.output import streams

from gunicorn import util
from gunicorn.app.wsgiapp import run

from flask_loopback.flask_loopback import httplib, iteritems


class Singleton(object):
    pass


def exception_decorator(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
            raise
    return decorator

@app.after_request
@exception_decorator
def after(response):
    request = flask.request
    open_kwargs = {
        'method': request.method.upper(), 'headers': iteritems(request.headers), 'data': request.data,
        'environ_base': {'REMOTE_ADDR': request.remote_addr},
        'base_url': request.url
    }
    returned = requests.Response()
    returned.url = request.url
    returned.status_code = response.status_code
    returned.reason = httplib.responses.get(response.status_code, None)
    returned.request = request
    returned._content = response.get_data()
    returned.headers.update(response.headers)

    Singleton.response = returned
    Singleton.method = request.method.upper()
    Singleton.url = request.url
    return response


def write_wrapper(func):
    @wraps(func)
    def write(sock, data, chunked=False):
        Singleton.response.raw = StringIO(data)
        env = core.Environment()
        args = cli.parser.parse_args(args=[Singleton.method, Singleton.url, '--print=b'], env=env)
        write_kwargs = {
            'stream': streams.build_output_stream(
            args, env, None, Singleton.response),
            'outfile': sys.stdout,
            'flush': env.stdout_isatty
        }
        streams.write(**write_kwargs)
        return func(sock, data, chunked)
    return write

def main():
    sys.argv = [sys.argv[0], 'pretty_httpbin:app', '--bind', '0.0.0.0:8000']
    util.write = write_wrapper(util.write)
    run()
