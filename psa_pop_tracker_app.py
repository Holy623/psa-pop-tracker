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

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
WATCHLIST_FILE = "watchlist.json"
NOTIFY_LOG = "pop_notify.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"

# ----- Pop & Price History -----

def load_json_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def flatten_grade_data(grade_data):
    flat = {}
    for grade, companies in grade_data.items():
        for company, value in companies.items():
            flat[f"{grade}_{company}"] = value
    return flat

def save_pop_history(card, data):
    history = load_json_file(POP_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history: history[card] = {}
    history[card][today] = flatten_grade_data(data)
    save_json_file(POP_HISTORY_FILE, history)

def save_price_history(card, price):
    history = load_json_file(PRICE_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history: history[card] = {}
    history[card][today] = price
    save_json_file(PRICE_HISTORY_FILE, history)

def plot_price_history(card):
    hist = load_json_file(PRICE_HISTORY_FILE)
    if card in hist:
        df = pd.DataFrame.from_dict(hist[card], orient="index", columns=["eBay Price"])
        df.index = pd.to_datetime(df.index)
        st.line_chart(df)

def plot_pop_history(card):
    hist = load_json_file(POP_HISTORY_FILE)
    if card in hist:
        df = pd.DataFrame(hist[card]).T.sort_index()
        st.line_chart(df)

def check_for_pop_changes():
    hist = load_json_file(POP_HISTORY_FILE)
    last_log = load_json_file(NOTIFY_LOG)
    out = []
    for card, records in hist.items():
        dates = sorted(records.keys())
        if len(dates) >= 2:
            prev, latest = dates[-2], dates[-1]
            for k in records[latest]:
                if records[latest][k] != records[prev].get(k):
                    out.append(f"{card}: {k} changed from {records[prev].get(k)} → {records[latest][k]}")
    if out:
        st.sidebar.subheader("🔔 Pop Changes Since Last Check")
        for line in out:
            st.sidebar.write(line)
    save_json_file(NOTIFY_LOG, hist)

# ----- Scrapers -----

def scrape_psa_pop(query):
    url = f"https://www.psacard.com/pop?q={query}"
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag = soup.find("img", {"class": "pop-report-card-image"})
        img_url = img_tag["src"] if img_tag else None
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    grade = cols[1].text.strip()
                    count = cols[2].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count
        return {"grades": pop_data, "image": img_url}
    except:
        return {}

def scrape_cgc_pop(query):
    try:
        url = f"https://www.cgccards.com/population/?query={query.replace(' ', '+')}"
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count
        return pop_data
    except:
        return {}

def scrape_sgc_pop(query):
    try:
        url = "https://sgccard.com/PopulationReport.aspx"
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count
        return pop_data
    except:
        return {}

def fetch_external_card_image(query):
    try:
        resp = requests.get(EBAY_IMAGE_URL.format(query.replace(" ", "+")))
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("img")
        return tag["src"] if tag and "src" in tag.attrs else None
    except:
        return None

def fetch_ebay_price(query):
    try:
        resp = requests.get(EBAY_IMAGE_URL.format(query.replace(" ", "+")))
        soup = BeautifulSoup(resp.text, "html.parser")
        prices = []
        for item in soup.find_all("li", class_="s-item"):
            price_tag = item.find("span", class_="s-item__price")
            if price_tag:
                raw = price_tag.text.replace("$", "").replace(",", "").split(" ")[0]
                try: prices.append(float(raw))
                except: continue
        if prices:
            return round(sum(prices)/len(prices), 2), len(prices)
        return None, 0
    except:
        return None, 0

# ----- UI -----

st.set_page_config(page_title="PSA Pop + eBay Tracker", layout="wide")
st.title("📈 PSA Pop + eBay Tracker")

watchlist = load_json_file(WATCHLIST_FILE)
st.sidebar.header("⭐ Watchlist")
if watchlist:
    for card in watchlist:
        st.sidebar.write("• " + card)
add_card = st.sidebar.text_input("Add to watchlist")
if add_card and add_card not in watchlist:
    watchlist.append(add_card)
    save_json_file(WATCHLIST_FILE, watchlist)
    st.experimental_rerun()

check_for_pop_changes()

query = st.text_input("🔍 Search card(s)", value=", ".join(watchlist))
if query:
    for card in [q.strip() for q in query.split(",") if q.strip()]:
        st.markdown(f"## 🃏 {card}")
        psa = scrape_psa_pop(card)
        cgc = scrape_cgc_pop(card)
        sgc = scrape_sgc_pop(card)

        if psa.get("image"):
            st.image(psa["image"], caption="PSA Image")
        else:
            fallback = fetch_external_card_image(card)
            if fallback:
                st.image(fallback, caption="eBay Preview")

        st.markdown(f"[🔗 View on eBay]({EBAY_IMAGE_URL.format(card.replace(' ', '+'))})")

        # Pop Table
        st.subheader("📊 Population Breakdown")
        grades = defaultdict(lambda: {"PSA": 0, "CGC": 0, "SGC": 0})
        if "grades" in psa:
            for g, v in psa["grades"].items():
                grades[g]["PSA"] = int(v.replace(",", "")) if v.replace(",", "").isdigit() else 0
        for g, v in cgc.items():
            grades[g]["CGC"] = int(v.replace(",", "")) if v.replace(",", "").isdigit() else 0
        for g, v in sgc.items():
            grades[g]["SGC"] = int(v.replace(",", "")) if v.replace(",", "").isdigit() else 0

        if grades:
            df = pd.DataFrame.from_dict(grades, orient="index").fillna(0).astype(int).sort_index()
            st.dataframe(df)
            save_pop_history(card, grades)

        # Price Estimate
        st.subheader("💵 eBay Market Estimate")
        price, count = fetch_ebay_price(card)
        if price:
            save_price_history(card, price)
            st.success(f"Avg: ${price} from {count} listings")
            plot_price_history(card)
        else:
            st.warning("No price data found.")

        # Pop History Chart
        st.subheader("📈 Population History")
        plot_pop_history(card)
