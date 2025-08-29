#!/usr/bin/env python3
"""
Startup script for BolashakChat deployment
This script validates the environment and starts the application safely
"""

import os
import sys
import logging
from typing import Dict, Any

def setup_logging():
    """Configure logging for production deployment"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_environment() -> Dict[str, Any]:
    """
    Validate all required environment variables for deployment
    Returns a dictionary with validation results
    """
    validation_results = {
        'success': True,
        'errors': [],
        'warnings': []
    }
    
    # Critical environment variables
    critical_vars = {
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
        'SESSION_SECRET': os.environ.get('SESSION_SECRET')
    }
    
    # Check DATABASE_URL or PostgreSQL components
    if not critical_vars['DATABASE_URL']:
        # Check for Replit PostgreSQL environment variables
        pg_vars = {
            'PGHOST': os.environ.get('PGHOST'),
            'PGDATABASE': os.environ.get('PGDATABASE'),
            'PGUSER': os.environ.get('PGUSER'),
            'PGPASSWORD': os.environ.get('PGPASSWORD'),
            'PGPORT': os.environ.get('PGPORT')
        }
        
        missing_pg = [k for k, v in pg_vars.items() if not v]
        if missing_pg:
            validation_results['errors'].append(
                f"Missing DATABASE_URL and PostgreSQL variables: {', '.join(missing_pg)}"
            )
            validation_results['success'] = False
        else:
            validation_results['warnings'].append("Using PostgreSQL environment variables instead of DATABASE_URL")
    
    # Check SESSION_SECRET
    if not critical_vars['SESSION_SECRET']:
        if os.environ.get('FLASK_ENV') == 'production':
            validation_results['errors'].append("SESSION_SECRET is required for production deployment")
            validation_results['success'] = False
        else:
            validation_results['warnings'].append("SESSION_SECRET not set, will use development fallback")
    
    # Optional but recommended variables
    optional_vars = {
        'MISTRAL_API_KEY': os.environ.get('MISTRAL_API_KEY'),
        'FLASK_ENV': os.environ.get('FLASK_ENV', 'production')
    }
    
    if not optional_vars['MISTRAL_API_KEY']:
        validation_results['warnings'].append("MISTRAL_API_KEY not set, AI features may not work")
    
    return validation_results

def test_database_connection():
    """Test database connection before starting the application"""
    try:
        # Import here to avoid circular imports
        from app import app
        from models import db
        from sqlalchemy import text
        
        with app.app_context():
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if not row or row[0] != 1:
                    raise ValueError("Database test query returned unexpected result")
                
        logging.info("Database connection test passed")
        return True
        
    except Exception as e:
        logging.error(f"Database connection test failed: {e}")
        return False

def main():
    """Main startup function"""
    setup_logging()
    
    logging.info("Starting BolashakChat application deployment validation")
    
    # Validate environment
    validation = validate_environment()
    
    # Log warnings
    for warning in validation['warnings']:
        logging.warning(warning)
    
    # Handle errors
    if not validation['success']:
        logging.error("Environment validation failed:")
        for error in validation['errors']:
            logging.error(f"  - {error}")
        
        print("\n" + "="*50)
        print("DEPLOYMENT CONFIGURATION ERROR")
        print("="*50)
        print("\nThe following issues must be resolved before deployment:")
        for error in validation['errors']:
            print(f"❌ {error}")
        
        if validation['warnings']:
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"⚠️  {warning}")
        
        print("\nTo fix these issues:")
        print("1. Set required environment variables in the Deployments pane")
        print("2. Ensure PostgreSQL database is properly configured")
        print("3. Add SESSION_SECRET for secure sessions")
        print("\nRefer to the deployment documentation for more details.")
        print("="*50)
        
        sys.exit(1)
    
    # Test database connection
    if not test_database_connection():
        logging.error("Database connection test failed - deployment cannot proceed")
        sys.exit(1)
    
    logging.info("All validation checks passed - application ready for deployment")
    
    # Import and return the app
    from app import app
    return app

if __name__ == '__main__':
    app = main()
    # Start the application if run directly
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)