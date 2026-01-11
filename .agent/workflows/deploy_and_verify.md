---
description: Build, Deploy, and Verify Brew-Brain on the Raspberry Pi
---
1. Run the standardized deployment script.

    ```bash
    // turbo
    ./deploy_and_verify.sh
    ```

    This script handles:
    * **Build**: Rebuilds the Docker containers on the remote host.
    * **Deploy**: Restarts the services (`brew-brain`, `influxdb`, `grafana`, `telegraf`).
    * **Verify**: Checks container status, API connectivity, and data integrity.
