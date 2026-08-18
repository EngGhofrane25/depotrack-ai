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

        // 3. SKT Uyarılarını ve Tüm Tabloyu Çek
        try {
            const expRes = await fetch("http://localhost:8000/expirations");
            const expData = await expRes.json();
            updateExpirations(expData);
            if (typeof renderAllBatches === "function") {
                renderAllBatches(expData);
            }
        } catch (error) {
            console.error("SKT verileri çekilemedi:", error);
        }
        // 4. Palet Durumunu Güncelle
        if (typeof checkPalletStatus === "function") {
            checkPalletStatus();
        }
        
        // 5. Kritik Stok Uyarılarını Çek
        if (typeof checkLowStock === "function") {
            checkLowStock();
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

    // ==========================================
    // GÜN 15: PALET MODU VE İMHA (WASTE) YÖNETİMİ
    // ==========================================

    const btnStartPallet = document.getElementById("btn-start-pallet");
    const btnStopPallet = document.getElementById("btn-stop-pallet");
    const inputPalletDate = document.getElementById("pallet-date-input");
    const badgePalletStatus = document.getElementById("pallet-status-badge");
    const batchesList = document.getElementById("batches-list");

    if (btnStartPallet) {
        btnStartPallet.addEventListener("click", async () => {
            const dateValue = inputPalletDate.value;
            if (!dateValue) {
                alert("Lütfen önce bir tarih seçin!");
                return;
            }
            const dateObj = new Date(dateValue);
            try {
                await fetch("http://localhost:8000/pallet/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ expiration_date: dateObj.toISOString() })
                });
                checkPalletStatus();
            } catch (e) {
                console.error("Palet başlatılamadı:", e);
            }
        });
    }

    if (btnStopPallet) {
        btnStopPallet.addEventListener("click", async () => {
            try {
                await fetch("http://localhost:8000/pallet/stop", { method: "POST" });
                checkPalletStatus();
            } catch (e) {
                console.error("Palet durdurulamadı:", e);
            }
        });
    }

    window.checkPalletStatus = async function() {
        if (!badgePalletStatus) return;
        try {
            const res = await fetch("http://localhost:8000/pallet/status");
            const data = await res.json();
            if (data.status === "active") {
                badgePalletStatus.innerText = "AKTİF (Tarih: " + new Date(data.expiration_date).toLocaleDateString("tr-TR") + ")";
                badgePalletStatus.style.backgroundColor = "#4caf50";
                badgePalletStatus.style.color = "white";
                btnStartPallet.style.display = "none";
                btnStopPallet.style.display = "inline-block";
                inputPalletDate.disabled = true;
            } else {
                badgePalletStatus.innerText = "PASİF";
                badgePalletStatus.style.backgroundColor = "#e0e0e0";
                badgePalletStatus.style.color = "black";
                btnStartPallet.style.display = "inline-block";
                btnStopPallet.style.display = "none";
                inputPalletDate.disabled = false;
            }
        } catch (e) {
            console.error("Palet durumu alınamadı:", e);
        }
    };

    window.wasteBatch = async function(batchId) {
        if (!confirm("Bu partiyi imha etmek (çöpe atmak) istediğinize emin misiniz? Stoklardan silinecektir.")) {
            return;
        }
        try {
            await fetch(`http://localhost:8000/batches/${batchId}/waste`, { method: "POST" });
            fetchLiveStock(); // Tabloyu anında yenile
        } catch (e) {
            console.error("İmha işlemi başarısız:", e);
        }
    };

    window.renderAllBatches = function(expirations) {
        if (!batchesList) return;
        batchesList.innerHTML = "";
        
        if (expirations.length === 0) {
            batchesList.innerHTML = `<tr><td colspan="6" style="padding: 10px; text-align: center;">Depoda kayıtlı koli bulunmamaktadır.</td></tr>`;
            return;
        }
        
        expirations.forEach(exp => {
            const tr = document.createElement("tr");
            tr.style.borderBottom = "1px solid #eee";
            
            let statusText = "Güvenli";
            let statusColor = "green";
            if (exp.status === "expired") {
                statusText = "Süresi Geçmiş!";
                statusColor = "red";
            } else if (exp.status === "danger") {
                statusText = "Kritik";
                statusColor = "darkorange";
            } else if (exp.status === "warning") {
                statusText = "Yaklaşıyor";
                statusColor = "#fbc02d";
            }
            
            tr.innerHTML = `
                <td style="padding: 10px;">#${exp.batch_id}</td>
                <td style="padding: 10px; font-weight: bold;">${exp.product_name}</td>
                <td style="padding: 10px;">${exp.quantity} Adet</td>
                <td style="padding: 10px;">${exp.expiration_date}</td>
                <td style="padding: 10px; color: ${statusColor}; font-weight: bold;">${statusText} (${exp.days_left} gün)</td>
                <td style="padding: 10px;">
                    <button onclick="wasteBatch(${exp.batch_id})" style="background-color: #d32f2f; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">İmha Et</button>
                </td>
            `;
            batchesList.appendChild(tr);
        });
    };

    // ==========================================
    // GÜN 16: KRİTİK STOK VE TOPTANCI SİPARİŞİ
    // ==========================================
    
    // Oturum boyunca sipariş verilen ürünleri tutalım ki tekrar tekrar buton çıkmasın
    const orderedProductsThisSession = new Set();
    
    window.checkLowStock = async function() {
        const container = document.getElementById("low-stock-alerts-container");
        const list = document.getElementById("low-stock-list");
        if (!container || !list) return;
        
        try {
            const res = await fetch("http://localhost:8000/alerts/low-stock");
            const alerts = await res.json();
            
            // Eğer daha önce sipariş verdiğimiz ürünler varsa listeden gizleyelim
            const activeAlerts = alerts.filter(a => !orderedProductsThisSession.has(a.product_id));
            
            if (activeAlerts.length === 0) {
                container.style.display = "none";
                return;
            }
            
            container.style.display = "block";
            list.innerHTML = "";
            
            activeAlerts.forEach(alert => {
                const item = document.createElement("div");
                item.style.backgroundColor = "#fff";
                item.style.border = "1px solid #ffcc80";
                item.style.padding = "10px 15px";
                item.style.borderRadius = "8px";
                item.style.display = "flex";
                item.style.justifyContent = "space-between";
                item.style.alignItems = "center";
                
                item.innerHTML = `
                    <div>
                        <strong style="font-size: 16px;">${alert.product_name}</strong> stoğu kritik seviyede! 
                        <span style="color: #d32f2f; font-weight: bold;">(Mevcut: ${alert.current_quantity} Kutu / Sınır: ${alert.critical_threshold})</span>
                    </div>
                    <div style="background-color: #e3f2fd; color: #1976d2; padding: 8px 15px; border-radius: 4px; font-weight: bold; font-size: 14px; display: flex; align-items: center; gap: 5px;">
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                        Görevliye Onay Maili İletildi
                    </div>
                `;
                list.appendChild(item);
            });
            
        } catch (e) {
            console.error("Kritik stok verisi çekilemedi:", e);
        }
    };
    
    // Not: window.placeOrder fonksiyonu silindi çünkü artık sistem 
    // görevlinin e-postasındaki link üzerinden arka ucu (GET /approve-order) tetikliyor.
});
