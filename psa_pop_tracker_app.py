# 🧠 PSA Pop Tracker UI Initialization

import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import matplotlib.pyplot as plt
import json
from datetime import datetime
import pandas as pd
from collections import defaultdict
import altair as alt

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
WATCHLIST_FILE = "watchlist.json"
NOTIFY_LOG = "pop_notify.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"

st.set_page_config(page_title="🃏 PSA Pop Tracker", layout="wide")
st.title("🃏 PSA Pop + eBay Card Tracker")

# Placeholder: assume the rest of the application logic is defined below
def load_json_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def display_dashboard_summary():
    history = load_json_file(POP_HISTORY_FILE)
    if not history:
        return
    total_latest = {}
    growth_rates = {}
    for card, records in history.items():
        dates = sorted(records.keys())
        if len(dates) >= 2:
            prev, last = dates[-2], dates[-1]
            prev_total = sum(records[prev].values())
            last_total = sum(records[last].values())
            growth = ((last_total - prev_total) / prev_total) * 100 if prev_total > 0 else 0
            growth_rates[card] = round(growth, 2)
        latest_total = sum(records[dates[-1]].values())
        total_latest[card] = latest_total

    top_pop = sorted(total_latest.items(), key=lambda x: x[1], reverse=True)[:5]
    top_growth = sorted(growth_rates.items(), key=lambda x: x[1], reverse=True)[:5]

    st.markdown("## 🔝 Most Graded Cards (Top 5)")
    for card, pop in top_pop:
        st.markdown(f"• **{card}**: {pop} total graded")

    if top_growth:
        st.markdown("## 🚀 Fastest Growing (by % pop growth)")
        for card, pct in top_growth:
            st.markdown(f"• **{card}**: {pct}% growth")

display_dashboard_summary()
