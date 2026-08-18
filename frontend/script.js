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

    // Arayüzdeki Son Hareketler Listesine Log Ekle (Şimdilik backend'den log çekmiyoruz, 
    // canlı stok değişimi farkı ile log yazdırabiliriz, ama şimdilik backend bağlantısını sağladık)
    function addLog(message, actionClass) {
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ":" + 
                        now.getMinutes().toString().padStart(2, '0') + ":" + 
                        now.getSeconds().toString().padStart(2, '0');

        const li = document.createElement("li");
        li.className = "log-item";
        
        li.innerHTML = `
            <span class="log-time">${timeStr}</span>
            <span class="log-action ${actionClass}">${message}</span>
        `;
        
        logList.insertBefore(li, logList.firstChild);

        if (logList.children.length > 50) {
            logList.removeChild(logList.lastChild);
        }
    }

    let previousStock = null;

    // Gerçek Sunucudan Veri Çekme Fonksiyonu
    async function fetchLiveStock() {
        try {
            const response = await fetch("http://localhost:8000/stock");
            const currentStock = await response.json();
            
            // Eğer önceki stoktan farklı bir ürün varsa log yazdır (Sadece görsellik için)
            if (previousStock) {
                for (let key in currentStock) {
                    if (currentStock[key] > previousStock[key]) {
                        addLog(`${key.toUpperCase()} Depoya Girdi`, "log-in");
                    } else if (currentStock[key] < previousStock[key]) {
                        addLog(`${key.toUpperCase()} Depodan Çıktı`, "log-out");
                    }
                }
            }
            
            previousStock = JSON.parse(JSON.stringify(currentStock)); // Kopyasını al
            updateStockDisplay(currentStock);
            
        } catch (error) {
            console.error("Sunucuya bağlanılamadı!", error);
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
