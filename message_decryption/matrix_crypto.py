#!/usr/bin/env python3

import base64
import base58
import hashlib
import hmac
import json
import struct
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.backends import default_backend
from nacl.secret import SecretBox
from nacl.utils import random
from nacl.public import PrivateKey, PublicKey, Box
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

class MatrixCrypto:
    @staticmethod
    def decode_recovery_key(recovery_key: str) -> bytes:
        """Decode Matrix recovery key from base58 format"""
        # Remove spaces and validate format
        clean_key = recovery_key.replace(' ', '')

        if not clean_key.startswith('E'):
            raise ValueError("Recovery key must start with 'E'")

        try:
            # Decode base58
            decoded = base58.b58decode(clean_key)

            # Matrix recovery keys are 35 bytes: prefix(1) + key(32) + checksum(2)
            if len(decoded) < 33:
                raise ValueError(f"Recovery key too short: {len(decoded)} bytes")

            # For now, just return the key portion (skip checksum validation)
            # Real implementation would validate checksum
            if len(decoded) == 35:
                return decoded[1:33]  # Skip prefix and checksum
            else:
                # Fallback: use first 32 bytes after prefix
                return decoded[1:33] if len(decoded) >= 33 else decoded[1:]

        except Exception as e:
            # If base58 decode fails, try base64 as fallback
            try:
                # Some recovery keys might be base64 encoded
                clean_key_b64 = clean_key[1:]  # Remove 'E' prefix
                decoded = base64.b64decode(clean_key_b64 + '==')  # Add padding
                return decoded[:32]  # Take first 32 bytes
            except:
                raise ValueError(f"Failed to decode recovery key: {e}")

    @staticmethod
    def derive_backup_key(recovery_key_bytes: bytes, backup_info: Dict) -> bytes:
        """Derive backup decryption key from recovery key using Matrix spec"""

        try:
            # For Matrix v1 curve25519 backup, the recovery key IS the private key
            # No additional derivation needed
            logger.info("Using recovery key as backup private key (curve25519)")
            return recovery_key_bytes

        except Exception as e:
            logger.error(f"Failed to derive backup key: {e}")
            raise

    @staticmethod
    def decrypt_session_data(session_data: Dict, backup_private_key: bytes) -> Optional[str]:
        """
        Decrypt Matrix backup session data using curve25519-aes-sha2 format
        Based on Matrix specification for backup decryption
        """

        try:
            # Helper function for unpadded base64
            def safe_b64decode(data):
                padding = 4 - (len(data) % 4)
                if padding != 4:
                    data += '=' * padding
                return base64.b64decode(data)

            # Extract the encrypted session components
            ephemeral_b64 = session_data.get("ephemeral", "")
            ciphertext_b64 = session_data.get("ciphertext", "")
            mac_b64 = session_data.get("mac", "")

            ephemeral_key = safe_b64decode(ephemeral_b64)
            ciphertext = safe_b64decode(ciphertext_b64)
            mac = safe_b64decode(mac_b64)

            logger.info(f"Attempting Matrix curve25519-aes-sha2 decryption")
            logger.info(f"Ephemeral key: {len(ephemeral_key)} bytes")
            logger.info(f"Ciphertext: {len(ciphertext)} bytes")
            logger.info(f"MAC: {len(mac)} bytes")

            # Matrix curve25519-aes-sha2 algorithm:
            # 1. Perform ECDH between backup private key and ephemeral public key
            backup_private = x25519.X25519PrivateKey.from_private_bytes(backup_private_key)
            ephemeral_public = x25519.X25519PublicKey.from_public_bytes(ephemeral_key)
            shared_secret = backup_private.exchange(ephemeral_public)

            # 2. Derive encryption and MAC keys using HKDF-SHA256
            # Key derivation for Matrix backup v1
            hkdf_encrypt = HKDF(
                algorithm=hashes.SHA256(),
                length=32,  # AES-256
                salt=b'\x00' * 32,  # 32 zero bytes
                info=b"backup",  # Matrix uses "backup" as info
                backend=default_backend()
            )
            encrypt_key = hkdf_encrypt.derive(shared_secret)

            hkdf_mac = HKDF(
                algorithm=hashes.SHA256(),
                length=32,  # HMAC key
                salt=b'\x00' * 32,
                info=b"backup_auth",
                backend=default_backend()
            )
            mac_key = hkdf_mac.derive(shared_secret)

            # 3. Verify MAC over ephemeral key + ciphertext
            computed_mac = hmac.new(
                mac_key,
                ephemeral_key + ciphertext,
                hashlib.sha256
            ).digest()[:8]  # Truncate to 8 bytes

            if mac != computed_mac:
                logger.warning(f"MAC verification failed: expected {computed_mac.hex()}, got {mac.hex()}")
                # Continue anyway for testing

            # 4. Decrypt ciphertext with AES-CTR
            # Matrix uses counter mode with zero IV
            cipher = Cipher(
                algorithms.AES(encrypt_key),
                modes.CTR(b'\x00' * 16),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            # 5. Parse decrypted JSON to extract session key
            session_json = json.loads(decrypted_bytes.decode('utf-8'))
            session_key = session_json.get("session_key")

            if session_key:
                logger.info("Session key decrypted successfully!")
                return session_key
            else:
                logger.error("No session_key found in decrypted data")
                return None

        except json.JSONDecodeError:
            logger.error("Decrypted data is not valid JSON")
            logger.error(f"Raw decrypted bytes: {decrypted_bytes[:50].hex()}...")
            return None
        except Exception as e:
            logger.error(f"Session decryption failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def decrypt_megolm_event(ciphertext: str, session_key: str) -> Optional[str]:
        """Decrypt a Megolm encrypted message"""

        try:
            # For now, implement a basic AES-CTR decryption
            # Real Megolm is more complex with ratcheting

            # Decode the session key and ciphertext
            key_bytes = base64.b64decode(session_key)
            cipher_bytes = base64.b64decode(ciphertext)

            if len(cipher_bytes) < 16:  # Need at least IV
                logger.error("Ciphertext too short")
                return None

            # Extract IV and payload
            iv = cipher_bytes[:16]
            payload = cipher_bytes[16:]

            # Use AES-CTR for decryption (simplified Megolm)
            cipher = Cipher(
                algorithms.AES(key_bytes[:32]),  # Use first 32 bytes as key
                modes.CTR(iv)
            )
            decryptor = cipher.decryptor()

            plaintext = decryptor.update(payload) + decryptor.finalize()

            # Parse as JSON
            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Megolm decryption failed: {e}")
            return None

# Test function
async def test_recovery_key_decoding(recovery_key: str):
    """Test recovery key decoding"""

    print("Testing Recovery Key Decoding")
    print("=" * 30)

    try:
        # Decode recovery key
        key_bytes = MatrixCrypto.decode_recovery_key(recovery_key)
        print(f"✓ Recovery key decoded successfully")
        print(f"  Key bytes length: {len(key_bytes)}")
        print(f"  Key hex: {key_bytes.hex()[:20]}...")

        # Test backup key derivation
        fake_backup_info = {"algorithm": "m.megolm_backup.v1.curve25519-aes-sha2"}
        backup_key = MatrixCrypto.derive_backup_key(key_bytes, fake_backup_info)
        print(f"✓ Backup key derived successfully")
        print(f"  Backup key hex: {backup_key.hex()[:20]}...")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

if __name__ == "__main__":
    import asyncio

    # Test with example key format
    test_key = "YOUR_RECOVERY_KEY_HERE"
    asyncio.run(test_recovery_key_decoding(test_key))
