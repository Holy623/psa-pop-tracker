# ✅ PSA Pop Tracker - Final Production Version

"""Streamlit application for tracking trading card populations and prices.

The app searches eBay sold listings for card images and recent sale prices,
scrapes population reports from grading companies (PSA, CGC and SGC) and
persists the information in JSON files. To avoid mismatched images, the photo
displayed is taken from the sold listing closest to the average sale price.
Price and population history for a card is displayed on an Altair line chart.
Search history is shown in the sidebar as a simple watchlist.
"""

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
st.markdown(
    f"<h1 style='text-align:center;'>{APP_NAME}</h1>",
    unsafe_allow_html=True,
)

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"
# Completed listings show actual sale prices
EBAY_SOLD_URL = (
    "https://www.ebay.com/sch/i.html?_nkw={}&LH_Complete=1&LH_Sold=1"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PSA Pop Tracker/1.0)"}

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

# ----------------- Scraping -----------------
def search_ebay_listings(query, sold=True):
    """Return a list of price/image pairs from an eBay search.

    If ``sold`` is True, query completed listings so prices reflect actual
    sales.
    """
    try:
        url = EBAY_SOLD_URL if sold else EBAY_IMAGE_URL
        resp = requests.get(url.format(query.replace(" ", "+")), headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = []
        for item in soup.find_all("li", class_="s-item"):
            price_tag = item.find("span", class_="s-item__price")
            img_tag = item.find("img", class_="s-item__image-img")
            title_tag = item.find(class_="s-item__title")
            if not price_tag or not img_tag or not title_tag:
                continue
            title = title_tag.get_text(" ", strip=True)
            if not title or title == "New Listing":
                continue
            if not all(word.lower() in title.lower() for word in query.split()):
                continue
            img_url = img_tag.get("src") or img_tag.get("data-src")
            if not img_url:
                continue
            text = price_tag.get_text(" ")
            m = re.search(r"\$([0-9,.]+)", text)
            if not m:
                continue
            try:
                price = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            listings.append({"price": price, "img": img_url, "title": title})
        return listings
    except requests.exceptions.RequestException:
        return []


def fetch_external_card_image(query):
    """Return an image from a sold listing closest to the average price."""
    try:
        listings = search_ebay_listings(query, sold=True)
        if not listings:
            return None
        avg = sum(l["price"] for l in listings) / len(listings)
        best = min(listings, key=lambda d: abs(d["price"] - avg))
        return best["img"]
    except requests.exceptions.RequestException:
        return None

def fetch_ebay_price(query):
    """Return average sold price and listing count from eBay."""
    try:
        listings = search_ebay_listings(query, sold=True)
        if not listings:
            return None, 0
        prices = [l["price"] for l in listings]
        avg = round(sum(prices) / len(prices), 2)
        return avg, len(prices)
    except requests.exceptions.RequestException:
        return None, 0

def scrape_psa_pop(query):
    """Scrape population data from PSA's population report."""
    try:
        resp = requests.get(
            f"https://www.psacard.com/pop?q={query}", headers=HEADERS
        )
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
    except Exception:
        return {}

def scrape_cgc_pop(query):
    """Scrape population data from CGC."""
    try:
        url = f"https://www.cgccards.com/population/?query={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS)
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
    except Exception:
        return {}

def scrape_sgc_pop(query):
    """Scrape population data from SGC."""
    try:
        resp = requests.get(
            "https://sgccard.com/PopulationReport.aspx", headers=HEADERS
        )
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
    except Exception:
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
    chart = (
        alt.Chart(df)
        .transform_fold(["price", "population"], as_=["type", "value"])
        .mark_line(point=True)
        .encode(x="date:T", y="value:Q", color="type:N")
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def plot_grade_distribution(pop_dict):
    """Show a bar chart of population counts by grade and grader."""
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
    except Exception:
        pass
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x="grade:N",
            y="count:Q",
            color="grader:N",
            tooltip=["grader", "grade", "count"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

# ----------------- Streamlit Interface -----------------
st.sidebar.header("⭐ Watchlist")

# Keep a history of searched cards in the user's session
history = st.session_state.setdefault("history", [])
if history:
    st.sidebar.markdown("\n".join(f"- {card}" for card in history))
else:
    st.sidebar.info("No cards searched yet.")

# Place the search input in the center of the page
center = st.columns([1, 2, 1])[1]
with center:
    query = st.text_input("Search card name")

if query:
    # Record the search in the sidebar history
    if query not in history:
        history.append(query)

    st.markdown(f"### 🔍 Results for: `{query}`")
    price, count = fetch_ebay_price(query)
    img = fetch_external_card_image(query)

    if img:
        if price:
            st.image(img, caption=f"eBay sold listing near average price (${price})")
        else:
            st.image(img, caption="eBay sold listing near average price")
    else:
        st.warning("Could not fetch card image from eBay.")

    if price:
        st.success(
            f"💵 Average eBay sold price: ${price} (based on {count} listings)"
        )
        save_price_history(query, price)
    else:
        st.warning("Price estimate unavailable.")

    st.markdown("### 📊 Population Summary Table")
    psa_pop = scrape_psa_pop(query)
    cgc_pop = scrape_cgc_pop(query)
    sgc_pop = scrape_sgc_pop(query)
    combined = {**psa_pop, **cgc_pop, **sgc_pop}
    if combined:
        save_pop_history(query, combined)
        df = pd.DataFrame.from_dict(combined, orient="index", columns=["Count"]).sort_index()
        st.dataframe(df, use_container_width=True)
        st.markdown("### 🏆 Grade Distribution by Grader")
        plot_grade_distribution(combined)
    else:
        st.warning("⚠️ Could not retrieve population data from graders.")

    st.markdown("### 📈 Combined Price and Population Chart")
    plot_price_and_pop(query)
