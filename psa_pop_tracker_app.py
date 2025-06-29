# 🧠 PSA Pop Tracker UI Initialization

st.set_page_config(page_title="🃏 PSA Pop Tracker", layout="wide")
st.title("🃏 PSA Pop + eBay Card Tracker")
display_dashboard_summary()

# FULL STREAMLIT APP CONTINUES BELOW

import requests
from bs4 import BeautifulSoup
import pandas as pd
import altair as alt
from collections import defaultdict

POP_HISTORY_FILE = "pop_history.json"
PRICE_HISTORY_FILE = "price_history.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"

st.sidebar.header("⭐ Watchlist")
query = st.sidebar.text_input("Search card name")

# Load functions

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
            tag = item.find("span", class_="s-item__price")
            if tag:
                price = tag.text.replace("$", "").replace(",", "").split(" ")[0]
                try:
                    prices.append(float(price))
                except:
                    continue
        if prices:
            return round(sum(prices) / len(prices), 2), len(prices)
        return None, 0
    except:
        return None, 0

# Additional utility functions

def save_price_history(card, price):
    history = load_json_file(PRICE_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history:
        history[card] = {}
    history[card][today] = price
    with open(PRICE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def save_pop_history(card, pop):
    history = load_json_file(POP_HISTORY_FILE)
    today = datetime.today().strftime("%Y-%m-%d")
    if card not in history:
        history[card] = {}
    history[card][today] = pop
    with open(POP_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

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
    chart = alt.Chart(df).transform_fold(
        ["price", "population"], as_=["type", "value"]
    ).mark_line(point=True).encode(
        x="date:T",
        y="value:Q",
        color="type:N"
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# --------------------- Scraping Functions ---------------------

def scrape_psa_pop(query):
    try:
        resp = requests.get(f"https://www.psacard.com/pop?q={query}")
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
                        pop_data[f"{grade}_CGC"] = int(count.replace(",", ""))
        return pop_data
    except:
        return {}

def scrape_sgc_pop(query):
    try:
        resp = requests.get("https://sgccard.com/PopulationReport.aspx")
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

# Render results
from datetime import datetime
import json

if query:
    st.markdown(f"### 🔍 Results for: `{query}`")

    img = fetch_external_card_image(query)
    if img:
        st.image(img, caption="eBay Preview")

    price, count = fetch_ebay_price(query)
    if price:
        st.success(f"💵 eBay Price Estimate: ${price} (based on {count} listings)")

        st.markdown("### 📊 Population Summary Table")

    psa_pop = scrape_psa_pop(query)
    cgc_pop = scrape_cgc_pop(query)
    sgc_pop = scrape_sgc_pop(query)
    combined = {**psa_pop, **cgc_pop, **sgc_pop}

    if combined:
        save_pop_history(query, combined)
        st.success("✅ Population data saved from PSA, CGC, and SGC.")
        df = pd.DataFrame.from_dict(combined, orient="index", columns=["Count"]).sort_index()
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ Could not retrieve population data from graders.")
    if price:
        save_price_history(query, price)
        st.markdown("### 📈 Combined Price and Population Chart")
        plot_price_and_pop(query)")

    # Live PSA/CGC/SGC scraping

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
                            pop_data[f"{grade}_CGC"] = int(count.replace(",", ""))
            return pop_data
        except:
            return {}

    def scrape_sgc_pop(query):
        try:
            resp = requests.get("https://sgccard.com/PopulationReport.aspx")
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

    # PSA scrape logic
    def scrape_psa_pop(query):
        try:
            resp = requests.get(f"https://www.psacard.com/pop?q={query}")
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

        psa_pop = scrape_psa_pop(query)
    cgc_pop = scrape_cgc_pop(query)
    sgc_pop = scrape_sgc_pop(query)
    combined = {**psa_pop, **cgc_pop, **sgc_pop}
    if combined:
        save_pop_history(query, combined)
        st.success("✅ Population data saved from PSA, CGC, and SGC.")
    else:
        st.warning("⚠️ Could not retrieve population data from graders.")
    else:
        st.warning("⚠️ Could not retrieve PSA population data.")

    st.markdown("### 📈 Combined Price and Population Chart")
    plot_price_and_pop(query)

# --------------------- Dashboard Summary ---------------------

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
