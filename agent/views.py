# agent/views.py
import os
import re
import tempfile
import urllib.parse
import requests
import google.generativeai as genai

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

from .utils import (
    search_web_for_scholarships, 
    verify_url_authenticity, 
    extract_details, 
    extract_rich_metadata
)

# ==========================================
# Configure Gemini API Securely
# ==========================================
load_dotenv()
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
# Grab the key securely from the .env file (or Render Environment Variables)
gemini_key = os.getenv("GEMINI_API_KEY")

if gemini_key:
    genai.configure(api_key=gemini_key)
else:
    print("⚠️ WARNING: GEMINI_API_KEY is missing from your .env file or Render Dashboard!")

# ==========================================
# AI Helper Functions
# ==========================================
def extract_url_with_gemini(media_url, mime_type):
    """Downloads Twilio media, passes it to Gemini Vision, and extracts the URL."""
    try:
        # 1. Grab credentials directly inside the function
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        # DEBUG CHECK: Are the keys actually loaded?
        if not twilio_sid or not twilio_token:
            return "ERROR: Server cannot find TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN! Check your .env or Render dashboard."

        # 2. Download the image/PDF from Twilio
        response = requests.get(media_url, auth=(twilio_sid, twilio_token))
        
        if response.status_code != 200:
            # Tell us exactly what Twilio is complaining about
            return f"ERROR: Twilio blocked the image download (Status {response.status_code}). Auth attempted with SID ending in: ...{twilio_sid[-4:]}"
        
        # 3. Save it to a temporary file
        ext = '.pdf' if 'pdf' in mime_type else '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        try:
            # 4. Upload to Gemini and ask for the URL
            sample_file = genai.upload_file(path=temp_path)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            
            prompt = "Extract the website link (URL) from this image. Reply ONLY with the raw URL starting with http:// or https://."
            result = model.generate_content([sample_file, prompt])
            extracted_text = result.text.strip()
        except Exception as ai_error:
            extracted_text = f"ERROR: Gemini API failed -> {str(ai_error)}"
        finally:
            # Clean up the temp file
            os.remove(temp_path)
            
        return extracted_text
    except Exception as e:
        return f"ERROR: System crashed -> {str(e)}"
# ==========================================
# WhatsApp Webhook View
# ==========================================
@csrf_exempt
def whatsapp_webhook(request):
    """
    Listens for WhatsApp messages. Supports both direct text URLs 
    and Image/PDF uploads using Gemini AI Vision.
    """
    if request.method == 'POST':
        incoming_msg = request.POST.get('Body', '').strip()
        num_media = int(request.POST.get('NumMedia', 0))
        
        twilio_resp = MessagingResponse()
        reply_msg = twilio_resp.message()
        
        target_url = None

        # --- BRANCH A: USER SENT AN IMAGE OR PDF ---
        if num_media > 0:
            media_url = request.POST.get('MediaUrl0')
            mime_type = request.POST.get('MediaContentType0')
            
            # Extract text using Gemini
            extracted_text = extract_url_with_gemini(media_url, mime_type)
            
            # Debug Catch: If extraction failed, send the error to WhatsApp so you can fix it
            if extracted_text.startswith("ERROR"):
                reply_msg.body(f"🛠️ *DEBUG MODE*\n{extracted_text}")
                return HttpResponse(str(twilio_resp), content_type='application/xml')

            # Use regex to perfectly grab the link out of the AI's response
            url_match = re.search(r'(https?://[^\s]+)', extracted_text)
            
            if url_match:
                target_url = url_match.group(1)
            else:
                reply_msg.body("🤖 *AUTHIC AGENT*\nI scanned your document but couldn't find a clear web address. Please ensure the image contains a valid URL starting with http/https.")
                return HttpResponse(str(twilio_resp), content_type='application/xml')

        # --- BRANCH B: USER SENT A TEXT MESSAGE ---
        else:
            url_match = re.search(r'(https?://[^\s]+)', incoming_msg)
            if url_match:
                target_url = url_match.group(1)
            else:
                reply_msg.body("🤖 *AUTHIC AGENT*\nPlease send me a direct scholarship link or upload a screenshot/PDF of the scholarship to run a security scan.")
                return HttpResponse(str(twilio_resp), content_type='application/xml')

        # --- RUN THE TRUST ENGINE ON THE EXTRACTED URL ---
        score, flags, status = verify_url_authenticity(target_url, title="WhatsApp Submission")
        flags_text = "\n- " + "\n- ".join(flags) if flags else "\n- None detected"
        
        if score > 60:
            final_text = (f"✅ *VERIFIED SCHOLARSHIP*\n\n"
                          f"🔗 *Detected URL:* {target_url}\n"
                          f"🛡️ *Trust Score:* {score}/100\n"
                          f"📊 *Status:* Safe to Apply\n\n*Scan Results:*{flags_text}")
        elif score < 30:
            final_text = (f"🚨 *SCAM DETECTED* 🚨\n\n"
                          f"🔗 *Detected URL:* {target_url}\n"
                          f"🛡️ *Trust Score:* {score}/100\n"
                          f"⚠️ *Status:* HIGH RISK\n\n*Red Flags:*{flags_text}\n\n"
                          f"⛔ _Do NOT submit Aadhaar or bank details to this site!_")
        else:
            final_text = (f"⚠️ *CAUTION ADVISED*\n\n"
                          f"🔗 *Detected URL:* {target_url}\n"
                          f"🛡️ *Trust Score:* {score}/100\n"
                          f"👀 *Status:* Suspicious\n\n*Scan Results:*{flags_text}")

        reply_msg.body(final_text)
        return HttpResponse(str(twilio_resp), content_type='application/xml')

# ==========================================
# Web Dashboard View
# ==========================================
def dashboard_ui(request):
    """
    Handles the initial page load AND the search results for the Web UI.
    """
    query = request.GET.get('q') 
    results = []
    
    if query:
        # 1. Get raw results from the RSS feed
        raw_data = search_web_for_scholarships(query)
        
        # ==========================================
        # 🔥 HACKATHON GOLDEN DEMO INJECTIONS 🔥
        # ==========================================
        
        # A. The Perfect Safe Link (Guaranteed to trigger iframe preview!)
        raw_data.insert(0, {
            'title': f'{query.upper()} State Merit Scholarship (Official)',
            'url': 'https://www.buddy4study.com/',
            'source': 'Gov Directory (Verified)'
        })

        # B. The Scam Link
        raw_data.append({
            'title': '!!! HURRY !!! 100% GUARANTEED CASH SCHOLARSHIP !!!',
            'url': 'http://get-free-money-now.scam/apply',
            'source': 'Test Injection'
        })
        # ==========================================
        
        # 3. Run each result through the Authenticity Agent
        for item in raw_data:
            score, flags, analysis = verify_url_authenticity(item['url'], item['title'])
            details = extract_details(item['title'])
            
            results.append({
                'title': item['title'],
                'url': item['url'],
                'source': item['source'],
                'trust_score': score,
                'flags': flags,
                'details': details
            })

    return render(request, 'agent/dashboard.html', {'results': results, 'query': query})

# ==========================================
# Main API Endpoints
# ==========================================
@csrf_exempt
def api_main_site_search(request):
    """
    Main ScholarMatch API: Takes a domain/course query, runs the AUTHIC security scan,
    and returns rich data (Paragraph Info, Deadlines, Documents, Trust Score).
    Usage: /api/main-search/?domain=medical
    """
    # Supports both GET and POST requests gracefully
    domain_query = request.GET.get('domain', '') or request.POST.get('domain', '')
    
    if not domain_query:
        return JsonResponse({"error": "Please provide a 'domain' parameter (e.g., ?domain=medical)"}, status=400)

    # 1. Fetch raw web links based on the student's domain (e.g., "diploma")
    raw_results = search_web_for_scholarships(domain_query)
    
    final_results = []
    
    # 2. Run the Trust Engine and Metadata Extractor on each link
    for result in raw_results:
        # Get Security Score
        score, flags, status = verify_url_authenticity(result['url'], result['title'])
        
        # Get Paragraph, Deadline, and Documents
        metadata = extract_rich_metadata(result['title'], result.get('summary', ''))
        
        final_results.append({
            "title": result['title'],
            "url": result['url'],
            "source": result['source'],
            "trust_score": score,
            "status": status,
            "security_flags": flags,
            "deadline": metadata['deadline'],
            "info_paragraph": metadata['info'],
            "documents_required": metadata['documents_required']
        })

    # 3. Return a beautifully formatted JSON for the main site frontend
    return JsonResponse({
        "student_domain": domain_query,
        "total_found": len(final_results),
        "scholarships": final_results
    })

def api_scan_endpoint(request):
    """Basic JSON response for the Trust Engine."""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({"error": "Please provide a query parameter (e.g., ?q=msbte)"}, status=400)

    raw_results = search_web_for_scholarships(query)
    processed_results = []
    for result in raw_results:
        score, flags, status = verify_url_authenticity(result['url'], result['title'])
        result['trust_score'] = score
        result['flags'] = flags
        result['status'] = status
        processed_results.append(result)

    return JsonResponse({
        "target_query": query,
        "results_found": len(processed_results),
        "data": processed_results
    })

def api_verify_url(request):
    """WhatsApp verification bridge API."""
    encoded_url = request.GET.get('url', '')
    if not encoded_url:
        return JsonResponse({"error": "Please provide a url parameter"}, status=400)

    target_url = urllib.parse.unquote(encoded_url)
    score, flags, status = verify_url_authenticity(target_url, title="WhatsApp Submission")
    
    is_safe = True if score > 60 else False
    is_scam = True if score < 30 else False

    return JsonResponse({
        "analyzed_url": target_url,
        "trust_score": score,
        "status": status,
        "is_safe": is_safe,
        "is_scam": is_scam,
        "flags_detected": flags
    })

# ==========================================
# Legacy Route Placeholders 
# (Kept to prevent urls.py from crashing)
# ==========================================
def search_and_verify(request):
    """Legacy route placeholder to prevent urls.py from crashing"""
    return JsonResponse({"status": "deprecated, use /api/scan/ instead"})

def get_verified_scholarships(request):
    """Legacy route placeholder to prevent urls.py from crashing"""
    return JsonResponse({"status": "deprecated"})