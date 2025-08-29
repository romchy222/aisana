# Gunicorn configuration for production deployment
# This file optimizes the application for deployment health checks

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Max 4 workers for efficiency
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Application
module = "main:application"

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'bolashak-chat'

# Server mechanics
preload_app = True  # Load application code before workers
daemon = False
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Performance tuning for health checks
graceful_timeout = 30  # Time to wait for workers to finish handling requests
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Bolashak Chat server is ready. Health check endpoint: /health")

def worker_int(worker):
    """Called just after a worker has been killed by a signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker is killed due to timeout."""
    worker.log.info(f"Worker timeout (pid: {worker.pid})")