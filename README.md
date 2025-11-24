🍺 Brew Brain: Intelligent Brewery Monitor

Turn your passive Tilt Hydrometer into an active, AI-powered brewing assistant.

Brew Brain is a Dockerized add-on for Raspberry Pi breweries. It sits on top of your existing InfluxDB/Grafana stack (or creates a new one) to provide:

Machine Learning Predictions: Predicts Final Gravity (FG) and completion time based on your specific history.

📊 Instant Dashboard: Comes with a professional, pre-configured Grafana dashboard (ABV, Attenuation, Battery) out of the box. No manual setup required.

Smart Calibration: Corrects noisy Tilt readings with a single manual offset entry.

Safety Watchdog: Monitors Tilt signal health and Raspberry Pi connectivity (reboots WiFi if stuck).

Test Mode: Run water tests or cleaning cycles without messing up your historical fermentation graphs.

Alerting: Telegram notifications for "Stuck Fermentation" or "Temp Runaway."

⚡ Prerequisites

Hardware: Raspberry Pi 4 or 5 (Recommended).

OS: Raspberry Pi OS (Bookworm 64-bit preferred).

Sensor: Tilt Hydrometer (Any color).

🚀 Installation

Choose the option that matches your current setup.

Option 1: The "Fresh Start" (I have nothing installed)

Use this if you are setting up a brand new Pi 5 and need the full stack.

TILTpi Logic: Uses the official flow from Baron Brew's TILTpi.

Docker Infrastructure: Adapted from the guide by Stian Josok.

Step 1: Install TILTpi (The Driver)

Since the official TILTpi SD card image does not support Raspberry Pi 5 yet, we must install the software manually on your OS.

Install Node-RED:
Run the official script to install Node-RED on Bookworm:

bash <(curl -sL [https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered](https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered))
# Type 'y' (Yes) when asked to install Pi-specific nodes.


Enable & Start Node-RED:

sudo systemctl enable nodered.service
sudo systemctl start nodered.service


Install the TILTpi Flow:

Open your browser to http://<pi-ip>:1880.

Click the Hamburger Menu (top right) -> Manage Palette.

Click the Install tab, search for node-red-contrib-tilt, and click install.

Import the Flow: Download the official TILTpi Flow JSON.

In Node-RED: Menu -> Import -> Paste the JSON code -> Click Import.

Click Deploy (Top Right Red Button).

Verify: Go to http://<pi-ip>:1880/ui. You should see your Tilt data.

Step 2: Install Brew Brain (The Intelligence)

Clone the Repo:

git clone [https://github.com/yourname/brew-brain.git](https://github.com/yourname/brew-brain.git)
cd brew-brain


Configure Environment:
Create a .env file:

nano .env


Add the following:

INFLUX_USER=admin
INFLUX_PASS=password123
INFLUX_TOKEN=my-super-secret-token


Launch:

docker compose up -d --build


Access:

Command Dashboard: http://<pi-ip>:5000

Grafana: http://<pi-ip>:3000 (User/Pass: admin/admin)

Option 2: The "Patch" (I already have TILTpi / InfluxDB)

Use this if you already followed the Baron Brew TILTpi Guide or similar guides and have a running database.

Clone the Repo:

git clone [https://github.com/yourname/brew-brain.git](https://github.com/yourname/brew-brain.git)
cd brew-brain


Identify your Network & Token:

Run docker network ls. Note the name of your existing network (e.g., tilt-pi-network or brewery-net).

Get your Org, Bucket, and Token from your existing InfluxDB.

Edit the Patch File:
Open docker-compose.brain-only.yml and update the networks section at the bottom to match your existing network name.

Launch the Brain:

export INFLUX_TOKEN=your_existing_token
export INFLUX_ORG=homebrew
export INFLUX_BUCKET=fermentation

docker compose -f docker-compose.brain-only.yml up -d --build


This will spin up only the Brain container and attach it to your existing database.

🛡️ Installing the Watchdog (Pi 5 / Bookworm)

The Watchdog runs outside Docker to handle physical network resets (WiFi restarts/Reboots) which Docker cannot safely do.

Install Dependencies (Host Side):

sudo apt update
sudo apt install python3-requests


Copy the Script:

cp watchdog.py /home/pi/watchdog.py


Automate with Cron:

crontab -e


Add this line to run every 5 minutes:

*/5 * * * * /usr/bin/python3 /home/pi/watchdog.py >> /home/pi/watchdog.log 2>&1


📊 Usage Guide

1. The Dashboard (http://<pi-ip>:5000)

Status: Shows Tilt Signal Strength (RSSI) and Pi CPU Temp.

Brewfather Sync: Go to Settings, enter your User ID and API Key. Then click the "Sync" icon on the dashboard to auto-fill your Batch Name and Gravity Targets.

Calibration: Take a reading with your refractometer. Enter it in the "Calibration" box. The system calculates the offset automatically.

Test Mode: Toggle this ON when cleaning. Data will be logged to test_readings instead of calibrated_readings.

2. Installing on Mobile (iOS/Android)

This dashboard is a Progressive Web App (PWA).

Open http://<pi-ip>:5000 in Safari (iOS) or Chrome (Android).

Tap Share -> Add to Home Screen.

It will now open as a fullscreen app with persistent login.

3. Grafana Integration

You don't need to build charts manually!

Open Grafana (:3000).

Go to Dashboards.

Click "Brew Brain Production".

This pre-loaded dashboard compares your raw Tilt data with the ML-corrected calibrated_readings and shows your live Attenuation %.

Acknowledgements

Baron Brew: Creators of the Tilt Hydrometer and the TILTpi software used in this stack.

Stian Josok: Author of the Tilt Pi Monitor Stack Docker Guide which inspired the container architecture.

Tiltpi: Brewing data and ML: Referenced Gemini Project.