## 2024-05-13 - HTTP Connection Pooling

**Learning:** When making repeated HTTP requests to the same domain (e.g. web scraping in `scraper_utils.py`), using `requests.get()` creates a new TCP/TLS connection for every call, introducing significant performance overhead.
**Action:** Use a global `requests.Session()` object to leverage HTTP connection pooling. This reuses existing connections, drastically reducing request latency for repeated calls to the same host. Ensure tests are updated to mock the `Session` object's `.get()` method instead of `requests.get()`.
