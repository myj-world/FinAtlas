"""WSGI entrypoint for Gunicorn.

Gunicorn is invoked as:
    gunicorn -c gunicorn.conf.py wsgi:application
"""

from app import create_app

application = create_app()
