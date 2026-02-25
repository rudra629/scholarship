import requests
import urllib.parse
import json

# Your clean Render URL
BASE_URL = "https://scholarship-4pxs.onrender.com/api/verify/"

def test_authic_agent(target_url):
    print(f"\n🚀 Sending URL to AUTHIC Agent: {target_url}")
    
    # We must URL-encode the link so it doesn't break the HTTP request
    encoded_url = urllib.parse.quote(target_url, safe='')
    
    # Build the final API call
    api_call = f"{BASE_URL}?url={encoded_url}"
    print(f"🔗 Full API Request: {api_call}")
    
    try:
        response = requests.get(api_call)
        response.raise_for_status() # Check for 404 or 500 errors
        
        # Parse and print the JSON response beautifully
        data = response.json()
        print("\n📦 RESPONSE PAYLOAD:")
        print(json.dumps(data, indent=4))
        
    except Exception as e:
        print(f"\n❌ Request Failed: {e}")

# ==========================================
# Run the Tests
# ==========================================
if __name__ == "__main__":
    # Test 1: A legitimate government site
    test_authic_agent("https://mahadbt.maharashtra.gov.in/")
    
    print("-" * 50)
    
    # Test 2: A fake scam site with bad keywords
    test_authic_agent("http://100percent-guaranteed-free-cash.com/apply-now")