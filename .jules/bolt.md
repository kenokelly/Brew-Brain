## 2024-05-18 - Missing Connection Pooling for External API Requests
**Learning:** Found a codebase-specific performance anti-pattern where multiple sequential synchronous API calls to external services (like the Brewfather API in `alerts.py`) were using `requests.get()` directly, resulting in establishing new TCP connections and TLS handshakes for every request.
**Action:** Use `requests.Session()` to enable HTTP connection pooling whenever sequential or paginated external API requests are made. This drastically cuts latency by reusing the underlying TCP/TLS connection.
