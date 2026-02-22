# agent/views.py
from django.shortcuts import render
from django.http import JsonResponse
import urllib.parse
from .utils import search_web_for_scholarships, verify_url_authenticity, extract_details

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