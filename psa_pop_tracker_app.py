# ✅ PSA Pop Tracker - Enhanced Production Version (Image Fix + Title + Grade Cache + Slab Links + Match Filtering + Avg Price + Last 10 Sales)

import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import pandas as pd
import altair as alt
import re

# ----------------- Config -----------------
APP_NAME = "🃏 PSA Pop Tracker"
st.set_page_config(page_title=APP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align:center;'>{APP_NAME}</h1>", unsafe_allow_html=True)

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
IMAGE_CACHE_FILE = "image_cache.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PSA Pop Tracker/1.0)"}
REQUEST_TIMEOUT = 10

# ----------------- Utilities -----------------
def load_json_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def save_price_history(card, price):
    history = load_json_file(PRICE_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history:
        history[card] = {}
    history[card][today] = price
    save_json_file(PRICE_HISTORY_FILE, history)

def save_pop_history(card, pop):
    history = load_json_file(POP_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history:
        history[card] = {}
    history[card][today] = pop
    save_json_file(POP_HISTORY_FILE, history)

def save_image_cache(card, img):
    cache = load_json_file(IMAGE_CACHE_FILE)
    cache[card] = img
    save_json_file(IMAGE_CACHE_FILE, cache)

def load_image_cache(card):
    cache = load_json_file(IMAGE_CACHE_FILE)
    return cache.get(card)

def parse_price(text: str):
    m = re.search(r"([0-9][0-9,.]*)", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None

# ----------------- Scraping -----------------
def search_ebay_listings(query, sold=True):
    try:
        url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}&LH_Complete=1&LH_Sold=1" if sold else f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = []
        query_words = [w.lower() for w in query.split() if w]
        for item in soup.find_all("li", class_="s-item"):
            price_tag = item.find("span", class_="s-item__price")
            img_tag = item.find("img", class_="s-item__image-img") or item.find("img")
            title_tag = item.find(class_="s-item__title")
            if not price_tag or not img_tag or not title_tag:
                continue
            title = title_tag.get_text(" ", strip=True)
            title_lower = title.lower()
            if any(w not in title_lower for w in query_words):
                continue
            img_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-image-src")
            price = parse_price(price_tag.get_text(" "))
            if not img_url or price is None:
                continue
            listings.append({"price": price, "img": img_url, "title": title})
        if sold and not listings:
            return search_ebay_listings(query, sold=False)
        return listings
    except:
        return []

def get_ebay_price_and_image(query):
    listings = search_ebay_listings(query, sold=True)
    if listings:
        prices = [l["price"] for l in listings]
        median_price = sorted(prices)[len(prices)//2]
        best = min(listings, key=lambda d: abs(d["price"] - median_price))
        avg = sum(prices) / len(prices)
        price = round(avg, 2)
        save_price_history(query, price)
        save_image_cache(query, best["img"])
        return price, len(listings), best["img"], best["title"], listings[:10]
    price_history = load_json_file(PRICE_HISTORY_FILE).get(query, {})
    price = price_history[sorted(price_history.keys())[-1]] if price_history else None
    img = load_image_cache(query)
    return price, 0, img, None, []
