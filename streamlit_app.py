import streamlit as st
import json
import base64
from datetime import date, timedelta
from pathlib import Path
from collections import OrderedDict

st.set_page_config(
    page_title="Jacob Family Rehoboth Trip - Meal Planner",
    page_icon="\U0001f3d6\ufe0f",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "meal_plan.json"
IMAGE_FILE = APP_DIR / "rehoboth.png"

MEMBERS = ["Christa", "Mike", "Nancy", "Dave", "Ling Ling", "Lauren"]
ALLERGY_NOTE = "Shellfish allergy — plan alt protein for shared meals"
START_DATE = date(2026, 7, 5)
END_DATE = date(2026, 7, 11)
DAYS = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
MEALS = ["Breakfast", "Lunch", "Dinner"]
MEAL_STYLES = ["Home", "Out", "Leftovers", "Flexible"]
MEAL_ICONS = {"Home": "\U0001f3e0", "Out": "\U0001f37d\ufe0f", "Leftovers": "\U0001f4e6", "Flexible": "\U0001f937"}
MEAL_TYPE_ICONS = {"Breakfast": "\u2600\ufe0f", "Lunch": "\U0001f334", "Dinner": "\U0001f305"}
COOK_COLORS = {
    "Christa": "#2d9bb0",
    "Mike": "#e07650",
    "Nancy": "#5cbdad",
    "Dave": "#8a6bbf",
    "Ling Ling": "#e8985e",
    "Lauren": "#c75d88",
}

GROCERY_SECTIONS = OrderedDict([
    ("Produce", ["lettuce", "tomato", "tomatoes", "onion", "garlic", "pepper", "cucumber", "avocado", "lime", "lemon", "cilantro", "basil", "parsley", "corn", "potato", "sweet potato", "carrot", "celery", "broccoli", "spinach", "kale", "banana", "apple", "berries", "strawberr", "blueberr", "watermelon", "grapes", "peach", "mango", "pineapple", "orange", "jalapeño", "jalapeno", "zucchini", "squash", "mushroom", "green bean", "asparagus", "bell pepper", "fruit", "salad", "arugula", "cabbage", "ginger", "scallion"]),
    ("Protein & Meat", ["chicken", "beef", "pork", "turkey", "fish", "salmon", "shrimp", "steak", "ground", "bacon", "sausage", "hot dog", "ham", "deli", "tofu", "eggs", "egg", "thigh", "breast", "wing", "rib"]),
    ("Dairy", ["milk", "cheese", "yogurt", "butter", "cream", "sour cream", "cream cheese", "mozzarella", "parmesan", "cheddar", "half and half"]),
    ("Bakery & Bread", ["bread", "bun", "buns", "roll", "rolls", "tortilla", "pita", "bagel", "croissant", "english muffin", "wrap"]),
    ("Pantry", ["oil", "olive oil", "vinegar", "soy sauce", "ketchup", "mustard", "mayo", "mayonnaise", "salt", "spice", "sugar", "flour", "rice", "pasta", "noodle", "sauce", "salsa", "dressing", "honey", "peanut butter", "jelly", "jam", "cereal", "oat", "granola", "cracker", "nut", "almond", "can", "bean", "beans", "broth", "stock", "seasoning", "marinade"]),
    ("Snacks", ["hummus", "chips", "dip", "trail mix", "granola bar", "fruit snack", "cookie", "cookies", "brownie", "pretzel", "popcorn", "goldfish", "puffs"]),
    ("Frozen", ["frozen", "ice cream", "popsicle"]),
    ("Beverages", ["water", "juice", "soda", "coffee", "tea", "wine", "beer", "seltzer", "lemonade", "drink"]),
    ("Baby & Kids", ["pouch", "pouches", "formula", "diaper", "diapers", "wipe", "wipes", "snack pack", "juice box"]),
])
SECTION_ICONS = {"Produce": "\U0001f966", "Protein & Meat": "\U0001f969", "Dairy": "\U0001f9c0", "Bakery & Bread": "\U0001f35e", "Pantry": "\U0001f3fa", "Snacks": "\U0001f36a", "Frozen": "\U0001f9ca", "Beverages": "\U0001f964", "Baby & Kids": "\U0001f476", "Other": "\U0001f4e6"}


def categorize_grocery(name):
    name_lower = name.lower()
    for section, keywords in GROCERY_SECTIONS.items():
        for kw in keywords:
            if kw in name_lower:
                return section
    return "Other"


def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


img_b64 = get_base64_image(IMAGE_FILE) if IMAGE_FILE.exists() else ""


def _use_gsheets():
    try:
        return "gcp_service_account" in st.secrets and "spreadsheet" in st.secrets
    except Exception:
        return False


@st.cache_resource
def _get_spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_url(st.secrets["spreadsheet"]["url"])
    existing = [ws.title for ws in sh.worksheets()]
    for tab, headers in [("Meals", ["key", "name", "style", "cook", "recipe_url", "notes", "ingredients"]),
                         ("Grocery", ["name", "context", "checked"]),
                         ("Snacks", ["name"]),
                         ("Toddler", ["name"])]:
        if tab not in existing:
            ws = sh.add_worksheet(title=tab, rows=200, cols=10)
            ws.update(range_name="A1", values=[headers])
    return sh


def _load_gsheets():
    sh = _get_spreadsheet()
    data = {"meals": {}, "grocery": [], "staples": {"snacks": [], "toddler": []}}
    try:
        for row in sh.worksheet("Meals").get_all_records():
            key = str(row.get("key", ""))
            if key:
                data["meals"][key] = {k: str(row.get(k, "")) for k in ["name", "style", "cook", "recipe_url", "notes", "ingredients"]}
    except Exception:
        pass
    try:
        for row in sh.worksheet("Grocery").get_all_records():
            n = str(row.get("name", ""))
            if n:
                data["grocery"].append({"name": n, "context": str(row.get("context", "")), "checked": row.get("checked", False) in [True, "TRUE", "true", 1]})
    except Exception:
        pass
    try:
        for row in sh.worksheet("Snacks").get_all_records():
            n = str(row.get("name", ""))
            if n:
                data["staples"]["snacks"].append(n)
    except Exception:
        pass
    try:
        for row in sh.worksheet("Toddler").get_all_records():
            n = str(row.get("name", ""))
            if n:
                data["staples"]["toddler"].append(n)
    except Exception:
        pass
    return data


def _save_gsheets(data):
    sh = _get_spreadsheet()
    try:
        ws = sh.worksheet("Meals")
        rows = [["key", "name", "style", "cook", "recipe_url", "notes", "ingredients"]]
        for key, m in data.get("meals", {}).items():
            rows.append([key, m.get("name", ""), m.get("style", ""), m.get("cook", ""), m.get("recipe_url", ""), m.get("notes", ""), m.get("ingredients", "")])
        ws.clear()
        ws.update(range_name="A1", values=rows)
    except Exception:
        pass
    try:
        ws = sh.worksheet("Grocery")
        rows = [["name", "context", "checked"]]
        for g in data.get("grocery", []):
            rows.append([g["name"], g.get("context", ""), g.get("checked", False)])
        ws.clear()
        ws.update(range_name="A1", values=rows)
    except Exception:
        pass
    try:
        ws = sh.worksheet("Snacks")
        rows = [["name"]] + [[s] for s in data.get("staples", {}).get("snacks", [])]
        ws.clear()
        ws.update(range_name="A1", values=rows)
    except Exception:
        pass
    try:
        ws = sh.worksheet("Toddler")
        rows = [["name"]] + [[s] for s in data.get("staples", {}).get("toddler", [])]
        ws.clear()
        ws.update(range_name="A1", values=rows)
    except Exception:
        pass


def load_data():
    if _use_gsheets():
        try:
            return _load_gsheets()
        except Exception:
            pass
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"meals": {}, "grocery": [], "staples": {"snacks": [], "toddler": []}}


def save_data(data):
    if _use_gsheets():
        try:
            _save_gsheets(data)
            return
        except Exception:
            pass
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def ensure_structure(data):
    if "meals" not in data:
        data["meals"] = {}
    if "grocery" not in data:
        data["grocery"] = []
    if "staples" not in data:
        data["staples"] = {"snacks": [], "toddler": []}
    if "snacks" not in data["staples"]:
        data["staples"]["snacks"] = []
    if "toddler" not in data["staples"]:
        data["staples"]["toddler"] = []
    return data


def meal_key(day, meal_type):
    return f"{day.isoformat()}|{meal_type}"


def get_meal(data, day, meal_type):
    return data["meals"].get(meal_key(day, meal_type), {})


def set_meal(data, day, meal_type, meal_data):
    data["meals"][meal_key(day, meal_type)] = meal_data
    save_data(data)


def clear_meal(data, day, meal_type):
    key = meal_key(day, meal_type)
    if key in data["meals"]:
        del data["meals"][key]
        save_data(data)


def search_recipes(query, meal_context=""):
    try:
        from ddgs import DDGS
        parts = [query.strip()]
        if meal_context:
            parts.insert(0, meal_context)
        parts.append("recipe")
        full_query = " ".join(parts)
        with DDGS() as ddgs:
            try:
                img_results = list(ddgs.images(full_query, max_results=6))
                if img_results:
                    return [
                        {
                            "title": r.get("title", ""),
                            "href": r.get("url", ""),
                            "body": r.get("source", ""),
                            "image": r.get("thumbnail", r.get("image", "")),
                        }
                        for r in img_results
                    ]
            except Exception:
                pass
            text_results = list(ddgs.text(full_query, max_results=6))
            return [dict(r, image="") for r in text_results]
    except Exception:
        return []


CUSTOM_CSS = f"""
<style>
    :root {{
        --sand: #f5f0e8;
        --sand-dark: #e8dfd3;
        --ocean-deep: #1a5c6b;
        --ocean-mid: #237a8a;
        --ocean-light: #2d9bb0;
        --seafoam: #5cbdad;
        --coral: #e07650;
        --coral-dark: #c75d38;
        --sunset: #e8985e;
        --driftwood: #6b5b4e;
        --driftwood-light: #8a7a6b;
        --shell-white: #faf8f5;
        --text-primary: #2c2420;
        --text-secondary: #5a4e44;
        --text-muted: #8a7a6b;
    }}

    .stApp {{
        background: var(--sand) !important;
    }}

    .stApp > header {{
        background: transparent !important;
    }}

    .block-container {{
        padding-top: 1rem !important;
        max-width: 720px !important;
    }}

    .header-banner {{
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        padding: 36px 24px 28px;
        margin-bottom: 8px;
        text-align: center;
    }}
    .header-banner::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: url('data:image/png;base64,{img_b64}');
        background-size: cover;
        background-position: center 40%;
        opacity: 0.45;
        z-index: 0;
    }}
    .header-banner::after {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(135deg, rgba(26,92,107,0.75), rgba(45,155,176,0.55));
        z-index: 1;
    }}
    .header-banner h1, .header-banner p {{
        position: relative;
        z-index: 2;
        color: white;
        margin: 0;
        text-shadow: 0 2px 8px rgba(0,0,0,0.35);
    }}
    .header-banner h1 {{
        font-size: 1.8em;
        margin-bottom: 2px;
        letter-spacing: -0.02em;
    }}
    .header-banner p {{
        font-size: 1em;
        opacity: 0.92;
    }}

    .allergy-banner {{
        background: #fdf0e0;
        border: 1.5px solid #e8985e;
        border-radius: 10px;
        padding: 8px 14px;
        margin: 8px 0 16px;
        font-size: 0.88em;
        color: #7a4a20;
        text-align: center;
        font-weight: 500;
    }}

    .how-to-box {{
        background: var(--shell-white);
        border: 2px solid var(--ocean-light);
        border-radius: 14px;
        padding: 18px 20px;
        margin: 0 0 16px;
        font-size: 0.95em;
        color: var(--text-primary);
        line-height: 1.7;
    }}
    .how-to-box strong {{
        color: var(--ocean-deep);
    }}
    .how-to-box .how-to-title {{
        font-size: 1.05em;
        font-weight: 700;
        color: var(--ocean-deep);
        margin-bottom: 8px;
    }}
    .how-to-box ol {{
        padding-left: 20px;
        margin: 6px 0 0;
    }}
    .how-to-box li {{
        margin-bottom: 4px;
    }}

    .day-nav {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin: 8px 0 12px;
    }}
    .day-nav-label {{
        font-size: 1.2em;
        font-weight: 700;
        color: var(--ocean-deep);
        min-width: 220px;
        text-align: center;
    }}

    .meal-row {{
        background: var(--shell-white);
        border: 1.5px solid var(--sand-dark);
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0;
        transition: box-shadow 0.15s;
    }}
    .meal-row:hover {{
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .meal-row-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }}
    .meal-type-label {{
        font-weight: 700;
        font-size: 1em;
        color: var(--ocean-deep);
    }}
    .meal-style-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78em;
        font-weight: 600;
    }}
    .badge-home {{
        background: #dff0e8;
        color: #2a6b4e;
    }}
    .badge-out {{
        background: #fde8d8;
        color: #b05a2a;
    }}
    .badge-leftovers {{
        background: #e8e4f0;
        color: #5a4a7a;
    }}
    .badge-flexible {{
        background: #e8e8e8;
        color: #5a5a5a;
    }}
    .meal-name {{
        font-size: 0.95em;
        color: var(--text-primary);
        margin: 2px 0;
    }}
    .meal-cook {{
        font-size: 0.82em;
        color: var(--text-muted);
    }}
    .meal-recipe-link {{
        font-size: 0.8em;
    }}
    .meal-empty {{
        font-size: 0.88em;
        color: var(--text-muted);
        font-style: italic;
    }}

    .grocery-item {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid var(--sand-dark);
        font-size: 0.92em;
        color: var(--text-primary);
    }}
    .grocery-checked {{
        text-decoration: line-through;
        color: var(--text-muted);
    }}
    .grocery-context {{
        font-size: 0.8em;
        color: var(--text-muted);
    }}

    .staple-chip {{
        display: inline-block;
        background: var(--shell-white);
        border: 1px solid var(--sand-dark);
        border-radius: 16px;
        padding: 4px 12px;
        margin: 3px 4px;
        font-size: 0.85em;
        color: var(--text-primary);
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: var(--sand-dark);
        border-radius: 12px;
        padding: 3px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 600;
        color: var(--text-secondary);
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--shell-white) !important;
        color: var(--ocean-deep) !important;
    }}

    .stSelectbox label, .stTextInput label, .stTextArea label {{
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
    }}
    .stSelectbox > div > div, .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
        background: var(--shell-white) !important;
        border-color: var(--sand-dark) !important;
        color: var(--text-primary) !important;
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, var(--ocean-mid), var(--seafoam)) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, var(--ocean-light), var(--seafoam)) !important;
        box-shadow: 0 2px 8px rgba(45,155,176,0.3) !important;
    }}
    .stButton > button[kind="secondary"] {{
        border-color: var(--coral) !important;
        color: var(--coral) !important;
        border-radius: 10px !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: #fdf0e0 !important;
    }}

    hr {{
        border-color: var(--sand-dark) !important;
    }}

    .login-container {{
        max-width: 400px;
        margin: 0 auto;
        padding: 20px 0;
    }}

    .user-pill {{
        display: inline-block;
        background: var(--ocean-deep);
        color: white;
        border-radius: 16px;
        padding: 4px 14px;
        font-size: 0.85em;
        font-weight: 600;
        margin-bottom: 8px;
    }}

    div[data-testid="stExpander"] {{
        border: 1.5px solid var(--sand-dark) !important;
        border-radius: 12px !important;
        background: var(--shell-white) !important;
    }}
    div[data-testid="stExpander"] summary {{
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }}

    .search-result {{
        background: var(--shell-white);
        border: 1px solid var(--sand-dark);
        border-radius: 10px;
        padding: 10px 12px;
        margin: 6px 0;
    }}
    .search-result-title {{
        font-weight: 600;
        font-size: 0.9em;
        color: var(--ocean-deep);
    }}
    .search-result-snippet {{
        font-size: 0.8em;
        color: var(--text-muted);
        margin: 2px 0;
    }}
    .search-result-img {{
        width: 80px;
        height: 80px;
        object-fit: cover;
        border-radius: 8px;
        flex-shrink: 0;
    }}
    .search-result-flex {{
        display: flex;
        gap: 12px;
        align-items: flex-start;
    }}

    .overview-grid {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 6px;
        margin: 8px 0 16px;
    }}
    .overview-day-header {{
        font-weight: 700;
        font-size: 0.75em;
        color: var(--ocean-deep);
        text-align: center;
        padding: 6px 2px;
        background: var(--sand-dark);
        border-radius: 8px 8px 0 0;
    }}
    .overview-cell {{
        background: var(--shell-white);
        border: 1px solid var(--sand-dark);
        border-radius: 8px;
        padding: 6px 5px;
        min-height: 54px;
        font-size: 0.72em;
        line-height: 1.3;
    }}
    .overview-cell-meal {{
        font-weight: 600;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .overview-cell-cook {{
        display: inline-block;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 0.85em;
        font-weight: 600;
        color: white;
        margin-top: 2px;
    }}
    .overview-cell-empty {{
        color: var(--text-muted);
        font-style: italic;
        font-size: 0.85em;
    }}
    .overview-meal-label {{
        font-size: 0.7em;
        color: var(--text-muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .overview-legend {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0 12px;
        justify-content: center;
    }}
    .overview-legend-item {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.8em;
        color: var(--text-secondary);
    }}
    .overview-legend-dot {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
    }}
</style>
"""

HEADER_HTML = """
<div class="header-banner">
    <h1>\U0001f3d6\ufe0f Jacob Family Rehoboth Trip</h1>
    <p>Meal Planner \u00b7 July 5 \u2013 11, 2026 \u00b7 6 adults, 3 kids</p>
</div>
"""

ALLERGY_HTML = f'<div class="allergy-banner">\u26a0\ufe0f {ALLERGY_NOTE}</div>'

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = ensure_structure(load_data())
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "current_day_idx" not in st.session_state:
    st.session_state.current_day_idx = 0
if "editing_meal" not in st.session_state:
    st.session_state.editing_meal = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_recipe" not in st.session_state:
    st.session_state.selected_recipe = None

data = st.session_state.data

HOW_TO_HTML = """
<div class="how-to-box">
    <div class="how-to-title">How to Use This App</div>
    <ol>
        <li><strong>Pick your name</strong> from the dropdown below, then tap <strong>"Let's Plan"</strong>.</li>
        <li>Use the <strong>Meals</strong> tab to plan each day. Tap the <strong>arrows</strong> to move between days.</li>
        <li>Tap <strong>"Edit"</strong> next to any meal to fill in what you're making, who's cooking, and any notes.</li>
        <li>Use the <strong>Grocery List</strong> tab to add items you need to buy. Check them off as you shop.</li>
        <li>Use the <strong>Staples</strong> tab for snacks and toddler foods that aren't tied to a specific meal.</li>
    </ol>
    <strong>Everyone shares the same plan</strong> &mdash; any changes you make will show up for the whole group.
</div>
"""

if not st.session_state.user_name:
    st.markdown(HEADER_HTML, unsafe_allow_html=True)
    st.markdown(ALLERGY_HTML, unsafe_allow_html=True)
    st.markdown(HOW_TO_HTML, unsafe_allow_html=True)
    st.markdown("#### Who are you?")
    chosen = st.selectbox("Pick your name", [""] + MEMBERS, index=0, label_visibility="collapsed")
    if st.button("Let's Plan", type="primary", use_container_width=True, disabled=not chosen):
        st.session_state.user_name = chosen
        st.rerun()
    st.stop()

st.markdown(HEADER_HTML, unsafe_allow_html=True)
st.markdown(ALLERGY_HTML, unsafe_allow_html=True)

if "show_help" not in st.session_state:
    st.session_state.show_help = False

col_user, col_help, col_sync, col_switch = st.columns([2, 0.7, 0.7, 0.6])
with col_user:
    storage_icon = "\U0001f4e1" if _use_gsheets() else "\U0001f4f1"
    st.markdown(f'<span class="user-pill">{st.session_state.user_name}</span> <span style="font-size:0.75em;color:var(--text-muted);">{storage_icon}</span>', unsafe_allow_html=True)
with col_help:
    if st.button("Help", key="help_btn", use_container_width=True):
        st.session_state.show_help = not st.session_state.show_help
        st.rerun()
with col_sync:
    if st.button("\U0001f504 Sync", key="sync_btn", use_container_width=True):
        st.session_state.data = ensure_structure(load_data())
        st.rerun()
with col_switch:
    if st.button("Switch", key="switch_user"):
        st.session_state.user_name = ""
        st.session_state.editing_meal = None
        st.session_state.search_results = []
        st.rerun()

if st.session_state.show_help:
    st.markdown(HOW_TO_HTML, unsafe_allow_html=True)

tab_overview, tab_meals, tab_grocery, tab_staples = st.tabs(["\U0001f4c5 Overview", "\U0001f37d\ufe0f Meals", "\U0001f6d2 Grocery List", "\U0001f34c Staples"])

with tab_overview:
    st.markdown("### \U0001f4c5 Week at a Glance")
    legend_html = '<div class="overview-legend">'
    for member, color in COOK_COLORS.items():
        legend_html += f'<span class="overview-legend-item"><span class="overview-legend-dot" style="background:{color};"></span>{member}</span>'
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)

    for meal_type in MEALS:
        icon = MEAL_TYPE_ICONS.get(meal_type, "")
        st.markdown(f"**{icon} {meal_type}**")
        grid_html = '<div class="overview-grid">'
        for day in DAYS:
            day_short = day.strftime("%a %m/%d")
            grid_html += f'<div class="overview-day-header">{day_short}</div>'
        grid_html += '</div><div class="overview-grid">'
        for day in DAYS:
            m = get_meal(data, day, meal_type)
            m_name = m.get("name", "")
            m_cook = m.get("cook", "")
            m_style = m.get("style", "")
            style_icon = MEAL_ICONS.get(m_style, "")
            if m_name:
                cook_color = COOK_COLORS.get(m_cook, "#8a7a6b")
                cook_badge = f'<div><span class="overview-cell-cook" style="background:{cook_color};">{m_cook}</span></div>' if m_cook else ""
                grid_html += (
                    f'<div class="overview-cell">'
                    f'<div class="overview-cell-meal">{style_icon} {m_name}</div>'
                    f'{cook_badge}'
                    f'</div>'
                )
            else:
                grid_html += '<div class="overview-cell"><div class="overview-cell-empty">\u2014</div></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

with tab_meals:
    if st.session_state.selected_recipe:
        sr = st.session_state.selected_recipe
        sr_day = date.fromisoformat(sr["day"])
        set_meal(data, sr_day, sr["meal_type"], {
            "name": sr["name"],
            "style": sr["style"],
            "cook": sr["cook"],
            "recipe_url": sr["recipe_url"],
            "notes": sr["notes"],
            "ingredients": sr["ingredients"],
        })
        old_set = {x.strip().lower() for x in sr.get("old_ingredients", "").split(",") if x.strip()}
        day_label = sr_day.strftime("%A") + " " + sr["meal_type"].lower()
        for item in [x.strip() for x in sr["ingredients"].split(",") if x.strip()]:
            if item.lower() not in old_set:
                data["grocery"].append({"name": item, "context": day_label, "checked": False})
        save_data(data)
        st.session_state.data = data
        st.session_state.selected_recipe = None
        st.session_state.editing_meal = None
        st.session_state.search_results = []
        st.rerun()

    day_idx = st.session_state.current_day_idx
    current_day = DAYS[day_idx]

    nav_cols = st.columns([1, 4, 1])
    with nav_cols[0]:
        if st.button("\u25c0", key="prev_day", disabled=day_idx == 0, use_container_width=True):
            st.session_state.current_day_idx = max(0, day_idx - 1)
            st.session_state.editing_meal = None
            st.session_state.search_results = []
            st.rerun()
    with nav_cols[1]:
        day_label = current_day.strftime("%A, %B %d")
        st.markdown(f'<div class="day-nav"><span class="day-nav-label">{day_label}</span></div>', unsafe_allow_html=True)
    with nav_cols[2]:
        if st.button("\u25b6", key="next_day", disabled=day_idx == len(DAYS) - 1, use_container_width=True):
            st.session_state.current_day_idx = min(len(DAYS) - 1, day_idx + 1)
            st.session_state.editing_meal = None
            st.session_state.search_results = []
            st.rerun()

    day_dots = ""
    for i in range(len(DAYS)):
        if i == day_idx:
            day_dots += f'<span style="color:var(--ocean-deep);font-size:1.4em;margin:0 3px;">\u25cf</span>'
        else:
            day_dots += f'<span style="color:var(--sand-dark);font-size:1.4em;margin:0 3px;">\u25cf</span>'
    st.markdown(f'<div style="text-align:center;margin-bottom:12px;">{day_dots}</div>', unsafe_allow_html=True)

    for meal_type in MEALS:
        meal = get_meal(data, current_day, meal_type)
        icon = MEAL_TYPE_ICONS.get(meal_type, "")
        style = meal.get("style", "")
        name = meal.get("name", "")
        cook = meal.get("cook", "")
        recipe_url = meal.get("recipe_url", "")
        notes = meal.get("notes", "")

        badge_class = f"badge-{style.lower()}" if style else ""
        badge_html = f'<span class="meal-style-badge {badge_class}">{MEAL_ICONS.get(style, "")} {style}</span>' if style else ""

        if name:
            recipe_html = f' &middot; <a class="meal-recipe-link" href="{recipe_url}" target="_blank">View Recipe</a>' if recipe_url else ""
            cook_html = f'<div class="meal-cook">Cook: {cook}{recipe_html}</div>' if cook else (f'<div class="meal-cook">{recipe_html.lstrip(" &middot; ")}</div>' if recipe_url else "")
            notes_html = f'<div class="meal-cook" style="font-style:italic;">{notes}</div>' if notes else ""
            content_html = f'<div class="meal-row"><div class="meal-row-header"><span class="meal-type-label">{icon} {meal_type}</span>{badge_html}</div><div class="meal-name">{name}</div>{cook_html}{notes_html}</div>'
        else:
            content_html = f'<div class="meal-row"><div class="meal-row-header"><span class="meal-type-label">{icon} {meal_type}</span>{badge_html}</div><div class="meal-empty">Tap edit to plan this meal</div></div>'

        st.markdown(content_html, unsafe_allow_html=True)

        is_editing = st.session_state.editing_meal == f"{current_day.isoformat()}|{meal_type}"

        edit_cols = st.columns([1, 1])
        with edit_cols[0]:
            if st.button("Edit" if not is_editing else "Close", key=f"edit_{meal_type}", use_container_width=True):
                if is_editing:
                    st.session_state.editing_meal = None
                    st.session_state.search_results = []
                else:
                    st.session_state.editing_meal = f"{current_day.isoformat()}|{meal_type}"
                    st.session_state.search_results = []
                st.rerun()
        with edit_cols[1]:
            if name:
                if st.button("Clear", key=f"clear_{meal_type}", type="secondary", use_container_width=True):
                    clear_meal(data, current_day, meal_type)
                    st.session_state.data = data
                    st.session_state.editing_meal = None
                    st.rerun()

        if is_editing:
            with st.container():
                st.markdown(f"**Edit {meal_type}**")

                edit_style = st.selectbox(
                    "Meal type",
                    MEAL_STYLES,
                    index=MEAL_STYLES.index(style) if style in MEAL_STYLES else 0,
                    key=f"style_{meal_type}",
                )

                edit_cook = st.selectbox(
                    "Who's cooking?",
                    ["(nobody yet)"] + MEMBERS,
                    index=(MEMBERS.index(cook) + 1) if cook in MEMBERS else 0,
                    key=f"cook_{meal_type}",
                )

                edit_name = st.text_input(
                    "What's planned?",
                    value=name,
                    placeholder="e.g. Grilled chicken + corn",
                    key=f"name_{meal_type}",
                )

                ingredients = meal.get("ingredients", "")
                edit_ingredients = st.text_input(
                    "Ingredients (comma-separated \u2192 auto-added to grocery list)",
                    value=ingredients,
                    placeholder="e.g. chicken thighs, corn on the cob, olive oil",
                    key=f"ingredients_{meal_type}",
                )

                edit_notes = st.text_input(
                    "Notes",
                    value=notes,
                    placeholder="e.g. marinate by 3pm",
                    key=f"notes_{meal_type}",
                )

                edit_recipe = st.text_input(
                    "Recipe URL",
                    value=recipe_url,
                    placeholder="Paste a link",
                    key=f"recipe_{meal_type}",
                )

                st.markdown("---")
                st.caption("\U0001f50d Find a Recipe")
                with st.form(key=f"search_form_{meal_type}"):
                    search_q = st.text_input("Search recipes", placeholder=f"e.g. {meal_type.lower()} ideas, grilled chicken", key=f"sq_{meal_type}", label_visibility="collapsed")
                    search_submitted = st.form_submit_button("\U0001f50d Search Recipes", use_container_width=True)

                if search_submitted:
                    q = search_q.strip() if search_q.strip() else edit_name.strip()
                    if q:
                        with st.spinner("Searching recipes..."):
                            st.session_state.search_results = search_recipes(q, meal_context=meal_type)
                        st.rerun()

                if st.session_state.search_results:
                    for ri, r in enumerate(st.session_state.search_results):
                        r_title = r.get("title", "")
                        r_url = r.get("href", "")
                        r_body = r.get("body", "")[:120]
                        r_image = r.get("image", "")
                        if r_image:
                            st.markdown(
                                f'<div class="search-result"><div class="search-result-flex">'
                                f'<img class="search-result-img" src="{r_image}" onerror="this.style.display=\'none\'">'
                                f'<div><div class="search-result-title">{r_title}</div>'
                                f'<div class="search-result-snippet">{r_body}</div></div>'
                                f'</div></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="search-result">'
                                f'<div class="search-result-title">{r_title}</div>'
                                f'<div class="search-result-snippet">{r_body}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            if r_url:
                                st.markdown(f"[Open recipe]({r_url})")
                        with rc2:
                            if st.button("Use this", key=f"use_{meal_type}_{ri}", use_container_width=True):
                                st.session_state.selected_recipe = {
                                    "name": r_title if r_title else edit_name.strip(),
                                    "style": edit_style,
                                    "cook": edit_cook if edit_cook != "(nobody yet)" else "",
                                    "recipe_url": r_url,
                                    "notes": edit_notes.strip(),
                                    "ingredients": edit_ingredients.strip(),
                                    "old_ingredients": meal.get("ingredients", ""),
                                    "day": current_day.isoformat(),
                                    "meal_type": meal_type,
                                }
                                st.rerun()

                if st.button("Save", key=f"save_{meal_type}", type="primary", use_container_width=True):
                    new_ingredients_str = edit_ingredients.strip()
                    old_ingredients_str = meal.get("ingredients", "")
                    set_meal(data, current_day, meal_type, {
                        "name": edit_name.strip(),
                        "style": edit_style,
                        "cook": edit_cook if edit_cook != "(nobody yet)" else "",
                        "recipe_url": edit_recipe.strip(),
                        "notes": edit_notes.strip(),
                        "ingredients": new_ingredients_str,
                    })
                    old_set = {x.strip().lower() for x in old_ingredients_str.split(",") if x.strip()} if old_ingredients_str else set()
                    new_items = [x.strip() for x in new_ingredients_str.split(",") if x.strip()]
                    day_label = current_day.strftime("%A") + " " + meal_type.lower()
                    for item in new_items:
                        if item.lower() not in old_set:
                            data["grocery"].append({"name": item, "context": day_label, "checked": False})
                    save_data(data)
                    st.session_state.data = data
                    st.session_state.editing_meal = None
                    st.session_state.search_results = []
                    st.rerun()

            st.markdown("---")

with tab_grocery:
    st.markdown("### \U0001f6d2 Grocery List")

    with st.form(key="grocery_form", clear_on_submit=True):
        new_item = st.text_input("Add item", placeholder="e.g. chicken thighs (3 lbs)", key="new_grocery", label_visibility="collapsed")
        gf_cols = st.columns([3, 1])
        with gf_cols[0]:
            new_context = st.text_input("For which meal? (optional)", placeholder="e.g. Tuesday dinner", key="grocery_ctx", label_visibility="collapsed")
        with gf_cols[1]:
            grocery_submitted = st.form_submit_button("Add", use_container_width=True)
    if grocery_submitted and new_item.strip():
        existing = [g["name"].lower() for g in data["grocery"]]
        if new_item.strip().lower() in existing:
            for g in data["grocery"]:
                if g["name"].lower() == new_item.strip().lower() and new_context.strip():
                    old_ctx = g.get("context", "")
                    g["context"] = f"{old_ctx}, {new_context.strip()}" if old_ctx else new_context.strip()
                    break
        else:
            data["grocery"].append({
                "name": new_item.strip(),
                "context": new_context.strip(),
                "checked": False,
            })
        save_data(data)
        st.rerun()

    unchecked = [(i, g) for i, g in enumerate(data["grocery"]) if not g.get("checked")]
    checked = [(i, g) for i, g in enumerate(data["grocery"]) if g.get("checked")]

    if unchecked:
        export_cols = st.columns([1, 1])
        with export_cols[0]:
            st.caption(f"{len(unchecked)} item(s) to buy")
        with export_cols[1]:
            if st.button("\U0001f4cb Copy List", key="export_grocery", use_container_width=True):
                st.session_state.show_grocery_export = True
                st.rerun()

        if st.session_state.get("show_grocery_export"):
            sections = OrderedDict()
            for _, item in unchecked:
                sec = categorize_grocery(item["name"])
                sections.setdefault(sec, []).append(item)
            export_lines = []
            for sec, items in sections.items():
                icon = SECTION_ICONS.get(sec, "")
                export_lines.append(f"\n{icon} {sec}")
                for it in items:
                    ctx = f" ({it['context']})" if it.get("context") else ""
                    export_lines.append(f"  \u25a2 {it['name']}{ctx}")
            export_text = "GROCERY LIST\n" + "\n".join(export_lines)
            st.code(export_text, language=None)
            if st.button("Hide", key="hide_export"):
                st.session_state.show_grocery_export = False
                st.rerun()

        sections = OrderedDict()
        for idx, item in unchecked:
            sec = categorize_grocery(item["name"])
            sections.setdefault(sec, []).append((idx, item))

        for sec, items in sections.items():
            icon = SECTION_ICONS.get(sec, "")
            st.markdown(f'<div style="font-weight:600;font-size:0.85em;color:var(--ocean-deep);margin:12px 0 4px;">{icon} {sec}</div>', unsafe_allow_html=True)
            for idx, item in items:
                gc = st.columns([0.5, 3, 1])
                with gc[0]:
                    if st.checkbox("", key=f"gc_{idx}", value=False, label_visibility="collapsed"):
                        data["grocery"][idx]["checked"] = True
                        save_data(data)
                        st.rerun()
                with gc[1]:
                    ctx = f' <span class="grocery-context">({item["context"]})</span>' if item.get("context") else ""
                    st.markdown(f'{item["name"]}{ctx}', unsafe_allow_html=True)
                with gc[2]:
                    if st.button("\u2715", key=f"grm_{idx}", use_container_width=True):
                        data["grocery"].pop(idx)
                        save_data(data)
                        st.rerun()

    elif not checked:
        st.caption("No grocery items yet. Add some above.")

    if checked:
        st.markdown("---")
        st.caption(f"{len(checked)} item(s) bought")
        for idx, item in checked:
            gc = st.columns([0.5, 3, 1])
            with gc[0]:
                if st.checkbox("", key=f"gc_{idx}", value=True, label_visibility="collapsed"):
                    data["grocery"][idx]["checked"] = False
                    save_data(data)
                    st.rerun()
            with gc[1]:
                st.markdown(f'<span class="grocery-checked">{item["name"]}</span>', unsafe_allow_html=True)
            with gc[2]:
                if st.button("\u2715", key=f"grm_{idx}", use_container_width=True):
                    data["grocery"].pop(idx)
                    save_data(data)
                    st.rerun()

        if st.button("Clear bought items", key="clear_checked", type="secondary", use_container_width=True):
            data["grocery"] = [g for g in data["grocery"] if not g.get("checked")]
            save_data(data)
            st.rerun()

with tab_staples:
    st.markdown("### \U0001f34c Snacks & Staples")
    st.caption("Recurring items for the trip — not tied to specific days")
    total_staples = len(data["staples"]["snacks"]) + len(data["staples"]["toddler"])
    if total_staples > 0:
        all_chips = ""
        for s in data["staples"]["snacks"]:
            all_chips += f'<span class="staple-chip" style="border-color:var(--seafoam);">\U0001f95c {s}</span>'
        for s in data["staples"]["toddler"]:
            all_chips += f'<span class="staple-chip" style="border-color:var(--sunset);">\U0001f476 {s}</span>'
        st.markdown(
            f'<div style="background:var(--shell-white);border:1.5px solid var(--sand-dark);border-radius:12px;padding:12px 14px;margin-bottom:12px;">'
            f'<div style="font-weight:700;color:var(--ocean-deep);margin-bottom:8px;">\U0001f4cb All Staples ({total_staples})</div>'
            f'<div>{all_chips}</div>'
            f'<div style="font-size:0.8em;color:var(--text-muted);margin-top:8px;">\u2705 Auto-added to Grocery List</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("**Snacks (everyone)**")
    snacks = data["staples"]["snacks"]
    if snacks:
        chips_html = " ".join(f'<span class="staple-chip">{s}</span>' for s in snacks)
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.caption("No snacks added yet")

    with st.form(key="snack_form", clear_on_submit=True):
        snack_cols = st.columns([3, 1])
        with snack_cols[0]:
            new_snack = st.text_input("Add snack", placeholder="e.g. hummus, chips", key="new_snack", label_visibility="collapsed")
        with snack_cols[1]:
            snack_submitted = st.form_submit_button("Add", use_container_width=True)
    if snack_submitted and new_snack.strip():
        data["staples"]["snacks"].append(new_snack.strip())
        data["grocery"].append({"name": new_snack.strip(), "context": "Staple - Snack", "checked": False})
        save_data(data)
        st.rerun()

    if snacks:
        remove_snack = st.selectbox("Remove a snack", [""] + snacks, key="rm_snack", label_visibility="collapsed")
        if remove_snack and st.button("Remove selected snack", key="do_rm_snack", type="secondary", use_container_width=True):
            data["staples"]["snacks"].remove(remove_snack)
            data["grocery"] = [g for g in data["grocery"] if not (g["name"] == remove_snack and g.get("context", "").startswith("Staple"))]
            save_data(data)
            st.rerun()

    st.markdown("---")
    st.markdown("**Toddler staples** (15mo, 17.5mo, 5yr)")
    toddler = data["staples"]["toddler"]
    if toddler:
        t_html = " ".join(f'<span class="staple-chip">{s}</span>' for s in toddler)
        st.markdown(t_html, unsafe_allow_html=True)
    else:
        st.caption("No toddler staples added yet")

    with st.form(key="toddler_form", clear_on_submit=True):
        toddler_cols = st.columns([3, 1])
        with toddler_cols[0]:
            new_toddler = st.text_input("Add toddler staple", placeholder="e.g. pouches, bananas", key="new_toddler", label_visibility="collapsed")
        with toddler_cols[1]:
            toddler_submitted = st.form_submit_button("Add", use_container_width=True)
    if toddler_submitted and new_toddler.strip():
        data["staples"]["toddler"].append(new_toddler.strip())
        data["grocery"].append({"name": new_toddler.strip(), "context": "Staple - Toddler", "checked": False})
        save_data(data)
        st.rerun()

    if toddler:
        remove_toddler = st.selectbox("Remove a toddler staple", [""] + toddler, key="rm_toddler", label_visibility="collapsed")
        if remove_toddler and st.button("Remove selected staple", key="do_rm_toddler", type="secondary", use_container_width=True):
            data["staples"]["toddler"].remove(remove_toddler)
            data["grocery"] = [g for g in data["grocery"] if not (g["name"] == remove_toddler and g.get("context", "").startswith("Staple"))]
            save_data(data)
            st.rerun()
