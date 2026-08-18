document.addEventListener("DOMContentLoaded", () => {
    
    // ==========================================
    // GÜN 10: GERÇEK VERİTABANI BAĞLANTISI (FETCH)
    // ==========================================
    
    // DOM Elementlerini seçelim
    const elElektronik = document.getElementById("stock-elektronik");
    const elGida = document.getElementById("stock-gida");
    const elTemizlik = document.getElementById("stock-temizlik");
    const elKirtasiye = document.getElementById("stock-kirtasiye");
    const elTekstil = document.getElementById("stock-tekstil");
    const logList = document.getElementById("log-list");

    // Stokları Ekrana Yazdır
    function updateStockDisplay(stockData) {
        elElektronik.innerText = stockData.elektronik || 0;
        elGida.innerText = stockData.gida || 0;
        elTemizlik.innerText = stockData.temizlik || 0;
        elKirtasiye.innerText = stockData.kirtasiye || 0;
        elTekstil.innerText = stockData.tekstil || 0;
    }

    function updateLogs(logs) {
        logList.innerHTML = ""; // Listeyi temizle
        
        // En son 5 hareketi göster
        const recentLogs = logs.slice(0, 5);
        
        recentLogs.forEach(log => {
            const li = document.createElement("li");
            li.className = "log-item";
            
            // Yön bilgisine göre Türkçe metin ve CSS sınıfı
            const isEntry = log.direction === "IN";
            const directionText = isEntry ? "GİRDİ" : "ÇIKTI";
            const directionClass = isEntry ? "log-entry" : "log-exit";
            
            // Ürün ID'sini İsimle eşleştir
            const productNames = {1: "Elektronik", 2: "Gıda", 3: "Tekstil", 4: "Kırtasiye", 5: "Temizlik"};
            const productName = productNames[log.product_id] || "Bilinmeyen Ürün";
            
            // Tarihi formatla
            const date = new Date(log.timestamp);
            const timeString = date.toLocaleTimeString('tr-TR');
            
            li.innerHTML = `
                <span class="${directionClass}">${directionText}</span>
                <span class="log-product">${productName}</span>
                <span class="log-time">${timeString}</span>
            `;
            
            logList.appendChild(li);
        });
    }

    // ==========================================
    // SKT (SON KULLANIM TARİHİ) GÜNCELLEME
    // ==========================================
    function updateExpirations(expirations) {
        const container = document.getElementById("expiration-alerts-container");
        const list = document.getElementById("expiration-list");
        
        // Tehlikeli (7 günden az kalan veya tarihi geçen) partileri filtrele
        const dangerousExpirations = expirations.filter(e => e.status === "danger" || e.status === "expired");
        
        if (dangerousExpirations.length === 0) {
            container.style.display = "none";
            return;
        }
        
        container.style.display = "block";
        list.innerHTML = "";
        
        dangerousExpirations.forEach(exp => {
            const item = document.createElement("div");
            item.style.backgroundColor = exp.status === "expired" ? "#b71c1c" : "#e53935";
            item.style.color = "white";
            item.style.padding = "5px 12px";
            item.style.borderRadius = "15px";
            item.style.fontSize = "13px";
            item.style.fontWeight = "500";
            item.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
            
            let timeText = exp.status === "expired" 
                ? "SKT GEÇTİ!" 
                : `Son ${exp.days_left} Gün!`;
                
            item.innerHTML = `<strong>${exp.product_name}</strong> (${exp.quantity} Koli) - ${timeText}`;
            list.appendChild(item);
        });
    }

    let previousStock = null;

    // Gerçek Sunucudan Veri Çekme Fonksiyonu
    async function fetchLiveStock() {
        // 1. Stok verisini çek
        try {
            const response = await fetch("http://localhost:8000/stock");
            const currentStock = await response.json();
            
            // Sadece görsellik için log yazdırma
            if (previousStock) {
                for (let key in currentStock) {
                    if (currentStock[key] > previousStock[key]) {
                        // Backend'den log çektiğimiz için bu kısmı geçebiliriz,
                        // ama isterseniz anlık animasyon vs koyulabilir.
                    }
                }
            }
            
            previousStock = JSON.parse(JSON.stringify(currentStock)); // Kopyasını al
            updateStockDisplay(currentStock);
        } catch (error) {
            console.error("Stok verisi çekilemedi!", error);
        }

        // 2. Hareket geçmişi (Loglar) verisini çek
        try {
            const logsRes = await fetch("http://localhost:8000/movements");
            const logsData = await logsRes.json();
            updateLogs(logsData);
        } catch (error) {
            console.error("Loglar çekilemedi:", error);
        }

        // 3. SKT Uyarılarını Çek
        try {
            const expRes = await fetch("http://localhost:8000/expirations");
            const expData = await expRes.json();
            updateExpirations(expData);
        } catch (error) {
            console.error("SKT verileri çekilemedi:", error);
        }
    }

    // Sayfa yüklendiğinde ilk veriyi çek
    fetchLiveStock();

    // Her 1 saniyede bir sunucudan güncel verileri otomatik olarak çek!
    setInterval(fetchLiveStock, 1000);

    // ==========================================
    // GÜN 13: RAPOR İNDİR BUTONU TIKLAMA OLAYI
    // ==========================================
    const downloadBtn = document.getElementById("download-report-btn");
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            // Arka uçtaki (Backend) rapor üretici endpoint'e yönlendir, tarayıcı dosyayı indirir
            window.open("http://localhost:8000/report", "_blank");
        });
    }
});
