# Brew-Brain User Guide

Welcome to Brew-Brain! This guide helps you configure your batch settings and set up integrations like Telegram alerts.

## ⚙️ accessing Settings
1.  Open the Brew-Brain dashboard (e.g., `http://192.168.155.226:5000`).
2.  Click the **Settings** tab at the top (or bottom on mobile).

---

## 🍺 Batch Profile
These settings tell Brew-Brain about what you are currently fermenting. Updating these ensures your ABV and attenuation stats are accurate.

*   **Batch Name**: A nickname for your brew (e.g., "Galaxy IPA").
*   **Start Date**: When you pitched the yeast.
*   **Original Gravity (OG)**: The specific gravity measured *before* fermentation started (e.g., `1.050`).
*   **Target FG**: Your expected finishing gravity (e.g., `1.010`). This helps the AI predict completion time.

> **Tip**: Click "Save Batch Profile" after making changes.

---

## 🤖 Setting Up Telegram Alerts
Brew-Brain can send you alerts if your temperature gets too high or if the Tilt stops sending data, and you can chat with it to get status updates!

### Step 1: Create a Bot
1.  Open Telegram and search for **@BotFather**.
2.  Send the message `/newbot`.
3.  Follow the prompts to name your bot (e.g., "MyBrewBot").
4.  BotFather will give you a **Token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`). **Copy this.**

### Step 2: Get Your Chat ID
1.  Search for **@userinfobot** in Telegram.
2.  Start the chat. It will reply with your **Id** (a number like `123456789`). **Copy this.**

### Step 3: Link to Brew-Brain
1.  Go to the **Settings** tab in Brew-Brain.
2.  Scroll down to **Integrations**.
3.  Paste your **Bot Token** into the "Bot Token" field.
4.  Paste your **Chat ID** into the "Chat ID" field.
5.  Click **Save Telegram**.

### Step 4: Test It
Open your new bot in Telegram and click **Start**. Try sending these commands:
*   `/status` - Get current gravity, temp, and ABV.
*   `/ping` - Check if the bot is online.
*   `/help` - See available commands.

---

## ⚖️ Calibration
If your Tilt hydrometer reading doesn't match your manual hydrometer reading, you can calibrate it here.

1.  Take a manual reading sample.
2.  Enter that number (e.g., `1.012`) into the **Calibrate Reading** field.
3.  Click **Set**.
4.  Brew-Brain will calculate the offset automatically and apply it to all future readings.

---

## ☁️ Brewfather Integration (Optional)
If you use Brewfather, you can sync data directly.
1.  In Brewfather, go to **Settings** -> **Power Controller & API**.
2.  Generate an API Key.
3.  Enter your **User ID** and **API Key** in Brew-Brain Settings.
4.  Click **Save Brewfather**.
