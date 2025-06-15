# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in InvOCR, please report it by emailing security@invocr.com.

**Please do not report security vulnerabilities through public GitHub issues.**

Include the following information:
- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

## Security Measures

InvOCR implements several security measures:

### Input Validation
- File type validation
- File size limits
- Input sanitization
- Path traversal protection

### API Security
- Rate limiting
- CORS configuration
- Request validation
- Error handling without information leakage

### Data Protection
- No persistent storage of uploaded files
- Automatic cleanup of temporary files
- Secure file handling

### Container Security
- Non-root user in containers
- Minimal base images
- Regular security updates
- Vulnerability scanning

## Best Practices

When deploying InvOCR:

1. **Use HTTPS** in production
2. **Configure firewalls** appropriately
3. **Regular updates** of dependencies
4. **Monitor logs** for suspicious activity
5. **Implement proper backup** procedures
6. **Use strong secrets** and rotate them regularly

## Contact

