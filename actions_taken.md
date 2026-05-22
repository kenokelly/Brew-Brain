# Actions Taken Log

This file tracks the progress and implemented modules during development.

## 2026-05-22

**Phase 4: Sourcing Engine**
- Integrated LLM (Ollama) to extract ingredient queries (e.g. converting "Citra" to {"hop": "Citra"}).
- Built scraping logic via Playwright (`web_scraper.py`) for multiple suppliers (e.g. "The Homebrew Company", "Get Er Brewed") with caching.
- Developed backend endpoints `POST /api/automation/sourcing/extract` and `POST /api/automation/sourcing/search`.
- Built the frontend `Sourcing.tsx` component with tabs for LLM Parsing vs Manual Entry, loading skeletons, and interactive search results showing price and supplier links.
- Added comprehensive unit tests in `tests/test_sourcing.py`.

**Phase 5: Auto-Order & Inventory Management**
- Converted `fetch_inventory_with_backoff` into an asynchronous Celery task (`@celery.task`) to prevent UI hanging during Brewfather HTTP 429 rate limit errors.
- Built polling endpoint `GET /api/automation/inventory/sync/status/<task_id>`.
- Updated `Inventory.tsx` to poll Celery task status.
- Added a "Low Stock" indicator and a "Re-order Deficit" button in the frontend that connects dynamically with the Phase 4 Sourcing engine.
- Ensured integration of `calculate_hop_freshness` mathematical degradation into the inventory calculations.
- Added unit tests in `tests/test_inventory.py`.

**Phase 6: Simulation & R&D**
- Converted Monte Carlo math processing (`run_monte_carlo_simulation`) into a background Celery task `run_simulation_task` inside `tasks.py`.
- Refactored `Simulation.tsx` to successfully connect to `POST /api/automation/simulate` and poll status.
- Rendered the Monte Carlo distribution bins dynamically inside a Recharts `AreaChart` (Possibility Graph).
- Injected LLM "AI Brewmaster" stress test results dynamically into an "AI Analysis Panel" component.
- Refactored `test_simulation.py` to use proper Pytest mocking against Celery tasks to prevent InfluxDB connection hangs and ensure continuous integration.

**DevOps & Git**
- Code successfully checked into Git under branch `main` (`feat(automation): Implement Phase 4 Sourcing, Phase 5 Inventory, Phase 6 Simulation`).
