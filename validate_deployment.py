#!/usr/bin/env python3
"""
Comprehensive deployment validation script for BolashakChat
Run this script before deploying to catch configuration issues early
"""

import os
import sys
import logging
from typing import List, Tuple

def setup_basic_logging():
    """Setup basic logging for validation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

def check_imports() -> Tuple[bool, List[str]]:
    """Check if all critical imports work"""
    errors = []
    
    try:
        from main import application
        if not hasattr(application, 'run'):
            errors.append("main:application is not a valid Flask app")
    except Exception as e:
        errors.append(f"Failed to import main:application - {e}")
    
    try:
        from app import create_app
    except Exception as e:
        errors.append(f"Failed to import create_app from app - {e}")
    
    try:
        from models import db
    except Exception as e:
        errors.append(f"Failed to import database models - {e}")
    
    try:
        from config import DatabaseConfig
    except Exception as e:
        errors.append(f"Failed to import DatabaseConfig - {e}")
    
    return len(errors) == 0, errors

def check_environment() -> Tuple[bool, List[str], List[str]]:
    """Check environment variables"""
    errors = []
    warnings = []
    
    # Check database configuration
    database_url = os.environ.get('DATABASE_URL')
    pg_vars = {
        'PGHOST': os.environ.get('PGHOST'),
        'PGDATABASE': os.environ.get('PGDATABASE'),
        'PGUSER': os.environ.get('PGUSER'),
        'PGPASSWORD': os.environ.get('PGPASSWORD'),
        'PGPORT': os.environ.get('PGPORT')
    }
    
    if not database_url:
        missing_pg = [k for k, v in pg_vars.items() if not v]
        if missing_pg:
            errors.append(f"Missing database configuration: {', '.join(missing_pg)}")
        else:
            warnings.append("Using PostgreSQL environment variables (OK for Replit)")
    
    # Check session secret
    if not os.environ.get('SESSION_SECRET'):
        if os.environ.get('FLASK_ENV') == 'production':
            errors.append("SESSION_SECRET required for production")
        else:
            warnings.append("SESSION_SECRET not set (will use development fallback)")
    
    # Check optional variables
    if not os.environ.get('MISTRAL_API_KEY'):
        warnings.append("MISTRAL_API_KEY not set (AI features disabled)")
    
    return len(errors) == 0, errors, warnings

def check_database_connection() -> Tuple[bool, str]:
    """Test database connection"""
    try:
        from app import create_app
        from models import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                row = result.fetchone()
                if not row or row[0] != 1:
                    return False, "Database test query failed"
        
        return True, "Database connection successful"
        
    except Exception as e:
        return False, f"Database connection failed: {e}"

def check_gunicorn_compatibility() -> Tuple[bool, str]:
    """Check if gunicorn can load the application"""
    try:
        import subprocess
        result = subprocess.run([
            'python', '-c', 
            'import main; print("Gunicorn compatibility: OK")'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, "Gunicorn compatibility verified"
        else:
            return False, f"Gunicorn compatibility check failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Gunicorn compatibility check error: {e}"

def main():
    """Main validation function"""
    setup_basic_logging()
    
    print("="*60)
    print("BolashakChat Deployment Validation")
    print("="*60)
    
    all_passed = True
    
    # Check imports
    print("\n1. Checking Python imports...")
    imports_ok, import_errors = check_imports()
    if imports_ok:
        print("   ✓ All imports successful")
    else:
        print("   ✗ Import errors found:")
        for error in import_errors:
            print(f"     - {error}")
        all_passed = False
    
    # Check environment
    print("\n2. Checking environment variables...")
    env_ok, env_errors, env_warnings = check_environment()
    if env_ok:
        print("   ✓ Environment configuration valid")
        if env_warnings:
            for warning in env_warnings:
                print(f"   ⚠  {warning}")
    else:
        print("   ✗ Environment errors found:")
        for error in env_errors:
            print(f"     - {error}")
        all_passed = False
    
    # Check database
    print("\n3. Testing database connection...")
    if imports_ok:  # Only test if imports work
        db_ok, db_message = check_database_connection()
        if db_ok:
            print(f"   ✓ {db_message}")
        else:
            print(f"   ✗ {db_message}")
            all_passed = False
    else:
        print("   ⏸ Skipped (import errors)")
    
    # Check gunicorn compatibility
    print("\n4. Checking Gunicorn compatibility...")
    if imports_ok:
        gunicorn_ok, gunicorn_message = check_gunicorn_compatibility()
        if gunicorn_ok:
            print(f"   ✓ {gunicorn_message}")
        else:
            print(f"   ✗ {gunicorn_message}")
            all_passed = False
    else:
        print("   ⏸ Skipped (import errors)")
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("🎉 VALIDATION PASSED - Ready for deployment!")
        print("\nNext steps:")
        print("1. Set required secrets in Replit Deployments pane")
        print("2. Click Deploy to start your application")
    else:
        print("❌ VALIDATION FAILED - Fix issues before deployment")
        print("\nReview the errors above and:")
        print("1. Fix any import or configuration issues")
        print("2. Set missing environment variables")
        print("3. Run this validation script again")
    
    print("="*60)
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())