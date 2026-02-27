# agent/views.py
from django.shortcuts import render
from django.http import JsonResponse
import urllib.parse
from .utils import search_web_for_scholarships, verify_url_authenticity, extract_details
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
from .utils import search_web_for_scholarships, verify_url_authenticity, extract_rich_metadata
@csrf_exempt
def whatsapp_webhook(request):
    """
    Listens for incoming WhatsApp messages from Twilio, scans the URL, and replies.
    """
    if request.method == 'POST':
        incoming_msg = request.POST.get('Body', '').strip()
        twilio_resp = MessagingResponse()
        reply_msg = twilio_resp.message()

        if not incoming_msg.startswith('http'):
            reply_msg.body("🤖 *AUTHIC AGENT*\nPlease send me a direct scholarship link (starting with http or https) to run a security scan.")
            return HttpResponse(str(twilio_resp), content_type='application/xml')

        score, flags, status = verify_url_authenticity(incoming_msg, title="WhatsApp Submission")
        flags_text = "\n- " + "\n- ".join(flags) if flags else "\n- None detected"
        
        if score > 60:
            final_text = (
                f"✅ *VERIFIED SCHOLARSHIP*\n\n"
                f"🛡️ *Trust Score:* {score}/100\n"
                f"📊 *Status:* Safe to Apply\n\n"
                f"*Scan Results:*{flags_text}"
            )
        elif score < 30:
            final_text = (
                f"🚨 *SCAM DETECTED* 🚨\n\n"
                f"🛡️ *Trust Score:* {score}/100\n"
                f"⚠️ *Status:* HIGH RISK\n\n"
                f"*Red Flags:*{flags_text}\n\n"
                f"⛔ _Do NOT submit Aadhar or bank details to this site!_"
            )
        else:
            final_text = (
                f"⚠️ *CAUTION ADVISED*\n\n"
                f"🛡️ *Trust Score:* {score}/100\n"
                f"👀 *Status:* Suspicious\n\n"
                f"*Scan Results:*{flags_text}"
            )

        reply_msg.body(final_text)
        return HttpResponse(str(twilio_resp), content_type='application/xml')

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

def api_scan_endpoint(request):
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
def search_and_verify(request):
    """Legacy route placeholder to prevent urls.py from crashing"""
    from django.http import JsonResponse
    return JsonResponse({"status": "deprecated, use /api/scan/ instead"})

def get_verified_scholarships(request):
    """Legacy route placeholder to prevent urls.py from crashing"""
    from django.http import JsonResponse
    return JsonResponse({"status": "deprecated"})
# Make sure to import this at the top of views.py!
# from .utils import search_web_for_scholarships, verify_url_authenticity, extract_rich_metadata

def api_main_site_search(request):
    """
    Main ScholarMatch API: Takes a domain/course query, runs the AUTHIC security scan,
    and returns rich data (Paragraph Info, Deadlines, Documents, Trust Score).
    Usage: /api/main-search/?domain=medical
    """
    domain_query = request.GET.get('domain', '')
    
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