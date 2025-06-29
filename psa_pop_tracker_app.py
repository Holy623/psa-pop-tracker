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
WATCHLIST_FILE = "watchlist.json"
NOTIFY_LOG = "pop_notify.json"
EBAY_IMAGE_URL = "https://www.ebay.com/sch/i.html?_nkw={}"

# Existing pop history, watchlist, and notification functions remain unchanged...

# PSA scraping logic

def scrape_psa_pop(query):
    url = f"https://www.psacard.com/pop?q={query}"
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        img_tag = soup.find("img", {"class": "pop-report-card-image"})
        img_url = img_tag['src'] if img_tag else None

        pop_data = {}
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    grade = cols[1].text.strip()
                    count = cols[2].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count

        return {"grades": pop_data, "image": img_url}
    except Exception as e:
        return {"Scrape Error": str(e)}

# eBay image fallback

def fetch_external_card_image(query):
    try:
        url = EBAY_IMAGE_URL.format(query.replace(" ", "+"))
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag = soup.find("img")
        return img_tag["src"] if img_tag and "src" in img_tag.attrs else None
    except:
        return None

# CGC scraping logic

def scrape_cgc_pop(query):
    url = f"https://www.cgccards.com/population/?query={query.replace(' ', '+')}"
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count
        return pop_data
    except Exception as e:
        return {"CGC Error": str(e)}

# SGC scraping logic

def scrape_sgc_pop(query):
    url = "https://sgccard.com/PopulationReport.aspx"
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        pop_data = {}
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    grade = cols[0].text.strip()
                    count = cols[1].text.strip()
                    if grade[:2].isdigit():
                        pop_data[grade] = count
        return pop_data
    except Exception as e:
        return {"SGC Error": str(e)}
