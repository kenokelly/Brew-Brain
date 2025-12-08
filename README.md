````markdown
# 🍺 Brew Brain: Intelligent Brewery Monitor

**Turn your passive Tilt Hydrometer into an active, AI-powered brewing assistant.**

Brew Brain is a Dockerized add-on for Raspberry Pi breweries. It sits on top of your existing InfluxDB/Grafana stack (or creates a new one) to provide:

* **🧠 Machine Learning Predictions:** Predicts Final Gravity (FG) and completion time based on your specific fermentation history using logistic regression.
* **📊 Instant Dashboard:** Comes with a professional, pre-configured Grafana dashboard (ABV, Attenuation, Battery) out of the box. No manual setup required.
* **🎯 Smart Calibration:** Corrects noisy Tilt readings with a single manual offset entry.
* **🛡️ Safety Watchdog:** Monitors Tilt signal health and Raspberry Pi connectivity (reboots WiFi if stuck).
* **🧪 Test Mode:** Run water tests or cleaning cycles without messing up your historical fermentation graphs.
* **🔔 Alerting:** Telegram notifications for "Stuck Fermentation" or "Temp Runaway."

---

## ⚡ Prerequisites

* **Hardware:** Raspberry Pi 4 or 5 (Recommended).
* **OS:** Raspberry Pi OS (Bookworm 64-bit preferred).
* **Sensor:** Tilt Hydrometer (Any color).

---

## 🚀 Installation

Choose the scenario that best matches your current equipment.

### Scenario A: The "Fresh Start" (Brand New Pi 5)
*You have a fresh SD card with Raspberry Pi OS (Bookworm) and nothing else.*

**1. Install Docker**
We need Docker to run the database and dashboard. Run these commands:
```bash
# Install Docker
curl -fsSL [https://get.docker.com](https://get.docker.com) -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the Docker group (so you don't need 'sudo' every time)
sudo usermod -aG docker $USER

# IMPORTANT: Log out and log back in for this to take effect!
logout
````

**2. Install TILTpi (The Driver)**
Since the official TILTpi SD image does not support Raspberry Pi 5 yet, we install it manually.

  * **Install Node-RED:**

    ```bash
    bash <(curl -sL [https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered](https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered))
    # Type 'y' when asked to install Pi-specific nodes.

    sudo systemctl enable nodered.service
    sudo systemctl start nodered.service
    ```

  * **Configure Node-RED:**

    1.  Open your browser to `http://<pi-ip>:1880`.
    2.  Click the Hamburger Menu (top right) -\> **Manage Palette**.
    3.  Click the **Install** tab, search for `node-red-contrib-tilt`, and click install.
    4.  **Import the Flow:** Download the [official TILTpi Flow JSON](https://www.google.com/search?q=https://github.com/baronbrew/TILTpi/blob/master/node-red-flow.json).
    5.  In Node-RED: Menu -\> Import -\> Paste the JSON code -\> Click Import.
    6.  Click **Deploy** (Top Right Red Button).
    7.  *Verify:* Go to `http://<pi-ip>:1880/ui`. You should see your Tilt data.

**3. Install Brew Brain**
Now we deploy the Intelligence, Database, and Dashboard.

```bash
git clone [https://github.com/kenokelly/brew-brain.git](https://github.com/kenokelly/brew-brain.git)
cd brew-brain

# Create your settings file
nano .env
```

Add the following configuration:

```ini
INFLUX_USER=admin
INFLUX_PASS=password123
INFLUX_TOKEN=my-super-secret-token
```

Launch the full stack:

```bash
docker compose up -d --build
```

-----

### Scenario B: The "Upgrader" (I have TiltPi Only)

*You already have a working TiltPi (Node-RED) setup, but no database or nice dashboards.*

You do **not** need to reinstall Node-RED. We will just add the "Brain," Database, and Dashboard alongside your existing setup.

**1. Install Docker** (If you haven't already)

```bash
curl -fsSL [https://get.docker.com](https://get.docker.com) -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
logout
```

*(Log back in after this step)*

**2. Deploy the Stack**
We use the standard installation, which is configured to listen to your existing TiltPi.

```bash
git clone [https://github.com/kenokelly/brew-brain.git](https://github.com/kenokelly/brew-brain.git)
cd brew-brain

# Configure your passwords
nano .env
# (Add your chosen User/Pass/Token as shown in Scenario A)

# Start the services
docker compose up -d --build
```

*Note: The system expects your TiltPi to be running on port 1880. It connects automatically.*

-----

### Scenario C: The "Patch" (I have TiltPi + InfluxDB + Grafana)

*You already have a full brewery dashboard stack, but you want to add the AI Predictions and Calibration.*

**1. Clone the Repo**

```bash
git clone [https://github.com/kenokelly/brew-brain.git](https://github.com/kenokelly/brew-brain.git)
cd brew-brain
```

**2. Identify your Network**
The Brain needs to join your existing Docker network to talk to your database.

```bash
docker network ls
# Look for your existing network (e.g., 'tilt_network' or 'brewery-net')
```

**3. Edit the Config**
Open `docker-compose.brain-only.yml`:

```bash
nano docker-compose.brain-only.yml
```

  * Scroll to the bottom (`networks:`).
  * Change `name: tilt-pi-network` to the name you found in step 2.
  * *Check `services: brew-brain: environment: INFLUX_URL`: Ensure `influxdb` matches your existing container name.*

**4. Launch**

```bash
# Export your EXISTING token so the Brain can write to your DB
export INFLUX_TOKEN=your_existing_token
export INFLUX_ORG=homebrew
export INFLUX_BUCKET=fermentation

# Launch only the Brain container
docker compose -f docker-compose.brain-only.yml up -d --build
```

-----

## 🛡️ Installing the Watchdog (Pi 5 / Bookworm)

The Watchdog runs outside Docker to handle physical network resets (WiFi restarts/Reboots) which Docker cannot safely do.

**1. Install Dependencies (Host Side)**

```bash
sudo apt update
sudo apt install python3-requests
```

**2. Copy the Script**

```bash
cp watchdog.py /home/pi/watchdog.py
```

**3. Automate with Cron**

```bash
crontab -e
```

Add this line to run every 5 minutes:

```bash
*/5 * * * * /usr/bin/python3 /home/pi/watchdog.py >> /home/pi/watchdog.log 2>&1
```

-----

## 📊 Usage Guide

### 1\. The Dashboard (http://\<pi-ip\>:5000)

  * **Status:** Shows Tilt Signal Strength (RSSI) and Pi CPU Temp.
  * **Brewfather Sync:** Go to Settings, enter your User ID and API Key. Then click the "Sync" icon on the dashboard to auto-fill your Batch Name and Gravity Targets.
  * **Calibration:** Take a reading with your refractometer. Enter it in the "Calibration" box. The system calculates the offset automatically.
  * **Test Mode:** Toggle this **ON** when cleaning. Data will be logged to `test_readings` instead of `calibrated_readings`.

### 2\. Installing on Mobile (iOS/Android)

This dashboard is a Progressive Web App (PWA).

1.  Open `http://<pi-ip>:5000` in Safari (iOS) or Chrome (Android).
2.  Tap **Share** -\> **Add to Home Screen**.
3.  It will now open as a fullscreen app with persistent login.

### 3\. Grafana Integration (http://\<pi-ip\>:3000)

You don't need to build charts manually\!

1.  Open Grafana (User/Pass: `admin`/`admin` default).
2.  Go to **Dashboards**.
3.  Click **"Brew Brain Production"**.

-----

## 🧠 Machine Learning Features

The "Brain" doesn't just log data; it analyzes the shape of your fermentation curve using Logistic Regression (Sigmoid fitting).

**How it works:**

1.  **Data Gathering:** It reads the last 21 days of SG data.
2.  **Curve Fitting:** It fits a standard fermentation curve equation: `SG(t) = FG + (OG - FG) / (1 + e^(k * (t - t_mid)))`
3.  **Prediction:** It calculates the asymptote (Predicted FG) and the point where the curve flattens out (Estimated Completion Date).

**To View Predictions:**
Add a new panel to your Grafana dashboard:

  * **Query:** `from(bucket: "fermentation") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "predictions") |> last()`
  * **Visualization:** Stat Panel
  * **Fields:** `predicted_fg` and `days_remaining`

-----

## Acknowledgements

  * **Baron Brew:** Creators of the Tilt Hydrometer and the TILTpi software used in this stack.
  * **Stian Josok:** Author of the *Tilt Pi Monitor Stack Docker Guide* which inspired the container architecture.
  * **Tiltpi:** Brewing data and ML concepts referenced from Gemini Project.

<!-- end list -->

```
```
# ... (Previous Sections) ...

## 🔒 Security & Best Practices

Since this device monitors physical processes (temperature/fermentation), security is important.

### 1. Hardened Secrets
The `.gitignore` file includes `.env`. **Do not remove this.** Your `.env` file contains your Database passwords and Telegram tokens. Never commit it to GitHub.

### 2. Grafana Ports
By default, Grafana is configured with `GF_AUTH_ANONYMOUS_ENABLED=true` to allow the dashboard to load without login on your local network (LAN).
* **Safe:** If you only access this via `http://192.168.x.x` at home.
* **Dangerous:** If you port-forward port `3000` to the internet.
* **Recommendation:** If exposing to the web, set `GF_AUTH_ANONYMOUS_ENABLED=false` in `docker-compose.yml` and use strong passwords.

### 3. API Validation
The System API (`/api/settings`) enforces strict type checking to prevent injection of invalid data types into the configuration database.

# ... (Rest of README) ...
