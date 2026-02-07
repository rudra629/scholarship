"""
Free Scholarship Search - No API Key Required!
Uses DuckDuckGo search (completely free)
"""

def search_with_duckduckgo(query):
    """
    Search using DuckDuckGo (Free, No API Key Needed)
    """
    try:
        from ddgs import DDGS
        import time
        
        print(f"\n{'='*70}")
        print(f"Search Results for: '{query}'")
        print(f"{'='*70}\n")
        
        ddgs = DDGS()
        results = []
        
        # Search and collect results
        for result in ddgs.text(query, max_results=10):
            results.append(result)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. TITLE: {result.get('title', 'No title')}")
                print(f"   URL: {result.get('href', 'No URL')}")
                print(f"   DESCRIPTION: {result.get('body', 'No description')}")
                print()
        else:
            print("No results found")
            
    except ImportError:
        print("❌ Installing required package...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ddgs"])
        print("✅ Installed! Run the script again.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying alternative search method...")

def search_with_bing(query):
    """
    Alternative: Using Bing Search (Free tier available)
    """
    try:
        from bing_search_api import Search
        
        print(f"\n{'='*70}")
        print(f"Searching on Bing: '{query}'")
        print(f"{'='*70}\n")
        
        search = Search(query)
        results = search.results()
        
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Description: {result['description']}\n")
            
    except ImportError:
        print("Bing API not available, using DuckDuckGo instead...")
        search_with_duckduckgo(query)

if __name__ == "__main__":
    print("="*70)
    print("🎓 FREE Scholarship Search (No API Key Required)")
    print("="*70)
    
    # Change this to search for different terms
    query = "scholarship for 10th class"
    
    print(f"\nSearching for: '{query}'")
    print("Using DuckDuckGo (Completely Free)...\n")
    
    search_with_duckduckgo(query)
    
    print("\n" + "="*70)
    print("Try these search terms:")
    print("="*70)
    print("- 'international scholarships'")
    print("- 'scholarship programs 2024'")
    print("- 'merit scholarships'")
    print("- 'girls scholarship'")
    print("\nEdit QUERY = '...' and run again")