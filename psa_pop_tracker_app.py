 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/psa_pop_tracker_app.py b/psa_pop_tracker_app.py
index adbe752e21929f9cdeaa60c8bfab6709a1c3df34..a2b4744c4e4662cc8cdb4d67e2e51ae7e1b9f0e7 100644
--- a/psa_pop_tracker_app.py
+++ b/psa_pop_tracker_app.py
@@ -1,178 +1,206 @@
 # ✅ PSA Pop Tracker - Final Production Version
 
 import streamlit as st
 import requests
 from bs4 import BeautifulSoup
 import os
 import json
 from datetime import datetime
 import pandas as pd
 from collections import defaultdict
 import altair as alt
 
 # ----------------- Config -----------------
-st.set_page_config(page_title="🃏 PSA Pop Tracker", layout="wide")
-st.title("🃏 PSA Pop + eBay Card Tracker")
+APP_NAME = "🃏 PSA Pop Tracker"
+st.set_page_config(page_title=APP_NAME, layout="wide")
+st.markdown(f"<h1 style='text-align:center;'>{APP_NAME}</h1>", unsafe_allow_html=True)
 
 POP_HISTORY_FILE = "pop_history.json"
 PRICE_HISTORY_FILE = "price_history.json"
 EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"
+HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PSA Pop Tracker/1.0)"}
 
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
 def fetch_external_card_image(query):
     try:
-        resp = requests.get(EBAY_IMAGE_URL.format(query.replace(" ", "+")))
+        resp = requests.get(
+            EBAY_IMAGE_URL.format(query.replace(" ", "+")), headers=HEADERS
+        )
         soup = BeautifulSoup(resp.text, "html.parser")
         tag = soup.find("img")
         return tag["src"] if tag and "src" in tag.attrs else None
     except:
         return None
 
 def fetch_ebay_price(query):
     try:
-        resp = requests.get(EBAY_IMAGE_URL.format(query.replace(" ", "+")))
+        resp = requests.get(
+            EBAY_IMAGE_URL.format(query.replace(" ", "+")), headers=HEADERS
+        )
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
 
 def scrape_psa_pop(query):
     try:
-        resp = requests.get(f"https://www.psacard.com/pop?q={query}")
+        resp = requests.get(
+            f"https://www.psacard.com/pop?q={query}", headers=HEADERS
+        )
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
-        resp = requests.get(url)
+        resp = requests.get(url, headers=HEADERS)
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
-        resp = requests.get("https://sgccard.com/PopulationReport.aspx")
+        resp = requests.get(
+            "https://sgccard.com/PopulationReport.aspx", headers=HEADERS
+        )
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
-    chart = alt.Chart(df).transform_fold(
-        ["price", "population"], as_=["type", "value"]
-    ).mark_line(point=True).encode(
-        x="date:T",
-        y="value:Q",
-        color="type:N"
-    ).properties(height=300)
+    if df.empty:
+        st.info("Not enough data for chart")
+        return
+    chart = (
+        alt.Chart(df)
+        .transform_fold(["price", "population"], as_=["type", "value"])
+        .mark_line(point=True)
+        .encode(x="date:T", y="value:Q", color="type:N")
+        .properties(height=300)
+    )
     st.altair_chart(chart, use_container_width=True)
 
 # ----------------- Streamlit Interface -----------------
 st.sidebar.header("⭐ Watchlist")
-query = st.sidebar.text_input("Search card name")
+
+# Keep a history of searched cards in the user's session
+history = st.session_state.setdefault("history", [])
+if history:
+    st.sidebar.markdown("\n".join(f"- {card}" for card in history))
+else:
+    st.sidebar.info("No cards searched yet.")
+
+# Place the search input in the center of the page
+center = st.columns([1,2,1])[1]
+with center:
+    query = st.text_input("Search card name")
 
 if query:
+    # Record the search in the sidebar history
+    if query not in history:
+        history.append(query)
+
     st.markdown(f"### 🔍 Results for: `{query}`")
     img = fetch_external_card_image(query)
     if img:
         st.image(img, caption="eBay Preview")
 
     price, count = fetch_ebay_price(query)
     if price:
         st.success(f"💵 eBay Price Estimate: ${price} (based on {count} listings)")
         save_price_history(query, price)
 
     st.markdown("### 📊 Population Summary Table")
     psa_pop = scrape_psa_pop(query)
     cgc_pop = scrape_cgc_pop(query)
     sgc_pop = scrape_sgc_pop(query)
     combined = {**psa_pop, **cgc_pop, **sgc_pop}
     if combined:
         save_pop_history(query, combined)
         df = pd.DataFrame.from_dict(combined, orient="index", columns=["Count"]).sort_index()
         st.dataframe(df, use_container_width=True)
     else:
         st.warning("⚠️ Could not retrieve population data from graders.")
 
     st.markdown("### 📈 Combined Price and Population Chart")
     plot_price_and_pop(query)
 
EOF
)
