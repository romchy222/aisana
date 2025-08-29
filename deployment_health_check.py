#!/usr/bin/env python3
"""
Deployment health check script for BolashakBot
This script can be used by deployment platforms to verify application readiness
"""

import os
import sys
import time
import requests
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_health_endpoint(base_url, timeout=30, max_retries=5):
    """Check if the health endpoint is responding"""
    health_url = urljoin(base_url, '/health')
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Health check attempt {attempt + 1}/{max_retries}: {health_url}")
            response = requests.get(health_url, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Health check passed: {data}")
                return True
            else:
                logger.warning(f"Health check failed with status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Health check attempt {attempt + 1} failed: {e}")
            
        if attempt < max_retries - 1:
            logger.info(f"Waiting 5 seconds before retry...")
            time.sleep(5)
    
    return False

def check_detailed_health(base_url, timeout=10):
    """Check detailed health endpoint with database status"""
    try:
        health_url = urljoin(base_url, '/health?detailed=true')
        response = requests.get(health_url, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Detailed health check: {data}")
            
            # Check if database is connected
            if data.get('database') == 'connected':
                logger.info("Database connection verified")
            else:
                logger.warning("Database connection not available")
                
            return True
        else:
            logger.warning(f"Detailed health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"Detailed health check failed: {e}")
        return False

def main():
    """Main health check function"""
    # Get base URL from environment or use default
    base_url = os.environ.get('APP_URL', 'http://localhost:5000')
    
    logger.info(f"Starting health check for: {base_url}")
    
    # Basic health check
    if not check_health_endpoint(base_url):
        logger.error("Basic health check failed")
        sys.exit(1)
    
    # Detailed health check (optional)
    if not check_detailed_health(base_url):
        logger.warning("Detailed health check failed, but basic health is OK")
    
    logger.info("All health checks passed successfully")
    sys.exit(0)

if __name__ == '__main__':
    main()