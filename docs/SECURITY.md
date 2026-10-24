# Security Guidelines

## Environment Variables
- Never commit `.env` files
- Use `.env.example` as template
- Set: `export GMAIL_APP_PASSWORD="your_app_password"`

## SSH Access
- Private key: `~/.ssh/github_portfolio` (0600)
- Public key added to GitHub only
- Rotate keys yearly

## Image Validation
- Validates base64 encoding
- Checks JPEG/PNG magic bytes
- Limits size to 25MB
- Sanitizes filenames

## Error Handling
- Retry logic on webhook failures (3 attempts)
- Proper logging to file + stdout
- No sensitive data in logs
- Timeout on all network requests

## File Permissions
- `.email_processed_hashes`: 0600 (readable by owner only)
- `devis_outputs/*.html`: 0644 (readable, not writable)
- `.env`: Add to .gitignore

## Rate Limiting
- 60-second polling interval (prevent spam)
- Message deduplication (hash-based)

## Monitoring
- Logs saved to `email_to_devis.log`
- Check logs for errors: `tail -f email_to_devis.log`

