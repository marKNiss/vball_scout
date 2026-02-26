import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time
import re
import shutil

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vball Scout", page_icon="🏐", layout="wide")

# --- CUSTOM CSS STYLING ---
st.markdown("""
    <style>
    /* Main App Background - Dark Navy */
    .stApp {
        background-color: #0a192f; 
        color: #ffffff; 
    }
    
    /* Headings on the main background */
    h1, h2, h3, .stMarkdown p {
        color: #ffffff !important;
    }

    /* INPUT WIDGET STYLING */
    .stSelectbox > div > div, .stTextInput > div > div {
        background-color: #ffffff !important;
        color: #0a192f !important;
        border: 2px solid #00c8d7 !important;
        border-radius: 8px;
    }
    .stSelectbox [data-baseweb="select"] span, .stTextInput input {
       color: #0a192f !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #00c8d7 !important; 
        color: #ffffff !important; 
    }

    /* BUTTON STYLING */
    .stButton button {
        background-color: #ffffff !important;
        color: #0a192f !important;
        border: 2px solid #00c8d7 !important;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #00c8d7 !important; 
        color: #ffffff !important; 
        border-color: #ffffff !important;
    }

    /* DIVIDER STYLING */
    hr {
        border-color: #00c8d7 !important; 
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    /* PAGE LINK STYLING */
    .stPageLink a {
        background-color: #ffffff !important;
        color: #0a192f !important;
        border: 2px solid #00c8d7 !important;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏐 Vball Scout")
st.subheader("Match Setup")

# Team Directory - Stacked to prevent copy-paste truncation!
team_directory = {
    "WF Waves 17-Brandy": {
        "code": "G17WAVES1GC", 
        "age": "U17", 
        "region": "GC", 
        "search_name": "WF Waves 17-Brandy"
    },
    "WF Waves 13-Natalie": {
        "code": "G13WAVES2GC", 
        "age": "U13", 
        "region": "GC", 
        "search_name": "WF Waves 13-Natalie"
    }
}

# Input Section
with st.container(border=True):
    selected_team = st.selectbox("Select Your Team:", list(team_directory.keys()))
    team_data = team_directory[selected_team]

    data_source = st.radio("Select Data Source:", ["AES", "SportsWrench"], horizontal=True)
    pool_url = st.text_input("Post today's AES Pool/Bracket overview link:")

st.divider()

# Initialize memory state
if 'scraped_stats' not in st.session_state:
    st.session_state.scraped_stats = {}
if 'home_table' not in st.session_state:
    st.session_state.home_table = None
if 'opp_table' not in st.session_state:
    st.session_state.opp_table = None

# --- HELPER: SCRAPE LIVE POOL DATA ---
def scrape_pool_data(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    if shutil.which("chromium"):
        options.add_argument('--single-process') # ONLY run this on the cloud!
        options.binary_location = shutil.which("chromium")
        svc = Service(shutil.which("chromedriver"))
    else:
        svc = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=svc, options=options)
    temp_stats = {}

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "k-grid-table")))
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        for table in soup.find_all('table', class_='k-grid-table'):
            for row in table.find_all('tr'):
                cols = [c.text.strip().replace('‡', '').replace('†', '') for c in row.find_all('td') if c.text.strip()]
                if len(cols) >= 5:
                    team_name = next((c for c in cols if len(c) > 3 and not c.replace('%', '').replace('.', '').isdigit()), "")
                    digits = [c for c in cols if c.isdigit() or c == '-']
                    digits = ['0' if x == '-' else x for x in digits]

                    if team_name and len(digits) >= 4:
                        temp_stats[team_name] = {
                            "Pool (Match)": f"{digits[0]}-{digits[1]}",
                            "Pool (Set)": f"{digits[2]}-{digits[3]}"
                        }
    except Exception as e:
        print(f"Pool Scrape Error: {e}")
    finally:
        driver.quit()

    return temp_stats

# --- HELPER: SEARCH A SPECIFIC AES RANKINGS URL ---
def search_aes_database(driver, url, search_term):
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Team Name']"))
        )
        time.sleep(2)

        search_boxes = driver.find_elements(By.XPATH, "//input[@placeholder='Team Name']")
        for box in search_boxes:
            if box.is_displayed():
                box.click()
                box.clear()

                for char in search_term:
                    box.send_keys(char)
                    time.sleep(0.05)

                time.sleep(1)
                box.send_keys(Keys.RETURN)
                break

        time.sleep(4)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        first_word = search_term.split()[0].lower()

        potential_rows = soup.find_all(lambda tag: tag.name in ['tr', 'div'] and first_word in tag.text.lower())
        for row in potential_rows:
            cols = [t.strip() for t in row.stripped_strings if t.strip()]
            if len(cols) >= 5 and cols[0].isdigit():
                if first_word in row.text.lower():
                    return cols
    except Exception as e:
        print(f"URL Search Error: {e}")
    return None

# --- PHASE 2: LIVE RANKINGS ENGINE ---
def fetch_seasonal_rankings(driver, opponent_name, age_group, home_region=None):
    search_term = re.sub(r'\(.*?\)', '', opponent_name).strip()
    if '-' in search_term:
        search_term = search_term.split('-')[0].strip()

    usav_url = f"https://www.advancedeventsystems.com/rankings/Female/{age_group}/usav"
    usav_cols = search_aes_database(driver, usav_url, search_term)

    usav_rank = "N/A"
    usav_season_g = "N/A"
    if usav_cols:
        usav_rank = usav_cols[0]
        wins = usav_cols[2] if usav_cols[2].isdigit() else "0"
        losses = usav_cols[3] if usav_cols[3].isdigit() else "0"
        usav_season_g = f"{wins}-{losses}"

    aes_url = f"https://www.advancedeventsystems.com/rankings/Female/{age_group}/aes"
    aes_cols = search_aes_database(driver, aes_url, search_term)

    aes_rank = "N/A"
    aes_season_g = "N/A"
    if aes_cols:
        aes_rank = aes_cols[0]
        wins = aes_cols[2] if aes_cols[2].isdigit() else "0"
        losses = aes_cols[3] if aes_cols[3].isdigit() else "0"
        aes_season_g = f"{wins}-{losses}"

    region_rank = "N/A"
    region_code = None

    region_match = re.search(r'\(([A-Z]{2})\)', opponent_name)
    if region_match:
        region_code = region_match.group(1)
    elif home_region:
        region_code = home_region

    if region_code and aes_cols:
        try:
            region_select = Select(driver.find_element(By.NAME, "region"))
            for option in region_select.options:
                if f"({region_code})" in option.text or option.get_attribute("value") == region_code:
                    region_select.select_by_visible_text(option.text)
                    time.sleep(3)

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    first_word = search_term.split()[0].lower()

                    potential_rows = soup.find_all(lambda tag: tag.name in ['tr', 'div'] and first_word in tag.text.lower())
                    for row in potential_rows:
                        cols = [t.strip() for t in row.stripped_strings if t.strip()]
                        if len(cols) >= 5 and cols[0].isdigit():
                            if first_word in row.text.lower():
                                region_rank = cols[0]
                                break
                    break
        except Exception as e:
            print(f"Region rank fetch error for {opponent_name}: {e}")

    return {
        "USAV Season (G)": usav_season_g,
        "AES Season (G)": aes_season_g,
        "USAV Rank": usav_rank,
        "AES Rank": aes_rank,
        "Region Rank": region_rank
    }

# --- PHASE 1: PULL THE MASTER DIVISION LIST ---
if st.button("1. Load Tournament Data"):
    if not pool_url:
        st.warning("Please paste a pool link first.")
    elif data_source == "SportsWrench":
        st.info("🚧 SportsWrench integration is coming in the next update! Please select AES for now.")
    else:
        with st.spinner("Extracting and alphabetizing the division..."):
            temp_stats = scrape_pool_data(pool_url)

            if temp_stats:
                st.session_state.scraped_stats = temp_stats
                st.success(f"Successfully loaded and sorted {len(temp_stats)} teams!")
            else:
                st.error("⚠️ Couldn't find the team list. Check the link.")

# --- THE UI: SEARCH & GENERATE ---
if st.session_state.scraped_stats:
    st.write("### 🔍 Scout Opponents")
    sorted_team_names = sorted(list(st.session_state.scraped_stats.keys()))

    with st.container(border=True):
        selected_opponents = st.multiselect(
            "Search and select opponents to build your radar:",
            options=sorted_team_names,
            help="Type a team name to filter the list."
        )

    st.divider()

    if st.button("2. Run Vball Scout"):
        if not selected_opponents:
            st.warning("⚠️ Please select at least one team.")
        else:
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            total_teams = len(selected_opponents) + 1
            current_team_count = 0

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            if shutil.which("chromium"):
                options.add_argument('--single-process') # ONLY run this on the cloud!
                options.binary_location = shutil.which("chromium")
                svc = Service(shutil.which("chromedriver"))
            else:
                svc = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=svc, options=options)

            try:
                # 1. PROCESS OUR OWN TEAM
                status_text.markdown(f"**Scouting {selected_team}... (1 of {total_teams})**")
                
                our_live_stats = {"Pool (Match)": "0-0", "Pool (Set)": "0-0"}
                for scraped_name, stats in st.session_state.scraped_stats.items():
                    if team_data["code"].lower() in scraped_name.lower() or "waves" in scraped_name.lower():
                        our_live_stats = stats
                        break

                our_season_stats = fetch_seasonal_rankings(driver, team_data["search_name"], team_data["age"], team_data["region"])

                home_team_data = [{
                    "Team": selected_team,
                    "Pool (Match)": our_live_stats["Pool (Match)"],
                    "Pool (Set)": our_live_stats["Pool (Set)"],
                    "USAV Season (G)": our_season_stats["USAV Season (G)"],
                    "AES Season (G)": our_season_stats["AES Season (G)"],
                    "USAV Rank": our_season_stats["USAV Rank"],
                    "AES Rank": our_season_stats["AES Rank"],
                    "Region Rank": our_season_stats["Region Rank"]
                }]
                
                current_team_count += 1
                progress_bar.progress(current_team_count / total_teams)

                # 2. PROCESS OPPONENTS
                opponents_data = []
                for opp_name in selected_opponents:
                    current_team_count += 1
                    status_text.markdown(f"**Scouting {opp_name}... ({current_team_count} of {total_teams})**")
                    
                    live_stats = st.session_state.scraped_stats[opp_name]
                    seasonal = fetch_seasonal_rankings(driver, opp_name, team_data["age"])

                    opponents_data.append({
                        "Team": opp_name,
                        "Pool (Match)": live_stats["Pool (Match)"],
                        "Pool (Set)": live_stats["Pool (Set)"],
                        "USAV Season (G)": seasonal["USAV Season (G)"],
                        "AES Season (G)": seasonal["AES Season (G)"],
                        "USAV Rank": seasonal["USAV Rank"],
                        "AES Rank": seasonal["AES Rank"],
                        "Region Rank": seasonal["Region Rank"]
                    })
                    
                    progress_bar.progress(current_team_count / total_teams)

                cols = ["Team", "Pool (Match)", "Pool (Set)", "USAV Season (G)", "AES Season (G)", "USAV Rank", "AES Rank", "Region Rank"]

                st.session_state.home_table = pd.DataFrame(home_team_data)[cols]
                st.session_state.opp_table = pd.DataFrame(opponents_data)[cols]
                
                status_text.success("Scouting Complete!")

            except Exception as e:
                st.error(f"Engine interrupted: {e}")
            finally:
                driver.quit()

# --- HTML CARD GENERATOR FUNCTION ---
def render_scout_card(row):
    html_lines = [
        "<div style='border: 2px solid #00c8d7; border-radius: 10px; padding: 12px; background-color: #112240; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>",
        f"<h4 style='color: #ffffff; margin-top: 0px; margin-bottom: 10px; font-size: 1.1rem; font-weight: bold;'>{row['Team']}</h4>",
        "<div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>",
        "<div style='line-height: 1.1;'>",
        "<span style='color: #00c8d7; font-size: 0.75rem; font-weight: 600;'>Pool (Match)</span><br>",
        f"<span style='color: #ffffff; font-size: 0.95rem; font-weight: bold;'>{row['Pool (Match)']}</span>",
        "</div>",
        "<div style='line-height: 1.1;'>",
        "<span style='color: #00c8d7; font-size: 0.75rem; font-weight: 600;'>Pool (Set)</span><br>",
        f"<span style='color: #ffffff; font-size: 0.95rem; font-weight: bold;'>{row['Pool (Set)']}</span>",
        "</div>",
        "<div style='line-height: 1.1;'>",
        "<span style='color: #00c8d7; font-size: 0.75rem; font-weight: 600;'>Region Rank</span><br>",
        f"<span style='color: #ffffff; font-size: 0.95rem; font-weight: bold;'>#{row['Region Rank']}</span>",
        "</div>",
        "</div>",
        "<div style='display: flex; justify-content: space-between;'>",
        "<div style='line-height: 1.1;'>",
        "<span style='color: #00c8d7; font-size: 0.75rem; font-weight: 600;'>USAV Rank</span><br>",
        f"<span style='color: #ffffff; font-size: 0.95rem; font-weight: bold;'>#{row['USAV Rank']} ({row['USAV Season (G)']})</span>",
        "</div>",
        "<div style='line-height: 1.1;'>",
        "<span style='color: #00c8d7; font-size: 0.75rem; font-weight: 600;'>AES Rank</span><br>",
        f"<span style='color: #ffffff; font-size: 0.95rem; font-weight: bold;'>#{row['AES Rank']} ({row['AES Season (G)']})</span>",
        "</div>",
        "</div>",
        "</div>"
    ]
    card_html = "".join(html_lines)
    st.markdown(card_html, unsafe_allow_html=True)

# ALWAYS DISPLAY CARDS IF THEY EXIST IN MEMORY
if st.session_state.home_table is not None and st.session_state.opp_table is not None:

    # --- REFRESH BUTTON ---
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Live Scores"):
            if pool_url:
                with st.spinner("Fetching latest pool results..."):
                    fresh_stats = scrape_pool_data(pool_url)

                    if fresh_stats:
                        for scraped_name, stats in fresh_stats.items():
                            if team_data["code"].lower() in scraped_name.lower() or "waves" in scraped_name.lower():
                                st.session_state.home_table.at[0, 'Pool (Match)'] = stats['Pool (Match)']
                                st.session_state.home_table.at[0, 'Pool (Set)'] = stats['Pool (Set)']
                                break

                        for index, row in st.session_state.opp_table.iterrows():
                            opp_name = row['Team']
                            if opp_name in fresh_stats:
                                st.session_state.opp_table.at[index, 'Pool (Match)'] = fresh_stats[opp_name]['Pool (Match)']
                                st.session_state.opp_table.at[index, 'Pool (Set)'] = fresh_stats[opp_name]['Pool (Set)']

                        st.rerun()
            else:
                st.warning("Please enter a valid pool link at the top to refresh.")

    # --- RENDER COMPACT MOBILE CARDS ---
    st.write(f"### 🌊 {selected_team}")
    for index, row in st.session_state.home_table.iterrows():
        render_scout_card(row)

    st.write("### 🛡️ Opponents")
    for index, row in st.session_state.opp_table.iterrows():
        render_scout_card(row)

st.divider()
st.page_link("pages/1_Region_Rankings.py", label="View Region Power Rankings", icon="🌎")