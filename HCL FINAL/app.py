import json
import os
import re
import time
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False


APP_TITLE = "INTERVIEW BUDDY : AAPKA APNA BUDDY"
SEARCH_ENGINE = "DuckDuckGo"

# -------------------------
# Safe image/icon loader
# -------------------------
BASE_DIR = Path(__file__).parent

def safe_path(filename: str) -> Optional[str]:
    """Return a safe path to an image, checking both root and assets/ folder."""
    root_path = BASE_DIR / filename
    assets_path = BASE_DIR / "assets" / filename
    if root_path.exists():
        return str(root_path)
    elif assets_path.exists():
        return str(assets_path)
    else:
        return None


FALLBACK_TECH_QUESTIONS = {
    ("Software Engineer", "frontend"): [
        {"q": "Explain the virtual DOM and how it differs from the real DOM.", "topic": "frontend", "difficulty": "medium", "type": "concept"},
        {"q": "Given an array of numbers, return indices of two numbers that add up to a target.", "topic": "algorithms", "difficulty": "easy", "type": "coding"},
        {"q": "How would you improve the performance of a large React application?", "topic": "performance", "difficulty": "medium", "type": "design"},
    ],
    ("Software Engineer", "backend"): [
        {"q": "Describe database indexing. When does an index help, and when might it hurt?", "topic": "databases", "difficulty": "medium", "type": "concept"},
        {"q": "Design a rate limiter for an API. Outline data structures and trade-offs.", "topic": "system design", "difficulty": "medium", "type": "design"},
        {"q": "Given a log stream, find the most frequent 10 endpoints in the last 5 minutes.", "topic": "stream/algorithms", "difficulty": "hard", "type": "algorithms"},
    ],
    ("Data Analyst", "ml"): [
        {"q": "Explain bias-variance tradeoff with an example.", "topic": "ml", "difficulty": "medium", "type": "concept"},
        {"q": "You have missing values in a dataset with categorical and numeric features—what strategies would you use?", "topic": "data prep", "difficulty": "easy", "type": "practical"},
        {"q": "How would you evaluate the impact of a new feature in a product?", "topic": "experimentation", "difficulty": "medium", "type": "analysis"},
    ],
}

FALLBACK_BEHAV_QUESTIONS = {
    "Software Engineer": [
        {"q": "Tell me about a time you had to quickly learn a new technology to deliver a project.", "topic": "learning", "type": "behavioral"},
        {"q": "Describe a situation where you had a conflict with a teammate. How did you handle it?", "topic": "conflict", "type": "behavioral"},
        {"q": "Give an example of a time you led without authority.", "topic": "leadership", "type": "behavioral"},
    ],
    "Product Manager": [
        {"q": "Tell me about a time you had to prioritize conflicting stakeholder requests.", "topic": "prioritization", "type": "behavioral"},
        {"q": "Describe a product decision you made that didn't work out. What did you learn?", "topic": "learning", "type": "behavioral"},
        {"q": "Give an example of influencing a team without direct authority.", "topic": "influence", "type": "behavioral"},
    ],
    "Data Analyst": [
        {"q": "Tell me about a time your analysis changed someone's mind.", "topic": "impact", "type": "behavioral"},
        {"q": "Describe a project where you had unclear requirements. What did you do?", "topic": "ambiguity", "type": "behavioral"},
        {"q": "Give an example of handling tight deadlines.", "topic": "time management", "type": "behavioral"},
    ],
}

TECH_RUBRIC = (
    "Evaluate technical accuracy, clarity, completeness and trade-offs. "
    "Focus on core concepts, steps/algorithms, edge-cases & complexity, and communication."
)
BEHAV_RUBRIC = (
    "Evaluate using STAR: Situation, Task, Action, Result - check clarity, ownership, impact, and reflection."
)

# -------------------------
# Streamlit setup
# -------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=safe_path("LOGO.png"),
    layout="wide"
)

# -------------------------
# Your existing code continues...
# -------------------------
# (unchanged code for search, generate_questions, evaluations, export, init_state, etc.)
# -------------------------

# replace image loading with safe_path in interview step:
elif st.session_state.step == "interview":
    q = current_q()
    st.markdown(f"### Interview — {st.session_state.mode} — {st.session_state.role}{' — ' + st.session_state.domain if st.session_state.domain else ''}")

    cols = st.columns(2)
    with cols[0]:
        bot_img = safe_path("BOT.jpg")
        if bot_img:
            st.image(bot_img, width=72)
        st.markdown("**InterviewBot**")
    with cols[1]:
        cand_img = safe_path("CANDIDATE.jpg")
        if cand_img:
            st.image(cand_img, width=72)
        st.markdown("**Candidate**")

    # rest of your interview logic unchanged...

