"""Gunicorn configuration file for production deployment."""
import os
import multiprocessing

# Basic server configuration
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'  # Use 'gevent' or 'eventlet' for async workers
worker_connections = 1000
timeout = 60
keepalive = 5

# Logging configuration
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')  # '-' for stdout
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')  # '-' for stderr
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Process management
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server mechanics
preload_app = True  # Load application code before the worker processes are forked
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 100  # Add jitter to max_requests to prevent all workers from restarting simultaneously

# SSL Configuration
# Comment these out if SSL is handled by a reverse proxy like Nginx
# keyfile = '/path/to/ssl/key.pem'
# certfile = '/path/to/ssl/cert.pem'
# ca_certs = '/path/to/ca/cert.pem'

# Server hooks
def on_starting(server):
    """Server starting hook."""
    print("Gunicorn server is starting...")

def on_reload(server):
    """Server reload hook."""
    print("Gunicorn server reloading...")

def post_fork(server, worker):
    """Post fork hook."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_int(worker):
    """Worker interrupted hook."""
    worker.log.info(f"Worker interrupted (pid: {worker.pid})")

def worker_abort(worker):
    """Worker aborted hook."""
    worker.log.info(f"Worker aborted (pid: {worker.pid})")

def worker_exit(server, worker):
    """Worker exit hook."""
    server.log.info(f"Worker exited (pid: {worker.pid})")

def pre_exec(server):
    """Pre-exec hook."""
    server.log.info("Forked child, re-executing.")

def pre_request(worker, req):
    """Pre-request hook."""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Post-request hook."""
    worker.log.debug(f"{req.method} {req.path} {resp.status}")

def child_exit(server, worker):
    """Child exit hook."""
    server.log.info(f"Worker exited (pid: {worker.pid})")

def nworkers_changed(server, new_value, old_value):
    """nworkers changed hook."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Server exit hook."""
    server.log.info("Gunicorn server is shutting down...")