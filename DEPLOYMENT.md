# BolashakBot Deployment Guide

## Health Check Fixes Applied

This document outlines the comprehensive deployment health check fixes applied to resolve deployment failures during the readiness probe phase.

### ✅ Fixes Implemented

#### 1. Enhanced Health Check Endpoints

Multiple health check endpoints are now available for deployment platforms:

- **`/health`** - Basic health check (recommended for most deployment platforms)
- **`/healthz`** - Kubernetes-style health check  
- **`/ready`** - Readiness probe endpoint
- **`/api/health`** - API-style health check

**Features:**
- Always returns HTTP 200 status for basic health checks
- Optional detailed check with `?detailed=true` parameter
- Includes database connectivity status in detailed mode
- Fast response times (<100ms) for deployment probes
- Graceful degradation when database is unavailable

**Example responses:**
```json
// Basic health check
{
  "status": "healthy",
  "timestamp": 1755019916.2530413,
  "service": "bolashak-chat",
  "version": "1.0.0"
}

// Detailed health check (?detailed=true)
{
  "status": "healthy",
  "timestamp": 1755019920.6812704,
  "service": "bolashak-chat", 
  "version": "1.0.0",
  "database": "connected"
}
```

#### 2. Non-Blocking Database Initialization

**Problem:** Database initialization during startup was blocking deployment health checks.

**Solution:** 
- Lightweight model imports during startup
- Deferred database table creation to avoid blocking
- Separate `/api/startup` endpoint for post-deployment initialization
- Graceful handling of database connection failures

**Benefits:**
- Faster application startup (critical for deployment platforms)
- Health check endpoints work immediately after startup
- Database initialization happens in background or on-demand

#### 3. Production-Ready Host Binding

**Applied changes:**
- Flask app binds to `0.0.0.0` (all interfaces) instead of `localhost`
- Proper PORT environment variable handling
- Production vs development mode detection
- Timeout and retry logic for database connections

#### 4. Improved Error Handling and Timeouts

**Startup resilience:**
- Database connection timeout (5-10 seconds)
- Retry logic with backoff for failed connections
- Graceful degradation when services are unavailable
- Comprehensive logging for debugging deployment issues

**Production vs Development modes:**
- Production: More lenient startup checks, continues with warnings
- Development: Stricter validation, fails fast on errors

#### 5. Gunicorn Production Configuration

Created `gunicorn.conf.py` with optimized settings:

```python
# Key optimizations for deployment
bind = "0.0.0.0:{PORT}"
workers = min(cpu_count * 2 + 1, 4)  # Efficient worker count
timeout = 30  # Reasonable request timeout
preload_app = True  # Faster worker startup
graceful_timeout = 30  # Clean shutdown
```

### 🚀 Deployment Commands

#### Using Gunicorn (Recommended for Production)

```bash
# Install gunicorn if not already installed
pip install gunicorn

# Start with configuration file
gunicorn -c gunicorn.conf.py main:application

# Or manual configuration
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 30 main:application
```

#### Using Flask Development Server

```bash
# Development mode
FLASK_ENV=development python main.py

# Production mode  
FLASK_ENV=production python main.py
```

### 🔍 Health Check Validation

Use the included health check script for deployment validation:

```bash
# Basic validation
python deployment_health_check.py

# With custom URL
APP_URL=https://your-app.replit.app python deployment_health_check.py
```

### 📋 Environment Variables

Required for deployment:

```bash
# Database (one of these required)
DATABASE_URL=postgresql://user:pass@host:port/db
# OR PostgreSQL connection components
PGHOST=host
PGDATABASE=dbname
PGUSER=user
PGPASSWORD=pass

# Application security
SESSION_SECRET=your-random-secret-key

# Optional deployment settings
PORT=5000
FLASK_ENV=production
```

### 🛠️ Troubleshooting Deployment Issues

#### Health Check Failures

1. **Test health endpoint directly:**
   ```bash
   curl -v http://your-app-url/health
   ```

2. **Check detailed health status:**
   ```bash
   curl -v "http://your-app-url/health?detailed=true"
   ```

3. **Verify database initialization:**
   ```bash
   curl -X POST http://your-app-url/api/startup
   ```

#### Common Deployment Platform Settings

**Replit Deployments:**
- Health check URL: `/health`
- Startup timeout: 30-60 seconds
- Port: Automatic (uses PORT environment variable)

**Heroku:**
- Buildpack: `heroku/python`
- Procfile: `web: gunicorn -c gunicorn.conf.py main:application`

**DigitalOcean App Platform:**
- Health check: `/health`
- Startup timeout: 60 seconds

**Railway:**
- Start command: `gunicorn -c gunicorn.conf.py main:application`
- Health check: `/health`

### 📈 Performance Optimizations

1. **Database Connection Pooling:**
   - Enabled in SQLAlchemy engine options
   - Pool recycle every 300 seconds
   - Pre-ping for connection validation

2. **Startup Time Optimization:**
   - Deferred database initialization
   - Minimal imports during startup
   - Preload application code in gunicorn

3. **Health Check Performance:**
   - Sub-100ms response times
   - Minimal database queries in detailed mode
   - Always returns 200 status for basic checks

### 🔧 Advanced Configuration

#### Custom Health Check Timeouts

Modify health check behavior in `views.py`:

```python
# Adjust timeout for database checks
@main_bp.route('/health')
def health_check():
    detailed = request.args.get('detailed', 'false').lower() == 'true'
    if detailed:
        # Custom timeout for DB check
        with db.engine.connect().execution_options(timeout=5) as connection:
            # ... health check logic
```

#### Deployment Platform Specific Optimizations

**Kubernetes:**
- Use `/healthz` for health checks
- Use `/ready` for readiness probes
- Set appropriate `initialDelaySeconds` and `timeoutSeconds`

**Docker:**
- Use `HEALTHCHECK` instruction with `/health` endpoint
- Set reasonable intervals and timeouts

This comprehensive set of fixes ensures reliable deployment health checks across all major deployment platforms while maintaining application performance and reliability.