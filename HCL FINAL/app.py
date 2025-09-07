
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



def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a search using DuckDuckGo and return results.
    Uses HTML scraping method.
    """
    try:

        url = "https://html.duckduckgo.com/html/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        data = {
            'q': query,
            'kl': 'us-en', 
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
    
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        result_elements = soup.find_all('div', class_='result')
        
        for result in result_elements[:max_results]:
            try:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                url_elem = result.find('a', class_='result__url')
                
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True)
                    url = url_elem.get('href') if url_elem else "No URL available"
                    
                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'url': url
                    })
            except Exception as e:
                st.error(f"Error parsing result: {e}")
                continue
        
        return results
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def search_with_fallback(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform search with fallback to cached results if needed
    """
   
    results = duckduckgo_search(query, max_results)
    
    if not results:
    
        if any(term in query.lower() for term in ['technical', 'code', 'programming', 'software']):
            results = [
                {
                    'title': 'Technical Interview Preparation Guide',
                    'snippet': 'Comprehensive guide to technical interviews including coding challenges, system design, and algorithm questions.',
                    'url': 'https://example.com/technical-interview-guide'
                },
                {
                    'title': 'Common Coding Interview Questions',
                    'snippet': 'Collection of frequently asked coding interview questions with solutions in multiple programming languages.',
                    'url': 'https://example.com/coding-questions'
                }
            ]
        elif any(term in query.lower() for term in ['behavioral', 'star', 'situation', 'experience']):
            results = [
                {
                    'title': 'Behavioral Interview Questions and Answers',
                    'snippet': 'Learn how to answer behavioral interview questions using the STAR method with examples.',
                    'url': 'https://example.com/behavioral-interviews'
                },
                {
                    'title': 'STAR Method Interview Guide',
                    'snippet': 'Complete guide to using the Situation, Task, Action, Result method for behavioral interviews.',
                    'url': 'https://example.com/star-method'
                }
            ]
    
    return results

def generate_from_search(query: str, context: str = "") -> str:
    """
    Generate content based on search results
    """
    search_results = search_with_fallback(query)
    
    if not search_results:
        return "I couldn't find specific information about this topic. Would you like to rephrase your question?"
    
    
    response = f"Based on my research about '{query}', I found these insights:\n\n"
    
    for i, result in enumerate(search_results[:3], 1):
        response += f"{i}. **{result['title']}**: {result['snippet']}\n"
        response += f"   Source: {result['url']}\n\n"
    
    response += "Would you like me to search for more specific information on any aspect?"
    
    return response


def extract_json(text: str, strict: bool = False) -> Optional[str]:
    """Try to extract a JSON object substring from text. If strict=True, only accept pure JSON."""
    if not text:
        return None
    t = text.strip()
    if strict:
        if t.startswith("{") and t.endswith("}"):
            return t
        return None

    m = re.search(r"\{[\s\S]*\}\s*$", text)
    return m.group(0) if m else None

def export_json(summary: Dict[str, Any], qa_rows: List[Dict[str, Any]]) -> bytes:
    payload = {"generated_at": datetime.utcnow().isoformat() + "Z", "summary": summary, "qa": qa_rows}
    return json.dumps(payload, indent=2).encode("utf-8")

def export_csv(qa_rows: List[Dict[str, Any]]) -> bytes:
    return pd.DataFrame(qa_rows).to_csv(index=False).encode("utf-8")

def export_pdf(summary: Dict[str, Any], qa_rows: List[Dict[str, Any]]) -> Optional[bytes]:
    if not HAS_FPDF:
        return None
    
    class UnicodePDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Interview Summary Report", 0, 1, "C")
            self.ln(4)
        
        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
    
    pdf = UnicodePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Interview Summary Report", 0, 1, "C")
    pdf.ln(10)
    
    def write_section(title: str, items: List[str]):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, title, 0, 1)
        pdf.set_font("Arial", size=11)
        for it in items:
        
            it_clean = it.replace('•', '-').replace('\u2022', '-')
            pdf.multi_cell(0, 6, f"- {it_clean}")
        pdf.ln(5)
    
   
    overall = summary.get("overall_score")
    if overall is not None:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"Overall Score: {overall}", 0, 1)
        pdf.ln(5)
    
 
    write_section("Strengths", summary.get("strengths", []))
    write_section("Areas to Improve", summary.get("improvements", []))
    write_section("Suggested Resources", summary.get("resources", []))
    
    
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Per-question Feedback", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    for i, row in enumerate(qa_rows, 1):
       
        question = row.get('question', '').encode('latin-1', 'replace').decode('latin-1')
        answer = row.get('answer', '').encode('latin-1', 'replace').decode('latin-1')
        feedback = row.get('feedback', '').encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 6, f"Q{i}: {question}")
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, f"Answer: {answer}")
        pdf.multi_cell(0, 6, f"Score: {row.get('score', '')}")
        
        if feedback:
            pdf.multi_cell(0, 6, f"Feedback: {feedback}")
        
        pdf.ln(5)
    
    try:
        return pdf.output(dest="S").encode("latin-1", "replace")
    except UnicodeEncodeError:
      
        try:
            return pdf.output(dest="S").encode("utf-8")
        except:
            return None


def generate_questions(role: str, domain: Optional[str], mode: str, n: int) -> List[Dict[str, str]]:
    """
    Generate interview questions using DuckDuckGo search
    """
    query = f"{mode} interview questions for {role}"
    if domain:
        query += f" with {domain} specialization"
    
    search_results = search_with_fallback(query, max_results=5)
    
    if search_results:
     
        questions = []
        for result in search_results:
         
            sentences = re.split(r'[.!?]', result['snippet'])
            for sentence in sentences:
                if len(sentence) > 20 and any(keyword in sentence.lower() for keyword in ['what', 'how', 'why', 'describe', 'explain', 'tell']):
                    questions.append({
                        "q": sentence.strip(),
                        "topic": result['title'],
                        "difficulty": "medium",
                        "type": mode.lower()
                    })
        
        if questions:
            return questions[:n]
    
    
    if mode == "Technical":
        key = (role, (domain or "").lower())
        return FALLBACK_TECH_QUESTIONS.get(key, FALLBACK_TECH_QUESTIONS[("Software Engineer", "frontend")])[:n]
    else:
        return FALLBACK_BEHAV_QUESTIONS.get(role, FALLBACK_BEHAV_QUESTIONS["Software Engineer"])[:n]


def evaluate_with_search(mode: str, role: str, domain: Optional[str], question: str, answer: str) -> Dict[str, Any]:
    """
    Evaluate answers using DuckDuckGo search for reference material
    """
   
    query = f"how to evaluate {mode.lower()} interview answers for {question}"
    search_results = search_with_fallback(query, max_results=3)
    
   
    wc = len(answer.split())
    has_num = bool(re.search(r"\b\d+(\.\d+)?%?\b|ms|sec|minute|hour|users|requests|throughput|latency|revenue|cost", answer, re.I))
    has_star = bool(re.search(r"(situation|task|action|result|star)", answer, re.I))
    has_tech = bool(re.search(r"(problem|approach|design|trade-?off|decision|result|outcome)", answer, re.I))
    
    is_short = wc < 30
    is_vague = any(word in answer.lower() for word in ["idk", "i don't know", "not sure", "not certain", "tbh", "I don't know", "IDK","No idea", "Uhm", "Yes"])
    is_detailed = wc > 80 and not is_vague
   
    tips = []
    strengths = []
    
    if is_vague:
        tips.append("Try to provide a more substantial answer even if you're unsure.")
        tips.append("Mention what you would do to find the answer if you don't know it.")
    elif is_short:
        tips.append("Elaborate more on your answer with specific details.")
        tips.append("Provide examples or experiences to support your points.")
    elif is_detailed:
        strengths.append("Provided a detailed response")
    
    if wc > 140:
        tips.append("Shorten to ~90s; headline first.")
    if mode == "Behavioral" and not has_star:
        tips.append("Use STAR: Situation → Task → Action → Result.")
    if mode == "Technical" and not has_tech:
        tips.append("Use Problem → Options/Trade-offs → Decision → Result.")
    if not has_num and mode == "Technical":
        tips.append("Quantify impact or scale with metrics.")
    
    if wc <= 140 and not is_short:
        strengths.append("Concise")
    if has_num:
        strengths.append("Uses metrics")
    if (mode == "Behavioral" and has_star) or (mode == "Technical" and has_tech):
        strengths.append("Clear structure")
    
   
    base_score = 6.0
    if is_vague:
        base_score = 3.0
    elif is_short:
        base_score = 4.0
    elif is_detailed:
        base_score = 7.5
    
    score = max(1, min(10, base_score + 
                        (1.0 if strengths else 0) - 
                        (0.5 if tips else 0) +
                        (1.0 if has_num else 0) +
                        (1.0 if has_star or has_tech else 0)))
    
   
    search_insights = []
    for result in search_results:
        search_insights.append(f"According to {result['title']}: {result['snippet'][:100]}...")
    
   
    feedback_parts = []
    if strengths:
        feedback_parts.append("Good aspects: " + ", ".join(strengths) + ".")
    if tips:
        feedback_parts.append("Areas for improvement: " + "; ".join(tips) + ".")
    
   
    if "performance" in question.lower() and "react" in question.lower():
        feedback_parts.append("For React performance, consider discussing: code splitting, memoization, virtualization, bundle optimization, or lazy loading.")
    elif "database" in question.lower() and "index" in question.lower():
        feedback_parts.append("For database indexing, consider discussing: B-tree structure, covering indexes, query optimization, or index maintenance.")
    
    feedback = " ".join(feedback_parts) if feedback_parts else "Try to provide more specific examples and details in your answer."
    
    return {
        "score": round(score, 1),
        "feedback": feedback,
        "reasoning": "Evaluation based on answer structure, content, and relevance." + (" " + " ".join(search_insights) if search_insights else ""),
        "tags": ["structure", "specificity", "relevance"],
        "improvements": tips + ["Add concrete examples.", "Explain your thought process more clearly."]
    }


def heuristic_eval(mode: str, question: str, answer: str) -> Dict[str, Any]:
    wc = len(answer.split())
    has_num = bool(re.search(r"\b\d+(\.\d+)?%?\b|ms|sec|minute|hour|users|requests|throughput|latency|revenue|cost", answer, re.I))
    has_star = bool(re.search(r"(situation|task|action|result|star)", answer, re.I))
    has_tech = bool(re.search(r"(problem|approach|design|trade-?off|decision|result|outcome)", answer, re.I))
    
  
    is_short = wc < 30
    is_vague = any(word in answer.lower() for word in ["idk", "i don't know", "not sure", "not certain", "tbh"])
    is_detailed = wc > 80 and not is_vague
    
    tips = []
    strengths = []
    
    if is_vague:
        tips.append("Try to provide a more substantial answer even if you're unsure.")
        tips.append("Mention what you would do to find the answer if you don't know it.")
    elif is_short:
        tips.append("Elaborate more on your answer with specific details.")
        tips.append("Provide examples or experiences to support your points.")
    elif is_detailed:
        strengths.append("Provided a detailed response")
    
    if wc > 140:
        tips.append("Shorten to ~90s; headline first.")
    if mode == "Behavioral" and not has_star:
        tips.append("Use STAR: Situation → Task → Action → Result.")
    if mode == "Technical" and not has_tech:
        tips.append("Use Problem → Options/Trade-offs → Decision → Result.")
    if not has_num and mode == "Technical":
        tips.append("Quantify impact or scale with metrics.")
    
    if wc <= 140 and not is_short:
        strengths.append("Concise")
    if has_num:
        strengths.append("Uses metrics")
    if (mode == "Behavioral" and has_star) or (mode == "Technical" and has_tech):
        strengths.append("Clear structure")
    
    base_score = 6.0
    if is_vague:
        base_score = 3.0
    elif is_short:
        base_score = 4.0
    elif is_detailed:
        base_score = 7.5
    
    score = max(1, min(10, base_score + 
                        (1.0 if strengths else 0) - 
                        (0.5 if tips else 0) +
                        (1.0 if has_num else 0) +
                        (1.0 if has_star or has_tech else 0)))
    
    feedback_parts = []
    if strengths:
        feedback_parts.append("Good aspects: " + ", ".join(strengths) + ".")
    if tips:
        feedback_parts.append("Areas for improvement: " + "; ".join(tips) + ".")
  
    if "performance" in question.lower() and "react" in question.lower():
        feedback_parts.append("For React performance, consider discussing: code splitting, memoization, virtualization, bundle optimization, or lazy loading.")
    elif "database" in question.lower() and "index" in question.lower():
        feedback_parts.append("For database indexing, consider discussing: B-tree structure, covering indexes, query optimization, or index maintenance.")
    
    feedback = " ".join(feedback_parts) if feedback_parts else "Try to provide more specific examples and details in your answer."
    
    return {
        "score": round(score, 1),
        "feedback": feedback,
        "reasoning": "Heuristic scoring based on answer quality and relevance.",
        "tags": ["structure", "specificity", "relevance"],
        "improvements": tips + ["Add concrete examples.", "Explain your thought process more clearly."]
    }


def init_state():
    st.session_state.setdefault("step", "setup")  
    st.session_state.setdefault("role", "Software Engineer")
    st.session_state.setdefault("domain", "")
    st.session_state.setdefault("mode", "Technical")
    st.session_state.setdefault("nq", 3)
    st.session_state.setdefault("search_enabled", True)
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("idx", 0)
    st.session_state.setdefault("rows", [])
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("summary", None)

def start_interview(role: str, domain: Optional[str], mode: str, nq: int):
    qs = generate_questions(role, domain, mode, nq)
    
  
    qs = qs[:nq] + qs[:max(0, nq - len(qs))]
    st.session_state.questions = qs
    st.session_state.idx = 0
    st.session_state.rows = []
    st.session_state.messages = []
    st.session_state.step = "interview"

def current_q() -> Optional[Dict[str, str]]:
    idx = st.session_state.idx
    qs = st.session_state.questions
    return qs[idx] if 0 <= idx < len(qs) else None

def accept_and_next(eval_obj: Dict[str, Any], user_answer: str):
    q = current_q()
    if not q:
        return
    st.session_state.rows.append(
        {
            "question": q.get("q", ""),
            "answer": user_answer,
            "score": eval_obj.get("score", 0),
            "feedback": eval_obj.get("feedback", ""),
            "reasoning": eval_obj.get("reasoning", ""),
            "tags": ", ".join(eval_obj.get("tags", [])),
            "improvements": "; ".join(eval_obj.get("improvements", [])),
            "topic": q.get("topic", ""),
            "difficulty": q.get("difficulty", ""),
            "type": q.get("type", ""),
        }
    )
    st.session_state.idx += 1
    nxt = current_q()
    if nxt:
        st.session_state.messages.append({"role": "assistant", "content": nxt["q"]})
    else:
        st.session_state.step = "summary"

def compute_summary() -> Dict[str, Any]:
    rows = st.session_state.rows
    
    role = st.session_state.role
    domain = st.session_state.domain or "general"
    mode = st.session_state.mode
  
    improvement_query = f"how to improve {mode.lower()} interview skills for {role}"
    if domain != "general":
        improvement_query += f" {domain}"
    
    search_results = search_with_fallback(improvement_query, max_results=3)
    
    resources = []
    for result in search_results:
        resources.append(f"{result['title']} - {result['url']}")
    

    if not resources:
        resources = [
            "System Design Primer - GitHub",
            "STAR Method Guide - Coursera", 
            "Cracking the Coding Interview - McDowell"
        ]
    
    
    scores = [r.get("score", 0) for r in rows if isinstance(r.get("score"), (int, float))]
    
    
    strengths = []
    improvements = []
    
    avg_score = sum(scores)/len(scores) if scores else 0
    
    if avg_score >= 7:
        strengths.extend(["Strong technical knowledge", "Good communication skills", "Well-structured answers"])
        improvements.extend(["Work on time management", "Include more specific examples"])
    elif avg_score >= 5:
        strengths.extend(["Adequate knowledge base", "Reasonable communication"])
        improvements.extend(["Practice more interview questions", "Work on answer structure", "Include metrics in responses"])
    else:
        strengths.extend(["Willingness to learn", "Basic understanding of concepts"])
        improvements.extend(["Study fundamental concepts", "Practice with mock interviews", "Work on communication skills"])
    
    return {
        "strengths": strengths,
        "improvements": improvements,
        "resources": resources,
        "overall_score": round(avg_score, 1) if scores else None
    }


st.set_page_config(page_title=APP_TITLE, page_icon="LOGO.png", layout="wide")
init_state()

with st.sidebar:
    st.header("Settings")
    st.session_state.search_enabled = st.checkbox("Enable Web Search", value=st.session_state.get("search_enabled", True))
    st.markdown(f"**Search Engine**: {SEARCH_ENGINE}")
    st.info("Uses web search to enhance question generation and evaluation.")


st.title(APP_TITLE)
st.caption("Simulate a short interview (technical or behavioral) using DuckDuckGo search for question generation and evaluation.")


if st.session_state.step == "setup":
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.role = st.selectbox("Target Role", ["Software Engineer", "Product Manager", "Data Analyst", "Data Scientist", "DevOps Engineer"], index=0)
        st.session_state.domain = st.text_input("Domain (optional)", value=st.session_state.domain)
        st.session_state.mode = st.radio("Interview Mode", ["Technical", "Behavioral"], index=0, horizontal=True)
    with c2:
        st.session_state.nq = st.slider("Number of questions", 3, 6, value=st.session_state.nq)
        st.markdown("Pick options and start the mock interview.")
    if st.button("Continue → Meet Interviewer", use_container_width=True):
        st.session_state.step = "interviewer"

elif st.session_state.step == "interviewer":
    behavioral = st.session_state.mode == "Behavioral"
    name = "Jordan Lee (People Manager)" if behavioral else "Alex Rivera (Senior Engineer)"
    st.markdown(f"### Interview Preview — {st.session_state.mode} — {st.session_state.role}{' — ' + st.session_state.domain if st.session_state.domain else ''}")
    st.write("Interviewer:", name)
    st.write("- Keep answers under 90s")
    st.write("- Focus on decisions, trade-offs and measurable outcomes" if not behavioral else "- Use STAR: Situation → Task → Action → Result")
    col_back, col_start = st.columns([1, 1])
    if col_back.button("← Back"):
        st.session_state.step = "setup"
    if col_start.button("I'm Ready → Start Interview"):
        start_interview(st.session_state.role, (st.session_state.domain or None), st.session_state.mode, st.session_state.nq)


elif st.session_state.step == "interview":
    q = current_q()
    st.markdown(f"### Interview — {st.session_state.mode} — {st.session_state.role}{' — ' + st.session_state.domain if st.session_state.domain else ''}")
    
   
    cols = st.columns(2)
    with cols[0]:
        st.image("BOT.jpg" , width=72)
        st.markdown("**InterviewBot**")
    with cols[1]:
        st.image("CANDIDATE.jpg" , width=72)
        st.markdown("**Candidate**")

   
    if not st.session_state.messages and q:
        st.session_state.messages.append({"role": "assistant", "content": q["q"]})

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Answer here… (Enter to submit • Shift+Enter for newline)")

    if user_msg and q:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        
        eval_obj = evaluate_with_search(
            st.session_state.mode, 
            st.session_state.role, 
            (st.session_state.domain or None), 
            q["q"], 
            user_msg
        )

        with st.chat_message("assistant"):
            st.markdown(f"**Feedback — Score {eval_obj.get('score', 0)}/10**\n\n{eval_obj.get('feedback','')}")
        
        accept_and_next(eval_obj, user_msg)
        nxt = current_q()
        if nxt:
            st.session_state.messages.append({"role": "assistant", "content": nxt["q"]})
            with st.chat_message("assistant"):
                st.markdown(nxt["q"])
                meta = " | ".join([b for b in [f"Topic: {nxt.get('topic')}" if nxt.get("topic") else "", f"Difficulty: {nxt.get('difficulty')}" if nxt.get("difficulty") else "", f"Type: {nxt.get('type')}" if nxt.get("type") else ""] if b])
                if meta:
                    st.caption(meta)
        else:
            st.session_state.messages.append({"role": "assistant", "content": "🎉 Interview Complete! Open the summary below."})
            st.session_state.step = "summary"

    c = st.columns([1, 1, 1])
    if c[0].button("Retry"):
        while st.session_state.messages and st.session_state.messages[-1]["role"] in ("assistant", "user"):
            st.session_state.messages.pop()
    if c[1].button("Skip"):
        q = current_q()
        if q:
            st.session_state.rows.append({"question": q["q"], "answer": "(skipped)", "score": 0, "feedback": "Question skipped.", "reasoning": "", "tags": "skipped", "improvements": "Attempt every question."})
            st.session_state.idx += 1
            nxt = current_q()
            if nxt:
                st.session_state.messages.append({"role": "assistant", "content": nxt["q"]})
            else:
                st.session_state.step = "summary"
    if c[2].button("End Interview"):
        st.session_state.step = "summary"

elif st.session_state.step == "summary":
    if st.session_state.summary is None:
        st.session_state.summary = compute_summary()
    s = st.session_state.summary
    st.subheader("Final Summary")
    if s.get("overall_score") is not None:
        st.metric("Overall Score", s["overall_score"])
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Strengths**")
        for it in s.get("strengths", []):
            st.write(f"• {it}")
    with c2:
        st.markdown("**Areas to Improve**")
        for it in s.get("improvements", []):
            st.write(f"• {it}")
    with c3:
        st.markdown("**Suggested Resources**")
        for it in s.get("resources", []):
            st.write(f"• {it}")

    st.divider()
    st.subheader("Per-question Feedback")
    df = pd.DataFrame(st.session_state.rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    jbytes = export_json(s, st.session_state.rows)
    st.download_button("Download JSON", data=jbytes, file_name="interview_session.json", mime="application/json")
    cbytes = export_csv(st.session_state.rows)
    st.download_button("Download CSV", data=cbytes, file_name="interview_session.csv", mime="text/csv")
    if HAS_FPDF:
        pbytes = export_pdf(s, st.session_state.rows)
        if pbytes:
            st.download_button("Download PDF", data=pbytes, file_name="interview_summary.pdf", mime="application/pdf")
    else:
        st.caption("Install 'fpdf' to enable PDF export: pip install fpdf")

    if st.button("Start New Interview"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        init_state()
