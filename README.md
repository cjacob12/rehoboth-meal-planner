# Vacation Meal Planner

Family vacation meal planner for July 5–11, 2026. Built with Streamlit.

## Features

- Log in with your name to claim dishes
- Plan meals for each day (Breakfast, Lunch, Dinner)
- Search the web for recipes and add them directly
- See the full week at a glance with a summary dashboard
- Data persists in a local JSON file

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`. Share the URL on your local network so others can access it from their devices.

### Access from other devices on the same network

1. Find your machine's local IP: `ipconfig` (Windows) or `ifconfig` / `ip addr` (Mac/Linux)
2. Others can visit `http://<your-ip>:8501` from their phones or computers

## Data

Meal plan data is stored in `meal_plan.json` in the app directory. Delete this file to reset.
