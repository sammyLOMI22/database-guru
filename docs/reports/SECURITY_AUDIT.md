# Security Audit Report - Database Guru

**Date:** October 7, 2025
**Status:** ✅ Generally Safe for Development / ⚠️ Needs Hardening for Production

---

## 📊 Executive Summary

### Python Backend
✅ **No known vulnerabilities** in 75 installed packages (scanned with Safety)

### Node.js Frontend
⚠️ **2 moderate vulnerabilities** in development dependencies only
- **esbuild** <=0.24.2: Development server can accept requests from any website (GHSA-67mh-4wv8-2f99)
- **vite**: Depends on vulnerable esbuild version

**Impact:** These vulnerabilities only affect the **development server**, NOT production builds. The development server should only be run locally and never exposed to the internet.

---

## 🔍 Detailed Findings

### 1. Backend Security Issues

#### ✅ Dependencies: CLEAN
```
Scanned: 75 packages
Vulnerabilities: 0
Scanner: Safety v3.6.2 (Open-source vulnerability database)
```

#### ⚠️ Code Security Issues (Found)

**HIGH PRIORITY:**

1. **Password Storage - UNENCRYPTED**
   - **Location:** `src/api/endpoints/connections.py:97`
   - **Issue:** Database passwords stored in plaintext
   ```python
   password_encrypted=connection_data.password,  # Store as-is for now
   ```
   - **Risk:** Database credentials exposed if SQLite file is stolen
   - **Fix Required:** Implement proper encryption (Fernet, AES-256)

2. **SQL Injection Risk - MEDIUM**
   - **Location:** `src/core/executor.py`
   - **Issue:** While using parameterized queries, LLM-generated SQL is executed directly
   - **Current Mitigation:** Read-only by default, require `allow_write=True` flag
   - **Risk:** Malicious prompts could trick LLM into generating harmful SQL
   - **Recommendation:** Implement SQL query whitelisting for common patterns

3. **No Rate Limiting on Query Endpoint**
   - **Location:** `src/api/endpoints/query.py`
   - **Issue:** No specific rate limiting for expensive LLM/DB operations
   - **Current:** Global rate limit: 100 req/60s (middleware)
   - **Recommendation:** Lower limit for `/api/query/` endpoint (e.g., 10/min)

4. **Missing Input Validation**
   - **Location:** Multiple endpoints
   - **Issue:** Some endpoints accept unrestricted text inputs
   - **Recommendation:** Add max length limits, sanitization

5. **CORS - Too Permissive**
   - **Location:** `src/main.py:61-66`
   - **Current:** `allow_origins=["*"]` (allows any origin)
   - **Risk:** CSRF attacks in production
   - **Fix:** Restrict to specific domains in production

6. **No Authentication/Authorization**
   - **Issue:** No user authentication implemented
   - **Risk:** Anyone can access the API
   - **Recommendation:** Add JWT/OAuth for production

**LOW PRIORITY:**

7. **Debug Mode Enabled**
   - **Location:** `.env` has `DEBUG=True`
   - **Risk:** Verbose error messages leak system info
   - **Fix:** Disable in production

8. **Secret Key Hardcoded**
   - **Location:** `.env` has `SECRET_KEY=dev-secret-key-...`
   - **Risk:** Sessions/tokens can be forged
   - **Fix:** Generate random secret in production

---

### 2. Frontend Security Issues

#### ⚠️ Dependencies: 2 MODERATE (Dev-only)

**esbuild <=0.24.2 (Moderate)**
- **CVE:** GHSA-67mh-4wv8-2f99
- **Issue:** Dev server accepts requests from any website
- **Affected:** Development environment only
- **Impact:** Low (dev server should never be exposed publicly)
- **Fix:** `npm audit fix --force` (may break compatibility)
- **Recommendation:** Keep current for dev, not an issue in production build

#### ✅ Code Security: CLEAN

Frontend code follows React security best practices:
- Using TypeScript for type safety
- No `dangerouslySetInnerHTML` usage
- Proper input sanitization in forms
- HTTPS API calls (in production)

---

## 🛡️ Security Recommendations

### For Development (Current Use)
✅ **Safe to use as-is** with these precautions:
1. Only run on localhost (never expose to internet)
2. Don't store real production database credentials
3. Don't commit `.env` file with real secrets to Git

### For Production Deployment

**CRITICAL - Must Fix:**

1. **Encrypt Database Passwords**
   ```python
   from cryptography.fernet import Fernet

   # Generate key: Fernet.generate_key()
   cipher = Fernet(settings.ENCRYPTION_KEY)
   encrypted_password = cipher.encrypt(password.encode())
   ```

2. **Restrict CORS Origins**
   ```python
   allow_origins=[
       "https://yourdomain.com",
       "https://app.yourdomain.com"
   ]
   ```

3. **Add Authentication**
   - Implement JWT or OAuth2
   - Require API keys for programmatic access
   - Add user sessions

4. **Disable Debug Mode**
   ```python
   DEBUG=False
   ```

5. **Use Strong Secrets**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

**RECOMMENDED:**

6. **Add Input Validation**
   - Max query length: 500 characters
   - Max schema size: 100KB
   - Sanitize all user inputs

7. **Implement Query Whitelisting**
   - Pre-approve common SQL patterns
   - Block dangerous keywords (DROP, TRUNCATE, etc.)

8. **Rate Limiting Per Endpoint**
   ```python
   @router.post("/", dependencies=[Depends(rate_limit(10, 60))])
   ```

9. **Add Request Logging & Monitoring**
   - Log all queries for audit
   - Monitor for suspicious patterns
   - Set up alerts for anomalies

10. **Use HTTPS Only**
    - Enforce SSL/TLS in production
    - Set secure cookie flags
    - Enable HSTS headers

11. **Database Connection Security**
    - Use SSL for database connections
    - Rotate credentials regularly
    - Use read-only DB users when possible

12. **Container Security** (if using Docker)
    - Run as non-root user
    - Use minimal base images
    - Scan images for vulnerabilities
    - Keep images updated

---

## 🔐 Password Security Implementation

Create `src/security/encryption.py`:

```python
from cryptography.fernet import Fernet
from src.config.settings import Settings

class PasswordEncryption:
    def __init__(self, settings: Settings):
        # Store encryption key in environment variable
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY not set!")
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt(self, password: str) -> str:
        """Encrypt a password"""
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a password"""
        return self.cipher.decrypt(encrypted.encode()).decode()

# Generate encryption key:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```bash
ENCRYPTION_KEY=your-generated-key-here
```

Update connection creation to use encryption.

---

## 📋 Security Checklist for Production

### Before Deploying:
- [ ] Encrypt all stored passwords
- [ ] Change SECRET_KEY to random value
- [ ] Set DEBUG=False
- [ ] Restrict CORS origins
- [ ] Add authentication/authorization
- [ ] Enable HTTPS only
- [ ] Update frontend dependencies (`npm audit fix`)
- [ ] Set up rate limiting per endpoint
- [ ] Configure logging and monitoring
- [ ] Add input validation and sanitization
- [ ] Review and restrict database permissions
- [ ] Set up security headers (CSP, X-Frame-Options, etc.)
- [ ] Enable SQL query logging
- [ ] Test with security scanner (OWASP ZAP, etc.)
- [ ] Implement backup and recovery procedures
- [ ] Document security procedures

### Ongoing:
- [ ] Regular dependency updates (`pip list --outdated`, `npm outdated`)
- [ ] Monthly security audits
- [ ] Monitor logs for suspicious activity
- [ ] Rotate credentials quarterly
- [ ] Review and update access controls

---

## 🎯 Current Risk Assessment

**For Development/Testing:** ✅ **LOW RISK**
- No public exposure
- No real credentials
- Development-only vulnerabilities acceptable

**For Production Deployment:** 🔴 **HIGH RISK** (without fixes)
- Unencrypted passwords
- No authentication
- Open CORS policy
- Debug mode enabled

**After Implementing Fixes:** 🟢 **LOW-MODERATE RISK**
- Standard web application security posture
- Follows industry best practices
- Acceptable for production use

---

## 📚 Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [React Security](https://reactjs.org/docs/introducing-jsx.html#jsx-prevents-injection-attacks)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

---

**Last Updated:** October 7, 2025
**Next Review:** Before production deployment
