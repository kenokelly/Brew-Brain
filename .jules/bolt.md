## 2024-05-18 - HTTP Connection Pooling

**Learning:** When making repeated synchronous API calls to external services (like `https://api.brewfather.app` in `app/services/alerts.py`), creating a new `requests.get()` each time can introduce significant overhead due to repeated TCP connection setups and TLS handshakes.
**Action:** Use a `requests.Session()` object when making sequential or looped HTTP requests to the same origin to enable HTTP connection pooling. This drastically reduces connection overhead.
