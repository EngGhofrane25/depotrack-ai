import urllib.request
try:
    req = urllib.request.Request('http://localhost:8000/stock')
    with urllib.request.urlopen(req) as response:
        print("Backend is responding!")
except Exception as e:
    print(f"Backend error: {e}")
