# Matrix Message Decryption Add-On Scripts

This directory contains scripts for decrypting and exporting Matrix/Beeper messages for use with the exocortex project.

## Privacy & Security Notice

All private credentials and sensitive data have been removed from these scripts. Before using them, you'll need to configure your own credentials.

### Sanitized Items

The following private data has been removed:
- **Access tokens**: All Matrix access tokens have been replaced with placeholders
- **Recovery keys**: Encryption recovery keys have been replaced with placeholders
- **Usernames**: Personal usernames have been replaced with placeholders

### Configuration Setup

1. **Copy the example config:**
   ```bash
   cp matrix_config.json.example matrix_config.json
   ```

2. **Edit `matrix_config.json` with your credentials:**
   - `homeserver`: Your Matrix homeserver URL (e.g., https://matrix.beeper.com)
   - `username`: Your Matrix username
   - `access_token`: Your Matrix access token (get via `setup_auth.py`)
   - `recovery_key`: Your Matrix recovery key (for E2EE decryption)
   - `output_directory`: Where to export messages (default: "matrix_exports")

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run setup authentication:**
   ```bash
   python setup_auth.py
   ```

## Quick Start

1. **Test your connection:**
   ```bash
   python test_connection.py matrix_config.json
   ```

2. **Sync and decrypt messages:**
   ```bash
   ./run_matrix_pipeline.sh
   ```

3. **Export to exocortex:**
   - Messages will be exported to the configured output directory
   - Use the exported JSONL files with your exocortex workflow

## Script Overview

- `decrypt_and_export.py`: Main decryption and export pipeline
- `matrix_sync.py`: Sync messages from Matrix server
- `matrix_crypto.py`: Cryptographic functions for E2EE decryption
- `setup_auth.py`: Interactive authentication setup
- `run_matrix_pipeline.sh`: Complete automated pipeline
- `matrix_aggregator/`: Core Matrix client library

## Important Security Notes

- **Never commit** your `matrix_config.json` file with real credentials
- **Keep your recovery key safe** - it can decrypt all your messages
- **Access tokens expire** - you may need to regenerate them periodically
- **Use `.gitignore`** to exclude sensitive files (already configured)

## Troubleshooting

See `MATRIX_README.md` for detailed documentation and troubleshooting steps.

---

**Note**: These scripts were sanitized for reuse. Always review code before using it with sensitive credentials.
