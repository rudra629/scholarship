# agent/views.py
from django.shortcuts import render
from .utils import search_web_for_scholarships, verify_url_authenticity, extract_details

def dashboard_ui(request):
    """
    Handles the initial page load AND the search results.
    """
    query = request.GET.get('q') # Gets the keyword from the search bar
    results = []
    
    if query:
        # 1. Get raw results from the RSS/Simulation
        raw_data = search_web_for_scholarships(query)
        
        # 2. Run each result through the Authenticity Agent
        raw_data.append({
            'title': '!!! HURRY !!! 100% GUARANTEED CASH SCHOLARSHIP - NO SELECTION !!!',
            'url': 'http://get-free-money-now.scam/apply',
            'source': 'Test Injection'
        })
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

    # 3. Send results to the dashboard.html
    return render(request, 'agent/dashboard.html', {'results': results, 'query': query})

# Keep your other API views below...
def search_and_verify(request):
    # (Existing search_and_verify code)
    pass

def get_verified_scholarships(request):
    # (Existing list code)
    pass
