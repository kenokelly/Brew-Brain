## 2024-05-14 - Fast String Check Before JSON Parsing
**Learning:** When extracting specific data (like 'Product' schemas) from parsed HTML components such as JSON-LD, standard `json.loads()` on every block is computationally expensive.
**Action:** Utilize optimized string substring checks (e.g., `if '"Product"' not in script.string:`) to quickly filter out irrelevant content before invoking expensive parsing operations.
