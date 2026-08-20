import re

with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace fetch for API requests that need auth with a custom fetchWithAuth

fetch_auth_js = '''
    // GÜVENLİK İÇİN YENİ FETCH YARDIMCISI
    window.fetchWithAuth = async function(url, options = {}) {
        const token = localStorage.getItem("adminToken");
        if (!options.headers) options.headers = {};
        if (token) options.headers["Authorization"] = "Bearer " + token;
        
        const response = await fetch(url, options);
        if (response.status === 401) {
            document.getElementById("login-overlay").style.display = "flex";
            alert("Oturumunuz süresi doldu veya yetkisiz erişim! Lütfen tekrar giriş yapın.");
        }
        return response;
    };
'''

content = content.replace('// GoN 10: GEREK VERTABANI BA?LANTISI (FETCH)', '// GÜN 10: GERÇEK VERİTABANI BAĞLANTISI (FETCH)\n' + fetch_auth_js)
content = content.replace('const res = await fetch("http://localhost:8000/stock/update"', 'const res = await fetchWithAuth("http://localhost:8000/stock/update"')
content = content.replace('const res = await fetch("http://localhost:8000/batches/" + batchId', 'const res = await fetchWithAuth("http://localhost:8000/batches/" + batchId')
content = content.replace('await fetch(http://localhost:8000/batches//waste', 'await fetchWithAuth(http://localhost:8000/batches//waste')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Frontend script.js patched for JWT auth.')
