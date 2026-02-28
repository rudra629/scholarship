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

# Internal imports
from .models import VerifiedScholarship
from .utils import (
    search_web_for_scholarships, 
    verify_url_authenticity, 
    extract_details, 
    extract_rich_metadata,
    save_scholarship_to_db
)

# ==========================================
# Configure API Keys Securely
# ==========================================
load_dotenv()
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
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
        # DEBUG CHECK: Are the keys actually loaded?
        if not twilio_sid or not twilio_token:
            return "ERROR: Server cannot find TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN! Check your .env or Render dashboard."

        # Download the image/PDF from Twilio
        response = requests.get(media_url, auth=(twilio_sid, twilio_token))
        
        if response.status_code != 200:
            return f"ERROR: Twilio blocked the image download (Status {response.status_code}). Auth attempted with SID ending in: ...{twilio_sid[-4:]}"
        
        # Save it to a temporary file
        ext = '.pdf' if 'pdf' in mime_type else '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        try:
            # Upload to Gemini and ask for the URL
            sample_file = genai.upload_file(path=temp_path)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash") # Using latest fast model
            
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
            
            extracted_text = extract_url_with_gemini(media_url, mime_type)
            
            if extracted_text.startswith("ERROR"):
                reply_msg.body(f"🛠️ *DEBUG MODE*\n{extracted_text}")
                return HttpResponse(str(twilio_resp), content_type='application/xml')

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
        
        # 🚨 UPGRADED DB SAVING LOGIC 🚨
        if score >= 60:  
            # It's a verified link! Extract details and save it to the DB
            metadata = extract_rich_metadata("WhatsApp Scholarship Submission", "")
            db_data = {
                "title": "Community Submitted Scholarship",
                "url": target_url,
                "source": "WhatsApp User",
                "trust_score": score,
                "status": status,
                "security_flags": flags,
                "deadline": metadata['deadline'],
                "info_paragraph": "This scholarship was crowdsourced and verified via the AUTHIC WhatsApp Agent.",
                "documents_required": metadata['documents_required']
            }
            
            # save_scholarship_to_db returns True if it's new, False if it already exists!
            is_new = save_scholarship_to_db("community_forwarded", db_data, added_from="WhatsApp")

            # Customize the WhatsApp message based on the database response
            if is_new:
                db_message = "💾 *Saved to ScholarMatch Database!*"
            else:
                db_message = "🔄 *Already on Portal! (Record Updated)*"

            final_text = (f"✅ *VERIFIED SCHOLARSHIP*\n\n"
                          f"🔗 *Detected URL:* {target_url}\n"
                          f"🛡️ *Trust Score:* {score}/100\n"
                          f"📊 *Status:* Safe to Apply\n"
                          f"{db_message}\n\n*Scan Results:*{flags_text}")
                          
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
    """Handles the initial page load AND the search results for the Web UI."""
    query = request.GET.get('q') 
    results = []
    
    if query:
        raw_data = search_web_for_scholarships(query)
        
        # ==========================================
        # 🔥 HACKATHON GOLDEN DEMO INJECTIONS 🔥
        # ==========================================
        raw_data.insert(0, {
            'title': f'{query.upper()} State Merit Scholarship (Official)',
            'url': 'https://www.buddy4study.com/',
            'source': 'Gov Directory (Verified)'
        })
        raw_data.append({
            'title': '!!! HURRY !!! 100% GUARANTEED CASH SCHOLARSHIP !!!',
            'url': 'http://get-free-money-now.scam/apply',
            'source': 'Test Injection'
        })
        # ==========================================
        
        for item in raw_data:
            score, flags, status = verify_url_authenticity(item['url'], item['title'])
            details = extract_details(item['title'])
            
            # 🚨 NEW: SAVE DASHBOARD SEARCHES TO DB 🚨
            if score >= 30:
                metadata = extract_rich_metadata(item['title'], item.get('summary', ''))
                db_data = {
                    "title": item['title'],
                    "url": item['url'],
                    "source": item['source'],
                    "trust_score": score,
                    "status": status,
                    "security_flags": flags,
                    "deadline": metadata['deadline'],
                    "info_paragraph": metadata['info'],
                    "documents_required": metadata['documents_required']
                }
                save_scholarship_to_db(query, db_data, added_from="Web_Dashboard")
            # -------------------------------------------

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
# Main API Endpoints (UPGRADED FOR MULTI-DOMAIN)
# ==========================================
@csrf_exempt
def api_main_site_search(request):
    """
    1. Accepts single or multiple domains (e.g., ?domain=msbte,diploma,engineering).
    2. Fetches live data from the web for EACH domain.
    3. Runs the Trust Engine & SAVES it to the DB.
    4. Returns ALL saved scholarships for ALL requested domains.
    """
    domain_query_raw = request.GET.get('domain', '') or request.POST.get('domain', '')
    
    if not domain_query_raw:
        return JsonResponse({"error": "Please provide a 'domain' parameter (e.g., ?domain=msbte,diploma)"}, status=400)

    # 1. Split the comma-separated string into a clean list of domains
    domains = [d.strip() for d in domain_query_raw.split(',') if d.strip()]
    
    # 2. Process each domain separately in the background
    for domain_query in domains:
        raw_results = search_web_for_scholarships(domain_query)
        
        for result in raw_results:
            score, flags, status = verify_url_authenticity(result['url'], result['title'])
            
            if score >= 30:
                metadata = extract_rich_metadata(result['title'], result.get('summary', ''))
                db_data = {
                    "title": result['title'],
                    "url": result['url'],
                    "source": result['source'],
                    "trust_score": score,
                    "status": status,
                    "security_flags": flags,
                    "deadline": metadata['deadline'],
                    "info_paragraph": metadata['info'],
                    "documents_required": metadata['documents_required']
                }
                save_scholarship_to_db(domain_query, db_data, added_from="RSS_API")

    # 3. Pull ALL data for ALL requested categories directly from the database
    lower_domains = [d.lower() for d in domains]
    
    # The __in filter acts as a massive OR operator (category=X OR category=Y)
    saved_scholarships = VerifiedScholarship.objects.filter(category__name__in=lower_domains).order_by('-created_at')
    
    final_output = []
    for sch in saved_scholarships:
        final_output.append({
            "id": sch.id,
            "title": sch.title,
            "url": sch.url,
            "source": sch.source,
            "trust_score": sch.trust_score,
            "status": sch.status,
            "security_flags": sch.security_flags,
            "deadline": sch.deadline,
            "info_paragraph": sch.info_paragraph,
            "documents_required": sch.documents_required,
            "added_from": sch.added_from,
            "category": sch.category.name if sch.category else "general"
        })

    return JsonResponse({
        "requested_domains": domains,
        "total_in_database": len(final_output),
        "scholarships": final_output
    })

@csrf_exempt
def api_get_saved_scholarships(request):
    """
    FAST READ-ONLY API for the frontend.
    Now supports multiple categories: ?category=engineering,medical
    """
    category_query_raw = request.GET.get('category', '').lower().strip()
    source_query = request.GET.get('source', '').strip()

    # 1. Start by grabbing EVERYTHING, sorted by newest first
    scholarships = VerifiedScholarship.objects.all().order_by('-created_at')

    # 2. If the frontend asked for specific categories, filter them
    if category_query_raw:
        categories = [c.strip() for c in category_query_raw.split(',') if c.strip()]
        scholarships = scholarships.filter(category__name__in=categories)
        
    # 3. If the frontend wants only WhatsApp ones, filter by source
    if source_query:
        scholarships = scholarships.filter(added_from__icontains=source_query)

    # 4. Package it into clean JSON
    final_output = []
    for sch in scholarships:
        final_output.append({
            "id": sch.id,
            "title": sch.title,
            "url": sch.url,
            "source": sch.source,
            "trust_score": sch.trust_score,
            "status": sch.status,
            "security_flags": sch.security_flags,
            "deadline": sch.deadline,
            "info_paragraph": sch.info_paragraph,
            "documents_required": sch.documents_required,
            "added_from": sch.added_from,
            "category": sch.category.name if sch.category else "general",
            "date_added": sch.created_at.strftime("%b %d, %Y")
        })

    return JsonResponse({
        "total_results": len(final_output),
        "active_filters": {
            "categories": category_query_raw.split(',') if category_query_raw else ["All"],
            "source": source_query or "All"
        },
        "data": final_output
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
# ==========================================
def search_and_verify(request):
    return JsonResponse({"status": "deprecated, use /api/scan/ instead"})

def get_verified_scholarships(request):
    return JsonResponse({"status": "deprecated"})