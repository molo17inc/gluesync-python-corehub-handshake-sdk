#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This file is part of Gluesync Scheduler Module.

Gluesync Scheduler Module is dual-licensed under the following licenses:

1. GNU General Public License (GPL) Version 3
   You may use, modify, and distribute this software under the terms of the GPL v3.
   See the LICENSE-GPL file or <http://www.gnu.org/licenses/gpl-3.0.html> for details.
   This option is available at no cost, but any derivative works must also be licensed under GPL v3.

2. MOLO17 Commercial License
   Alternatively, you may use this software under the MOLO17 Commercial License,
   which includes a warranty and permits proprietary use. Contact MOLO17 at info@molo17.com
   for licensing terms and conditions.

You must choose one of these licenses to use this software. Using this software implies
acceptance of one of these licenses. See the accompanying LICENSE files or contact
MOLO17 for more information.

Copyright (C) 2025 MOLO17. All rights reserved.
"""

import os
import ssl
import jks
import tempfile
import logging
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Import cryptography libraries
try:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    logger.warning("Cryptography library not available. Some certificate formats may not be supported.")
    CRYPTOGRAPHY_AVAILABLE = False
    
# Constants for certificate formats
CERT_FORMAT_PKCS12 = "PKCS12"
CERT_FORMAT_JKS = "JKS"
CERT_FORMAT_PEM = "PEM"
CERT_FORMAT_DER = "DER"


def create_ssl_context_with_cryptography(keystore_path: str, keystore_password: str = None) -> tuple[ssl.SSLContext, str]:
    """
    Create an SSL context using the cryptography library, which can handle various certificate formats.
    
    Args:
        keystore_path: Path to the certificate file
        keystore_password: Password for the certificate file (if needed)
        
    Returns:
        Tuple containing (SSL context, detected format)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The cryptography library is required for this function.")
        
    logger.info(f"Attempting to create SSL context using cryptography from: {keystore_path}")
    
    # Check if file exists
    if not os.path.exists(keystore_path):
        raise FileNotFoundError(f"Certificate file not found: {keystore_path}")
        
    # Read the file
    with open(keystore_path, 'rb') as f:
        data = f.read()
    
    # Create temp files for the certificate and key
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
    
    success = False
    error = None
    
    try:
        # Try as PKCS12 first - this is the most common for JKS-named files from Java
        try:
            logger.info("Attempting to load as PKCS12...")
            # Try both with the provided password and lowercase version
            passwords_to_try = [keystore_password]
            
            # If the password is capitalized, add a lowercase version to try
            if keystore_password and any(c.isupper() for c in keystore_password):
                passwords_to_try.append(keystore_password.lower())
                
            last_error = None
            for pwd_attempt in passwords_to_try:
                try:
                    pwd_bytes = pwd_attempt.encode() if pwd_attempt else None
                    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                        data, pwd_bytes, default_backend()
                    )
                    
                    # If we got here, the password worked
                    logger.info(f"Successfully loaded PKCS12 with password: {pwd_attempt}")
                    
                    # Write the certificate in PEM format
                    if certificate:
                        cert_pem = certificate.public_bytes(encoding=serialization.Encoding.PEM)
                        cert_file.write(cert_pem)
                        
                        # Write the private key in PEM format if available
                        if private_key:
                            key_pem = private_key.private_bytes(
                                encoding=serialization.Encoding.PEM,
                                format=serialization.PrivateFormat.PKCS8,
                                encryption_algorithm=serialization.NoEncryption()
                            )
                            key_file.write(key_pem)
                        
                        cert_file.close()
                        key_file.close()
                        
                        # Create and configure the SSL context
                        context = ssl.create_default_context()
                        
                        if private_key:
                            context.load_cert_chain(cert_file.name, key_file.name)
                        else:
                            context.load_cert_chain(cert_file.name)
                            
                        context.check_hostname = True
                        context.verify_mode = ssl.CERT_REQUIRED
                        
                        logger.info("Successfully created SSL context from PKCS12 certificate")
                        success = True
                        return context, CERT_FORMAT_PKCS12
                except Exception as e:
                    last_error = e
                    continue
                    
            if last_error:
                error = f"PKCS12 loading failed: {last_error}"
                logger.warning(error)
            
        except Exception as e:
            error = f"PKCS12 loading failed: {e}"
            logger.warning(error)
        
        # Try as other formats only if PKCS12 fails
        # Try as DER certificate
        try:
            logger.info("Attempting to load as DER certificate...")
            cert = x509.load_der_x509_certificate(data, default_backend())
            
            # Convert to PEM for SSL context
            pem_data = cert.public_bytes(encoding=serialization.Encoding.PEM)
            cert_file.write(pem_data)
            cert_file.close()
            
            # Create and configure the SSL context
            context = ssl.create_default_context()
            context.load_verify_locations(cafile=cert_file.name)
            
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            logger.info("Successfully created SSL context from DER certificate")
            success = True
            return context, CERT_FORMAT_DER
        except Exception as e:
            if error:
                error += f"; DER loading failed: {e}"
            else:
                error = f"DER loading failed: {e}"
            logger.warning(f"DER loading failed: {e}")
        
        # Try as PEM certificate
        try:
            logger.info("Attempting to load as PEM certificate...")
            cert = x509.load_pem_x509_certificate(data, default_backend())
            
            # The data is already PEM, so we can use it directly
            with open(cert_file.name, 'wb') as f:
                f.write(data)
            
            # Create and configure the SSL context
            context = ssl.create_default_context()
            context.load_verify_locations(cafile=cert_file.name)
            
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            logger.info("Successfully created SSL context from PEM certificate")
            success = True
            return context, CERT_FORMAT_PEM
        except Exception as e:
            if error:
                error += f"; PEM loading failed: {e}"
            else:
                error = f"PEM loading failed: {e}"
            logger.warning(f"PEM loading failed: {e}")
        
        # If we got here, all methods failed
        if not success:
            raise Exception(f"Failed to create SSL context: {error}")
            
    except Exception as e:
        logger.error(f"Failed to create SSL context with cryptography: {e}")
        raise
    finally:
        # Clean up temporary files
        if not success:
            try:
                os.unlink(cert_file.name)
                os.unlink(key_file.name)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary files: {cleanup_error}")


def create_ssl_context_from_pkcs12(keystore_path: str, keystore_password: str) -> ssl.SSLContext:
    """
    Create an SSL context from a PKCS12 certificate file.
    
    Args:
        keystore_path: Path to the PKCS12 file (.p12 or .pfx)
        keystore_password: Password for the PKCS12 file
        
    Returns:
        SSL context configured with the certificates from the PKCS12 file
    """
    # Create a default SSL context
    context = ssl.create_default_context()
    
    try:
        # Load the PKCS12 certificate directly
        context.load_cert_chain(
            keystore_path,
            password=keystore_password
        )
        
        # Configure SSL settings
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        logger.info(f"SSL context created successfully from PKCS12 file: {keystore_path}")
        return context
    except Exception as e:
        logger.error(f"Failed to create SSL context from PKCS12: {e}")
        raise


def create_ssl_context_from_jks(keystore_path: str, keystore_password: str, alias: str = None, key_password: str = None) -> ssl.SSLContext:
    """
    Create an SSL context from a certificate file.
    This function will intelligently detect and handle multiple certificate formats:
    1. PKCS12 format (often used in Java environments)
    2. JKS format (Java KeyStore)
    3. PEM format (common in many environments)
    4. DER format (binary certificate format)
    
    Args:
        keystore_path: Path to the certificate file
        keystore_password: Password for the certificate file
        alias: Optional alias for the certificate in the keystore
        key_password: Optional password for the certificate key
        
    Returns:
        SSL context configured with the certificates from the keystore file
    """
    exceptions = []
    logger.info(f"Creating SSL context from keystore: {keystore_path}")
    
    # Check if the file exists
    if not os.path.exists(keystore_path):
        raise FileNotFoundError(f"Certificate file not found: {keystore_path}")
    
    # Try lowercase password if the original has any uppercase letters
    passwords_to_try = [keystore_password]
    if keystore_password and any(c.isupper() for c in keystore_password):
        passwords_to_try.append(keystore_password.lower())
        logger.info(f"Will also try lowercase password: {keystore_password.lower()}")
    
    # First try using the cryptography library (most flexible)
    if CRYPTOGRAPHY_AVAILABLE:
        for password in passwords_to_try:
            try:
                logger.info(f"Attempting to load {keystore_path} using cryptography library with password: {password}")
                actual_key_pwd = key_password or password
                context, format_type = create_ssl_context_with_cryptography(keystore_path, actual_key_pwd)
                logger.info(f"Successfully loaded certificate as {format_type} format")
                return context
            except Exception as e:
                # Only log the first error in detail
                if password == passwords_to_try[0]:
                    logger.info(f"Cryptography loading failed with password {password}: {e}")
                    exceptions.append(f"Cryptography: {e}")
    else:
        logger.warning("Cryptography library not available, using fallback methods")
    
    # Try standard ssl module with PKCS12 loading
    for password in passwords_to_try:
        try:
            logger.info(f"Attempting to load {keystore_path} as PKCS12 format with password: {password}")
            context = create_ssl_context_from_pkcs12(keystore_path, password)
            logger.info(f"Successfully loaded certificate as PKCS12 format with password: {password}")
            return context
        except Exception as e:
            # Only log the first error in detail
            if password == passwords_to_try[0]:
                logger.info(f"PKCS12 loading failed with password {password}: {e}")
                exceptions.append(f"PKCS12: {e}")
    
    # Finally try JKS format with both passwords
    for password in passwords_to_try:
        try:
            logger.info(f"Attempting to load {keystore_path} as JKS format with password: {password}")
            # Create a default SSL context
            context = ssl.create_default_context()
            
            # Load the JKS keystore
            ks = jks.KeyStore.load(keystore_path, password)
            
            # Get all certificates from the keystore
            with tempfile.NamedTemporaryFile(delete=False) as ca_cert_file:
                # If alias is specified, only extract that certificate
                if alias and alias in ks.certs:
                    cert = ks.certs[alias]
                    ca_cert_file.write(cert.cert)
                else:
                    # Otherwise extract all certificates
                    for cert_alias, cert in ks.certs.items():
                        ca_cert_file.write(cert.cert)
            
            # Load certificates to the SSL context
            context.load_verify_locations(cafile=ca_cert_file.name)
            
            # Clean up temporary file
            os.unlink(ca_cert_file.name)
            
            # Configure SSL settings
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            logger.info(f"SSL context created successfully from JKS file with password: {password}")
            return context
        except Exception as e:
            # Only log the first error in detail
            if password == passwords_to_try[0]:
                logger.info(f"JKS loading failed with password {password}: {e}")
                exceptions.append(f"JKS: {e}")
    
    # If we reached here, all methods failed
    logger.error(f"All certificate loading methods failed. SSL context creation failed.")
    error_msg = "\n".join(exceptions)
    raise Exception(f"Failed to create SSL context from certificate file: {error_msg}")


def parse_close_reason(reason: str) -> Tuple[str, str]:
    """
    Parse a WebSocket close reason into error code and message.
    
    Args:
        reason: The close reason string from the WebSocket
        
    Returns:
        Tuple of (error_code, error_message)
    """
    if ":" in reason:
        parts = reason.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return "UNKNOWN", reason


def get_error_from_close_reason(reason: str) -> Optional[str]:
    """
    Extract a user-friendly error message from a close reason.
    
    Args:
        reason: The close reason string from the WebSocket
        
    Returns:
        An error message suitable for display to the user
    """
    error_code, error_message = parse_close_reason(reason)
    
    error_messages = {
        "NOT_CONSISTENT": "Authentication failed: Invalid headers or license information",
        "VIOLATED_POLICY": "License not valid or expired",
        "INTERNAL_ERROR": "Server error: Please check CoreHub logs for more information",
        "CLOSED_ABNORMALLY": "Connection closed unexpectedly"
    }
    
    return error_messages.get(error_code, error_message)
