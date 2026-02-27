# agent/views.py
from django.shortcuts import render
from django.http import JsonResponse
import urllib.parse
from .utils import search_web_for_scholarships, verify_url_authenticity, extract_details
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
# Make sure verify_url_authenticity is imported from .utils

@csrf_exempt  # Twilio sends POST requests without CSRF tokens, so we must exempt this view
def whatsapp_webhook(request):
    """
    Listens for incoming WhatsApp messages from Twilio, scans the URL, and replies.
    """
    if request.method == 'POST':
        # 1. Get the text message the user sent
        incoming_msg = request.POST.get('Body', '').strip()

        # 2. Prepare the Twilio Response object
        twilio_resp = MessagingResponse()
        reply_msg = twilio_resp.message()

        # 3. Basic Check: Did they actually send a link?
        if not incoming_msg.startswith('http'):
            reply_msg.body("🤖 *AUTHIC AGENT*\nPlease send me a direct scholarship link (starting with http or https) to run a security scan.")
            return HttpResponse(str(twilio_resp), content_type='application/xml')

        # 4. Run your Trust Engine!
        score, flags, status = verify_url_authenticity(incoming_msg, title="WhatsApp Submission")

        # 5. Format a beautiful WhatsApp reply
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

        # 6. Send the message back to the user
        reply_msg.body(final_text)
        return HttpResponse(str(twilio_resp), content_type='application/xml')
def dashboard_ui(request):
    """
    Handles the initial page load AND the search results for the Web UI.
    """
    query = request.GET.get('q') # Gets the keyword from the search bar
    results = []
    
    if query:
        # 1. Get raw results from the RSS/Simulation
        raw_data = search_web_for_scholarships(query)
        
        # 2. Inject the test scam for demonstration (Kept as requested)
        raw_data.append({
            'title': '!!! HURRY !!! 100% GUARANTEED CASH SCHOLARSHIP - NO SELECTION !!!',
            'url': 'http://get-free-money-now.scam/apply',
            'source': 'Test Injection'
        })
        
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

    # 4. Send results to the dashboard.html
    return render(request, 'agent/dashboard.html', {'results': results, 'query': query})


def api_scan_endpoint(request):
    """
    API Endpoint for AUTHIC Search. Returns JSON results for a keyword.
    Usage: /api/scan/?q=msbte
    """
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({"error": "Please provide a query parameter (e.g., ?q=msbte)"}, status=400)

    # 1. Fetch live links
    raw_results = search_web_for_scholarships(query)
    
    # 2. Run them through the Trust Engine
    processed_results = []
    for result in raw_results:
        # We process the score just like the HTML view does
        score, flags, status = verify_url_authenticity(result['url'], result['title'])
        
        result['trust_score'] = score
        result['flags'] = flags
        result['status'] = status
        processed_results.append(result)

    # 3. Return the data as JSON
    return JsonResponse({
        "target_query": query,
        "results_found": len(processed_results),
        "data": processed_results
    })


def api_verify_url(request):
    """
    API for the WhatsApp Bot. Verifies a single direct link.
    Usage: /api/verify/?url=https://example.com/apply
    """
    encoded_url = request.GET.get('url', '')
    
    if not encoded_url:
        return JsonResponse({"error": "Please provide a url parameter (e.g., ?url=https://...)"}, status=400)

    # Decode the URL just in case the WhatsApp bot sends it URL-encoded
    target_url = urllib.parse.unquote(encoded_url)

    # Run it through Rudra's Trust Engine
    score, flags, status = verify_url_authenticity(target_url, title="WhatsApp Submission")
    
    # Determine a simple boolean for the bot to read easily
    is_safe = True if score > 60 else False
    is_scam = True if score < 30 else False

    # Return clean JSON for your teammate to format into a WhatsApp message
    return JsonResponse({
        "analyzed_url": target_url,
        "trust_score": score,
        "status": status,
        "is_safe": is_safe,
        "is_scam": is_scam,
        "flags_detected": flags
    })


# Keep your other API views below...
def search_and_verify(request):
    # (Existing search_and_verify code)
    pass

def get_verified_scholarships(request):
    # (Existing list code)
    pass