#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PKCS12 Certificate Test Script

This script tests the Gluesync SDK's ability to load and use PKCS12 certificates.
It demonstrates the various ways to load certificates and handles potential case
sensitivity issues with passwords.
"""

import os
import logging
import json
import argparse
from pathlib import Path

from gluesync_sdk.utils import (
    create_ssl_context_from_jks,
    create_ssl_context_from_pkcs12,
    create_ssl_context_with_cryptography,
    CERT_FORMAT_PKCS12
)
from gluesync_sdk import GluesyncClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PKCS12-Test")


def test_direct_loading(certificate_path, password):
    """Test loading the certificate directly using our utility functions."""
    logger.info(f"Testing direct certificate loading with path: {certificate_path}")
    logger.info(f"Using password: {password}")
    
    # Test with cryptography library
    try:
        logger.info("Testing with cryptography library...")
        ssl_context, format_type = create_ssl_context_with_cryptography(certificate_path, password)
        logger.info(f"✅ SUCCESS: Certificate loaded with cryptography as {format_type}")
    except Exception as e:
        logger.error(f"❌ FAILED: Could not load with cryptography: {e}")
    
    # Test with direct PKCS12 loading
    try:
        logger.info("Testing with direct PKCS12 loading...")
        ssl_context = create_ssl_context_from_pkcs12(certificate_path, password)
        logger.info("✅ SUCCESS: Certificate loaded with PKCS12 method")
    except Exception as e:
        logger.error(f"❌ FAILED: Could not load with PKCS12 method: {e}")
    
    # Test with the universal loader
    try:
        logger.info("Testing with universal certificate loader...")
        ssl_context = create_ssl_context_from_jks(certificate_path, password)
        logger.info("✅ SUCCESS: Certificate loaded with universal loader")
    except Exception as e:
        logger.error(f"❌ FAILED: Could not load with universal loader: {e}")


def test_client_loading(certificate_path, password, config_file=None):
    """Test loading the certificate through the GluesyncClient."""
    logger.info(f"Testing client certificate loading")
    
    if config_file:
        # Test with security config
        try:
            logger.info(f"Testing with security config: {config_file}")
            client = GluesyncClient(
                host="localhost",  # Just for testing, not connecting
                port=1717,
                ssl=True,
                security_config=config_file
            )
            logger.info("✅ SUCCESS: Client created SSL context from security config")
        except Exception as e:
            logger.error(f"❌ FAILED: Client could not create SSL context from security config: {e}")
    else:
        # Test with direct parameters
        try:
            logger.info(f"Testing with direct parameters")
            client = GluesyncClient(
                host="localhost",  # Just for testing, not connecting
                port=1717,
                ssl=True,
                keystore_path=certificate_path,
                keystore_password=password
            )
            logger.info("✅ SUCCESS: Client created SSL context from direct parameters")
        except Exception as e:
            logger.error(f"❌ FAILED: Client could not create SSL context from direct parameters: {e}")


def test_case_sensitivity(certificate_path, password):
    """Test password case sensitivity handling."""
    logger.info(f"Testing password case sensitivity handling")
    
    # Test original password
    logger.info(f"Testing with original password: {password}")
    try:
        ssl_context, format_type = create_ssl_context_with_cryptography(certificate_path, password)
        logger.info(f"✅ SUCCESS: Certificate loaded with original password: {password}")
    except Exception as e:
        logger.error(f"❌ FAILED: Could not load with original password: {e}")
    
    # Test lowercase password if original has uppercase
    if any(c.isupper() for c in password):
        lowercase_password = password.lower()
        logger.info(f"Testing with lowercase password: {lowercase_password}")
        try:
            ssl_context, format_type = create_ssl_context_with_cryptography(certificate_path, lowercase_password)
            logger.info(f"✅ SUCCESS: Certificate loaded with lowercase password: {lowercase_password}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not load with lowercase password: {e}")
    
    # Test uppercase password if original has lowercase
    if any(c.islower() for c in password):
        uppercase_password = password.upper()
        logger.info(f"Testing with uppercase password: {uppercase_password}")
        try:
            ssl_context, format_type = create_ssl_context_with_cryptography(certificate_path, uppercase_password)
            logger.info(f"✅ SUCCESS: Certificate loaded with uppercase password: {uppercase_password}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not load with uppercase password: {e}")


def create_test_config(certificate_path, password, output_file):
    """Create a test security config file."""
    config = {
        "ssl": {
            "sslCertificatePath": certificate_path,
            "certificateAlias": "gluesync",
            "certificatePassword": password,
            "certificateKeyPassword": password
        },
        "dh": {
            "diffieHellmanPassword": "Gluesync-password",
            "salt": "Gluesync-salt"
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created test config at: {output_file}")
    return output_file


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test PKCS12 certificate loading")
    parser.add_argument("--cert", help="Path to certificate file")
    parser.add_argument("--password", help="Certificate password")
    parser.add_argument("--config", help="Path to security config file (optional)")
    
    args = parser.parse_args()
    
    # Use provided values or defaults
    certificate_path = args.cert or "/Users/danieleangeli/Documents/Repositories/gluesync-python-corehub-handshake-sdk/gluesync.com.jks"
    password = args.password or "gluesync"
    config_file = args.config
    
    logger.info("=" * 50)
    logger.info("PKCS12 Certificate Testing")
    logger.info("=" * 50)
    logger.info(f"Certificate path: {certificate_path}")
    logger.info(f"Certificate exists: {os.path.exists(certificate_path)}")
    
    # Create a test config file if not provided
    if not config_file:
        config_file = "test-security-config.json"
        create_test_config(certificate_path, password, config_file)
    
    # Run the tests
    logger.info("\n" + "=" * 50)
    logger.info("Test 1: Direct Certificate Loading")
    logger.info("=" * 50)
    test_direct_loading(certificate_path, password)
    
    logger.info("\n" + "=" * 50)
    logger.info("Test 2: Client Certificate Loading")
    logger.info("=" * 50)
    test_client_loading(certificate_path, password, config_file)
    
    logger.info("\n" + "=" * 50)
    logger.info("Test 3: Password Case Sensitivity")
    logger.info("=" * 50)
    test_case_sensitivity(certificate_path, password)
    
    logger.info("\n" + "=" * 50)
    logger.info("All tests completed")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
