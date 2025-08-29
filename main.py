import os
import sys
import logging
import time
from app import app

# Set up logging for production deployment
if __name__ != '__main__':
    # Production logging configuration for gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Export app for gunicorn
# This is what gunicorn will import: main:app
application = app

def check_required_environment():
    """Check if all required environment variables are set"""
    required_vars = []
    
    # Check for database configuration
    if not os.environ.get("DATABASE_URL"):
        # Check if PostgreSQL variables are available (from Replit)
        if not (os.environ.get("PGHOST") and os.environ.get("PGDATABASE")):
            required_vars.append("DATABASE_URL or PostgreSQL connection variables")
    
    # Check for session secret
    if not os.environ.get("SESSION_SECRET"):
        app.logger.warning("SESSION_SECRET not set, using development fallback")
    
    if required_vars:
        error_msg = f"Missing required environment variables: {', '.join(required_vars)}"
        app.logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    return True

def verify_database_connection(timeout=10):
    """Verify database connection is working with timeout"""
    try:
        with app.app_context():
            from models import db
            from sqlalchemy import text
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Database connection timeout after {timeout} seconds")
            
            # Set up timeout for database connection
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            
            try:
                # Test database connection using SQLAlchemy 2.0 syntax
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                signal.alarm(0)  # Cancel alarm
                app.logger.info("Database connection verified successfully")
                return True
            finally:
                signal.signal(signal.SIGALRM, old_handler)
                
    except TimeoutError as e:
        app.logger.warning(f"Database connection timeout: {e}")
        return False
    except Exception as e:
        app.logger.warning(f"Database connection failed: {e}")
        return False

def startup_checks_with_retry(max_retries=3):
    """Perform startup checks with retry logic"""
    for attempt in range(max_retries):
        try:
            # Check environment variables
            check_required_environment()
            
            # Verify database connection with timeout
            if not verify_database_connection(timeout=5):
                if attempt < max_retries - 1:
                    app.logger.warning(f"Database connection failed, retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                else:
                    app.logger.warning("Database connection failed after all retries, starting without DB")
                    break
            else:
                app.logger.info("All startup checks passed successfully")
                break
                
        except Exception as e:
            if attempt < max_retries - 1:
                app.logger.warning(f"Startup check failed: {e}, retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            else:
                app.logger.error(f"Startup checks failed after all retries: {e}")
                raise

if __name__ == '__main__':
    try:
        # Production vs Development detection
        is_production = os.environ.get('FLASK_ENV') != 'development'
        
        if is_production:
            # In production, be more lenient with startup checks
            app.logger.info("Production mode: performing lightweight startup checks")
            try:
                startup_checks_with_retry(max_retries=2)
            except Exception as e:
                app.logger.warning(f"Some startup checks failed, but continuing in production mode: {e}")
        else:
            # In development, be stricter
            app.logger.info("Development mode: performing full startup checks")
            startup_checks_with_retry(max_retries=3)
        
        # Start server with proper host binding
        port = int(os.environ.get('PORT', 5000))
        host = '0.0.0.0'  # Important for deployment - bind to all interfaces
        
        if is_production:
            app.logger.info(f"Starting production server on {host}:{port}")
            # Note: In production, this will typically be overridden by gunicorn
            app.run(host=host, port=port, debug=False)
        else:
            app.logger.info(f"Starting development server on {host}:{port}")
            app.run(host=host, port=port, debug=True)
        
    except Exception as e:
        app.logger.error(f"Failed to start application: {e}")
        # In production, don't exit immediately - let the deployment handle restart
        if os.environ.get('FLASK_ENV') == 'development':
            sys.exit(1)
        else:
            app.logger.warning("Application failed to start completely, but health check endpoints should still work")
