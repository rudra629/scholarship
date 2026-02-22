import feedparser
import ssl
import socket
import random
import re
from urllib.parse import urlparse
import requests

# ==========================================
#  HELPER: URL UNWRAPPER
# ==========================================
def unwrap_google_url(google_url):
    """
    Bypasses the Google News redirect to get the REAL government URL.
    """
    try:
        # We ping the link to see where it redirects us
        response = requests.head(google_url, allow_redirects=True, timeout=3)
        return response.url
    except:
        return google_url
    
# ==========================================
#  1. NLP TONE ANALYZER (The "Scam Detector")
# ==========================================
def analyze_nlp_tone(text):
    """
    Analyzes text for 'Pushy' or 'Aggressive' tones.
    """
    text = text.lower()
    penalty = 0
    flags = []

    # 1. THE "PUSHY" CHECK
    pushy_patterns = [
        "act now", "don't wait", "urgent", "immediate action", 
        "expires in", "last chance", "hurry", "limited spots"
    ]
    
    if text.count('!') > 2:
        penalty -= 15
        flags.append("Aggressive Punctuation (!!!)")

    found_pushy = [w for w in pushy_patterns if w in text]
    if found_pushy:
        penalty -= 25
        flags.append(f"Pushy Tone Detected: {', '.join(found_pushy)}")

    # 2. THE "TOO GOOD TO BE TRUE" CHECK
    guarantees = ["100% success", "guaranteed", "no selection", "direct entry", "free cash"]
    if any(g in text for g in guarantees):
        penalty -= 30
        flags.append("Unrealistic Guarantees")

    return penalty, flags

# ==========================================
#  2. AUTHENTICITY VERIFICATION (Fixed Scoring)
# ==========================================
def verify_url_authenticity(url, title=""):
    try:
        domain = urlparse(url).netloc
    except:
        return 0, ["Invalid URL"], ""

    # Start with a Baseline Score
    trust_score = 50 
    flags = []

    # --- LAYER 1: STRICT WHITELIST (Gov & Edu) ---
    trusted_gov = ['.gov.in', '.nic.in', '.ai', 'aicte-india.org']
    trusted_edu = ['.edu.in', '.ac.in']
    
    if any(t in domain for t in trusted_gov):
        return 100, ["Official Government Source"], "High Trust"
    
    if any(t in domain for t in trusted_edu):
        return 90, ["Official Educational Institute"], "High Trust"

    # --- LAYER 2: REPUTABLE NEWS SOURCES ---
    reputable_news = ['timesofindia', 'hindustantimes', 'ndtv', 'jagran', 'careers360', 'shiksha']
    if any(news in domain for news in reputable_news):
        trust_score += 30 # Bumps them to 80 (Verified)
        flags.append("Reputable News Source")

    # --- LAYER 3: NLP TONE CHECK ---
    combined_text = f"{url} {title}"
    nlp_penalty, nlp_flags = analyze_nlp_tone(combined_text)
    
    trust_score += nlp_penalty
    flags.extend(nlp_flags)

    # --- LAYER 4: SECURITY ---
    if not url.startswith("https"):
        trust_score -= 50 # Massive penalty for HTTP
        flags.append("Insecure Connection (No SSL)")
    else:
        trust_score += 10 # Small bonus for having SSL

    # Clamp score between -100 and 100
    final_score = max(-100, min(100, trust_score))
    
    status = "Verified" if final_score > 60 else "Caution"
    if final_score < 30: status = "Risk"

    return final_score, flags, status

# ==========================================
#  3. RSS SEARCH
# ==========================================
def search_web_for_scholarships(query):
    """
    Real-time Google News RSS Search with URL Unwrapping.
    """
    print(f"📡 Rudra is scanning Google News feeds for: '{query}'...")
    
    # Re-added the missing logic to define clean_query!
    official_query = f"{query} scholarship (site:.gov.in OR site:.edu.in OR application OR apply online)"
    clean_query = official_query.replace(" ", "+")
    
    rss_url = f"https://news.google.com/rss/search?q={clean_query}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []

    try:
        print(f"🔎 Fetching: {rss_url}")
        feed = feedparser.parse(rss_url)

        if feed.entries:
            for entry in feed.entries[:8]: # Top 8 results
                
                # --- UNWRAP THE URL HERE ---
                real_url = unwrap_google_url(entry.link)
                
                results.append({
                    'title': entry.title,
                    'url': real_url, # Now passing the real .gov.in link
                    'source': entry.source.title if hasattr(entry, 'source') else 'Google News'
                })
        else:
            print("⚠️ No live news found.")

    except Exception as e:
        print(f"❌ RSS Error: {e}")
        
    return results

# Placeholder to prevent import errors if your views call this
def extract_details(text):
    return {"income": "Check Portal", "deadline": "Open"}