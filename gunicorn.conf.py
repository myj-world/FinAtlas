import os
import multiprocessing

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"

# Prefer the explicit WSGI module when no application argument is supplied.
wsgi_app = "wsgi:application"
