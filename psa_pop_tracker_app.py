# ✅ PSA Pop Tracker - Enhanced Production Version (Image Fix + Title + Grade Cache + Slab Links)

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
        for item in soup.find_all("li", class_="s-item"):
            price_tag = item.find("span", class_="s-item__price")
            img_tag = item.find("img", class_="s-item__image-img") or item.find("img")
            title_tag = item.find(class_="s-item__title")
            if not price_tag or not img_tag or not title_tag:
                continue
            title = title_tag.get_text(" ", strip=True)
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

def fetch_cgc_image(query):
    try:
        url = f"https://www.cgccards.com/population/?query={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag = soup.find("img")
        if img_tag:
            src = img_tag.get("src")
            if src and src.startswith("/"):
                return "https://www.cgccards.com" + src
            return src
    except:
        pass
    return None

def fetch_sgc_image():
    return "https://sgccard.com/images/logo.png"

def get_ebay_price_and_image(query):
    listings = search_ebay_listings(query, sold=True)
    if listings:
        avg = sum(l["price"] for l in listings) / len(listings)
        best = min(listings, key=lambda d: abs(d["price"] - avg))
        price = round(avg, 2)
        save_price_history(query, price)
        save_image_cache(query, best["img"])
        return price, len(listings), best["img"], best["title"]
    price_history = load_json_file(PRICE_HISTORY_FILE).get(query, {})
    price = price_history[sorted(price_history.keys())[-1]] if price_history else None
    img = load_image_cache(query)
    if not img:
        img = fetch_cgc_image(query)
    if not img:
        img = fetch_sgc_image()
    if img:
        save_image_cache(query, img)
    return price, 0, img, None

def scrape_psa_pop(query):
    try:
        resp = requests.get(f"https://www.psacard.com/pop?q={query}", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    grade = cols[1].text.strip()
                    count = cols[2].text.strip()
                    if grade[:2].isdigit():
                        pop_data[f"{grade}_PSA"] = int(count.replace(",", ""))
        return pop_data
    except:
        return {}

def scrape_cgc_pop(query):
    try:
        url = f"https://www.cgccards.com/population/?query={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[f"{grade}_CGC"] = int(count.replace(",", ""))
        return pop_data
    except:
        return {}

def scrape_sgc_pop(query):
    try:
        resp = requests.get("https://sgccard.com/PopulationReport.aspx", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[f"{grade}_SGC"] = int(count.replace(",", ""))
        return pop_data
    except:
        return {}

# ----------------- Charting -----------------
def plot_price_and_pop(card):
    price_data = load_json_file(PRICE_HISTORY_FILE)
    pop_data = load_json_file(POP_HISTORY_FILE)
    if card not in price_data or card not in pop_data:
        return
    price_df = pd.DataFrame.from_dict(price_data[card], orient="index", columns=["price"])
    pop_df = pd.DataFrame.from_dict(pop_data[card], orient="index")
    total_pop = pop_df.sum(axis=1).rename("population")
    df = pd.concat([price_df, total_pop], axis=1).dropna()
    df.index = pd.to_datetime(df.index)
    df = df.reset_index().rename(columns={"index": "date"})
    if df.empty:
        st.info("Not enough data for chart")
        return
    chart = alt.Chart(df).transform_fold(["price", "population"], as_=["type", "value"]).mark_line(point=True).encode(
        x="date:T", y="value:Q", color="type:N").properties(height=300)
    st.altair_chart(chart, use_container_width=True)

def plot_grade_distribution(pop_dict):
    rows = []
    for key, count in pop_dict.items():
        if "_" in key:
            grade, grader = key.split("_", 1)
            rows.append({"grade": grade, "grader": grader, "count": count})
    if not rows:
        return
    df = pd.DataFrame(rows)
    try:
        df["grade_num"] = df["grade"].str.extract(r"(\d+(?:\.\d+)?)").astype(float)
        df = df.sort_values("grade_num")
    except:
        pass
    chart = alt.Chart(df).mark_bar().encode(
        x="grade:N", y="count:Q", color="grader:N", tooltip=["grader", "grade", "count"]).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# ----------------- Interface -----------------
st.sidebar.header("⭐ Watchlist")
history = st.session_state.setdefault("history", [])
grade_cache = st.session_state.setdefault("grade_cache", {})

if history:
    st.sidebar.markdown("\n".join(f"- {card}" for card in history))
else:
    st.sidebar.info("No cards searched yet.")

center = st.columns([1, 2, 1])[1]
with center:
    query = st.text_input("Search card name")

if query:
    if query not in history:
        history.append(query)

    st.markdown(f"## 🔍 Results for: `{query}`")

    price, count, img, title = get_ebay_price_and_image(query)

    cols = st.columns([1, 2])
    with cols[0]:
        if img and img.startswith("http"):
            st.image(img, caption="🖼️ Card Image")
        else:
            st.warning("⚠️ Invalid or missing image URL.")

    with cols[1]:
        if title:
            st.markdown(f"**📝 Title:** {title}")
        if price is not None:
            if count:
                st.success(f"💵 Avg Sold Price: **${price}**  \n🔢 Based on **{count} listings**")
            else:
                st.info(f"💵 Cached eBay price: **${price}**")
        else:
            st.warning("❌ Price estimate unavailable.")

    st.markdown("### 📊 Population Summary Table")

    def get_cached_pop(query):
        if query in grade_cache:
            return grade_cache[query]
        psa = scrape_psa_pop(query)
        cgc = scrape_cgc_pop(query)
        sgc = scrape_sgc_pop(query)
        combined = {**psa, **cgc, **sgc}
        grade_cache[query] = combined
        return combined

    combined = get_cached_pop(query)
    if combined:
        save_pop_history(query, combined)
        df = pd.DataFrame.from_dict(combined, orient="index", columns=["Count"]).sort_index()
        st.dataframe(df, use_container_width=True)

        st.markdown("### 🔍 Slab Certification Lookup")
        st.markdown(f"- 🔗 [PSA Cert Lookup](https://www.psacard.com/cert/lookup?q={query})")
        st.markdown(f"- 🔗 [CGC Cert Lookup](https://www.cgccards.com/certlookup/?query={query})")
        st.markdown(f"- 🔗 [SGC Cert Lookup](https://sgccard.com/VerifyCard.aspx?CertNumber={query})")

        st.markdown("### 🏆 Grade Distribution by Grader")
        plot_grade_distribution(combined)
    else:
        st.warning("⚠️ Could not retrieve population data from graders.")

    st.markdown("### 📈 Combined Price and Population Chart")
    plot_price_and_pop(query)
