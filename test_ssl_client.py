#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to validate SSL configuration for Gluesync client.
"""

import logging
import sys
import os
import json
from gluesync_sdk.client import GluesyncClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test the Gluesync client SSL configuration"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_ssl_client.py <path_to_security_config.json> [certificate_path]")
        print("If certificate_path is not provided, it will be read from the security config file")
        return 1
    
    security_config_path = sys.argv[1]
    
    # Display the security config parameters
    try:
        with open(security_config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded security config: {json.dumps(config, indent=2)}")
            
            if 'ssl' not in config:
                logger.error("SSL configuration not found in security config file")
                return 1
                
            ssl_config = config['ssl']
            certificate_path = ssl_config.get('sslCertificatePath')
            certificate_password = ssl_config.get('certificatePassword')
            
            logger.info(f"SSL certificate path from config: {certificate_path}")
            logger.info(f"Certificate password from config: {certificate_password}")
            
            # If a certificate path was provided as a command line argument, use it
            if len(sys.argv) > 2:
                certificate_path = sys.argv[2]
                logger.info(f"Overriding certificate path with: {certificate_path}")
                
                # Update the config with the new path
                ssl_config['sslCertificatePath'] = certificate_path
                
                # Save to a temporary config file
                temp_config_path = 'temp-security-config.json'
                with open(temp_config_path, 'w') as temp_f:
                    json.dump(config, temp_f, indent=2)
                
                security_config_path = temp_config_path
                logger.info(f"Created temporary security config with updated certificate path")
    
    except Exception as e:
        logger.error(f"Failed to load or parse security config: {e}")
        return 1
    
    # Try to create a client with SSL enabled using the security config
    try:
        logger.info(f"Creating Gluesync client with security config: {security_config_path}")
        client = GluesyncClient(
            host="localhost",  # Dummy host for testing
            port=1717,         # Default port
            ssl=True,
            security_config=security_config_path
        )
        
        logger.info("SUCCESS: SSL context was created successfully!")
        logger.info(f"Client connection status: {client.connection_status}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to initialize Gluesync client with SSL: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
