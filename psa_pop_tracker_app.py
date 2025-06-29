# psa_pop_tracker_app.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import matplotlib.pyplot as plt
import json
from datetime import datetime
import pandas as pd
from collections import defaultdict
from difflib import get_close_matches

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
WATCHLIST_FILE = "watchlist.json"
NOTIFY_LOG = "pop_notify.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"

# ------------------- Pop History & Notification -------------------

def load_pop_history():
    if os.path.exists(POP_HISTORY_FILE):
        with open(POP_HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def flatten_grade_data(grade_data):
    flat_data = {}
    for grade, companies in grade_data.items():
        for company, value in companies.items():
            flat_data[f"{grade}_{company}"] = value
    return flat_data

def save_pop_history(query, grade_data):
    history = load_pop_history()
    date = datetime.today().strftime("%Y-%m-%d")
    if query not in history:
        history[query] = {}
    history[query][date] = flatten_grade_data(grade_data)
    with open(POP_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def plot_pop_history(query):
    history = load_pop_history()
    if query not in history:
        return
    df = pd.DataFrame(history[query]).T.sort_index()
    st.line_chart(df)

def check_for_pop_changes():
    history = load_pop_history()
    if not os.path.exists(NOTIFY_LOG):
        with open(NOTIFY_LOG, "w") as f:
            json.dump({}, f)
    with open(NOTIFY_LOG, "r") as f:
        log = json.load(f)
    today = datetime.today().strftime("%Y-%m-%d")
    notifications = []
    for card, records in history.items():
        dates = sorted(records.keys())
        if len(dates) >= 2:
            last, prev = dates[-1], dates[-2]
            for key in records[last]:
                v_new = records[last][key]
                v_old = records[prev].get(key, v_new)
                if v_new != v_old:
                    notifications.append(f"📈 {card}: {key} changed from {v_old} → {v_new}")
    if notifications:
        st.sidebar.subheader("🔔 Population Changes Since Last Check")
        for note in notifications:
            st.sidebar.write(note)
    with open(NOTIFY_LOG, "w") as f:
        json.dump(history, f)

# NOTE: The rest of the core UI, scraping functions, and main app loop must also be included below this.
# This is the foundational backend logic portion. To complete the full app, append it with your latest interface/UI blocks.

