## 2024-05-10 - HTTP Connection Pooling with requests.Session()
**Learning:** Sequential HTTP requests to the same domain (e.g., in paginated API fetching or bulk category queries) incur significant latency due to repeated TCP handshakes and TLS negotiations.
**Action:** Always wrap multiple requests to the same host in a `with requests.Session() as session:` block to enable connection pooling and reuse the underlying socket for better performance.
