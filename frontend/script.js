
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

// Ürün bazlı toptancı e-postası için önbellekler
// supplierEmailCache: backend'deki kayıtlı değerler | pendingSupplierEdits: kullanıcı henüz kaydetmedi
var supplierEmailCache = {};
var pendingSupplierEdits = {};
window.supplierEmailCache = supplierEmailCache;
window.pendingSupplierEdits = pendingSupplierEdits;

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // GÜN 10: GERÇEK VERİTABANI BAĞLANTISI (FETCH)
    // ==========================================

    // DOM Elementlerini seçelim
    const elElektronik = document.getElementById("stock-elektronik");
    const elGıda = document.getElementById("stock-gida");
    const elTemizlik = document.getElementById("stock-temizlik");
    const elKırtasiye = document.getElementById("stock-kirtasiye");
    const elTekstil = document.getElementById("stock-tekstil");
    const logList = document.getElementById("log-list");

    // Stokları Ekrana Yazdır
    function updateStockDisplay(stockData) {
        elElektronik.innerText = stockData.elektronik || 0;
        elGıda.innerText = stockData.gida || 0;
        elTemizlik.innerText = stockData.temizlik || 0;
        elKırtasiye.innerText = stockData.kirtasiye || 0;
        elTekstil.innerText = stockData.tekstil || 0;
    }

    function updateLogs(logs) {
        console.log("[POLL] updateLogs called with", logs.length, "entries. Most recent:", logs[0]?.timestamp);
        logList.innerHTML = ""; // Listeyi temizle

        const recentLogs = logs; // Zaten backend filtreleyip gonderiyor

        recentLogs.forEach(log => {
            const li = document.createElement("li");
            li.className = "log-item";

            // Yön bilgisine göre Türkçe metin ve CSS sınıfı
            const isEntry = log.direction === "IN";
            const directionText = isEntry ? "GİRDİ" : "ÇIKTI";
            const directionColor = isEntry ? "#4ade80" : "#f87171";

            // Ürün ID'sini İsimle eşleştir
            const productNames = {1: "Elektronik", 2: "Gıda", 3: "Tekstil", 4: "Kırtasiye", 5: "Temizlik"};
            const productName = productNames[log.product_id] || "Bilinmeyen Ürün";

            // Tarihi formatla
            const date = new Date(log.timestamp);
            const timeString = date.toLocaleTimeString('tr-TR');

            li.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div>
                        <span class="log-time" style="color: #888; font-size: 0.85rem; width: 70px; display: inline-block;">${timeString}</span>
                        <span style="color: ${directionColor}; font-weight: 700; width: 60px; display: inline-block;">${directionText}</span>
                        <span class="log-product" style="font-weight: 500; margin-left: 5px;">${productName}</span>
                    </div>
                    ${true ? `<button onclick="undoMovement(${log.id})" style="background:#ff9800; color:white; border:none; padding:3px 8px; border-radius:3px; cursor:pointer; font-size:11px;">Geri Al</button>` : ''}
                </div>
            `;

            logList.appendChild(li);
        });
    }

    let chartInstance = null;

    // --- 1. Login Sistemi ---
    if (localStorage.getItem("adminToken")) {
        document.getElementById("login-overlay").style.display = "none";
        applyRoleUI();
    }

    window.performLogin = async function() {
        const u = document.getElementById("username").value;
        const p = document.getElementById("password").value;

        try {
            const res = await fetch("http://localhost:8000/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: u, password: p })
            });
            const data = await res.json();
            if (data.status === "success") {
                localStorage.setItem("adminToken", data.token);
                localStorage.setItem("userRole", data.role); // Role kaydediliyor
                document.getElementById("login-overlay").style.display = "none";
                applyRoleUI();
            } else {
                document.getElementById("login-error").innerText = "Hatalı Giriş!";
                document.getElementById("login-error").style.display = "block";
            }
        } catch (e) {
            document.getElementById("login-error").innerText = "Sunucuya bağlanılamadı.";
            document.getElementById("login-error").style.display = "block";
        }
    };

    // --- 2. Dark Mode ---
    if (localStorage.getItem("theme") === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    }

    window.toggleTheme = function() {
        if (document.documentElement.getAttribute("data-theme") === "dark") {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("theme", "light");
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
        }
    };

    // --- 3. Excel İndirme ---
    window.downloadExcel = function() {
        window.open("http://localhost:8000/export/csv", "_blank");
    };

    // --- 4. Chart.js Çizimi ---
    window.updateChart = async function() {
        try {
            const res = await fetch("http://localhost:8000/analytics", { cache: "no-store" });
            const data = await res.json();

            const ctx = document.getElementById('inventoryChart');
            if (!ctx) return;

                        const colorMap = {
                'Elektronik': '#60a5fa',
                'Gida': '#f87171',
                'Temizlik': '#4ade80',
                'Kirtasiye': '#fbbf24',
                'Tekstil': '#c084fc'
            };
            const dynamicColors = data.labels.map(label => colorMap[label] || '#999999');

            if (chartInstance) {
                chartInstance.data.labels = data.labels;
                chartInstance.data.datasets[0].data = data.data;
                chartInstance.data.datasets[0].backgroundColor = dynamicColors;
                chartInstance.update();
            } else {
                chartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: dynamicColors,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'right' } }
                    }
                });
            }
        } catch (e) {
            console.error("Grafik verisi alınamadı", e);
        }
    };

    // --- 5. Karekod (QR Code) Modalı ---
    let qrCodeObj = null;

    window.generateQR = function(batchId, productName, expDate) {
        document.getElementById('qrModal').style.display = 'flex';
        document.getElementById('qrModalTitle').innerText = `Koli #${batchId} Karekod`;
        document.getElementById('qrModalDesc').innerText = `Ürün: ${productName} | SKT: ${expDate}`;

        const qrContainer = document.getElementById('qrcode');
        qrContainer.innerHTML = ''; // Temizle

        qrCodeObj = new QRCode(qrContainer, {
            text: `DEPOTRACK-BATCHID:${batchId}|URUN:${productName}|SKT:${expDate}`,
            width: 150,
            height: 150,
            colorDark : "#000000",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        });
    };

    window.closeQRModal = function() {
        document.getElementById('qrModal').style.display = 'none';
    };

    // ==========================================
    // CANLI VERİ ÇEKME DÖNGÜSÜ
    // ==========================================


    let previousStock = null;

    // Gerçek Sunucudan Veri Çekme Fonksiyonu
    async function fetchLiveStock() {
        console.log("[POLL] fetchLiveStock called at", new Date().toLocaleTimeString());
        // 1. Stok verisini çek
        try {
            const response = await fetch("http://localhost:8000/stock", { cache: "no-store" });
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
            const filterVal = document.getElementById("log-time-filter") ? document.getElementById("log-time-filter").value : "5";
            const logsRes = await fetch("http://localhost:8000/movements?filter=" + filterVal, { cache: "no-store" });
            const logsData = await logsRes.json();
            updateLogs(logsData);
        } catch (error) {
            console.error("Loglar çekilemedi:", error);
        }

        // 3. SKT Uyarılarını ve Tüm Tabloyu Çek
        try {
            const expRes = await fetch("http://localhost:8000/expirations", { cache: "no-store" });
            const expData = await expRes.json();
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

        // 6. Analitik Grafiği Güncelle
        if (typeof updateChart === "function") {
            updateChart();
        }
    }

// --- Rol Yönetimi UI Güncellemeleri ---
function applyRoleUI() {
    const role = localStorage.getItem("userRole");
    const reportSection = document.getElementById("report-section");
    const lowStockAlerts = document.getElementById("low-stock-alerts-container");
    const adminIcons = document.querySelectorAll(".admin-only");

    if (role === "worker") {
        if (reportSection) reportSection.style.display = "none";
        adminIcons.forEach(icon => icon.style.display = "none");
    } else {
        if (reportSection) reportSection.style.display = "flex";
        adminIcons.forEach(icon => icon.style.display = "inline-block");
    }
}
window.applyRoleUI = applyRoleUI;

window.logout = function() {
    localStorage.removeItem("adminToken");
    localStorage.removeItem("userRole");
    window.location.reload();
};

window.promptEditStock = async function(productName) {
    if (localStorage.getItem("userRole") === "worker") {
        alert("Bu işlem için yetkiniz yok!");
        return;
    }
    const currentVal = document.getElementById("stock-" + productName).innerText;
    const newVal = prompt(productName.toUpperCase() + " için yeni stok miktarını girin:", currentVal);

    if (newVal !== null && newVal.trim() !== "" && !isNaN(newVal)) {
        let parsedVal = parseInt(newVal);
        if (parsedVal < 0) {
            alert("Stok 0'dan küçük olamaz!");
            parsedVal = 0;
        }
        try {
            const res = await fetchWithAuth("http://localhost:8000/stock/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ product_name: productName, new_quantity: parsedVal })
            });
            const data = await res.json();
            if (data.status === "success") {
                // The polling will update the UI automatically, but we can also update it immediately
                document.getElementById("stock-" + productName).innerText = data.new_quantity;
            } else {
                alert("Güncelleme başarısız: " + data.detail);
            }
        } catch(e) {
            alert("Sunucu ile iletişim kurulamadı.");
        }
    }
};


    // ==========================================
    // WEBSOCKET (CANLI YAYIN) BAĞLANTISI
    // ==========================================
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onmessage = (event) => {
        if(event.data === "update") {
            console.log("[WS] Sunucudan guncelleme tetigi geldi!");
            fetchLiveStock();
        }
    };
    ws.onopen = () => console.log("[WS] Baglanti kuruldu.");
    ws.onclose = () => console.log("[WS] Baglanti koptu.");

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
    // SKT VE PARTİ YÖNETİMİ
    // ==========================================

    const batchesList = document.getElementById("batches-list");


    window.promptEditBrand = async function(batchId, currentBrand) {
        if (localStorage.getItem("userRole") === "worker") {
            alert("Sadece yetkili markayi duzenleyebilir.");
            return;
        }
        const newBrand = prompt("Lutfen yeni marka adini girin:", currentBrand === "-" ? "" : currentBrand);
        if (newBrand !== null && newBrand.trim() !== "") {
            try {
                await fetch("http://localhost:8000/batches/" + batchId + "/brand", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ brand_name: newBrand.trim() })
                });
                fetchExpirations(); // reload table
            } catch (e) {
                console.error("Marka guncelleme hatasi:", e);
            }
        }
    };

    window.promptEditSKT = async function(batchId, currentSKT) {
        if (localStorage.getItem("userRole") === "worker") {
            alert("Bu işlem için yetkiniz yok!");
            return;
        }

        let sktParts = currentSKT.split(".");
        let defaultDate = sktParts.length === 3 ? `${sktParts[2]}-${sktParts[1]}-${sktParts[0]}` : "";

        const newDate = prompt("Parti #" + batchId + " için yeni SKT girin (YYYY-AA-GG formatında):", defaultDate);

        if (newDate !== null && newDate.trim() !== "") {
            // YYYY-MM-DD validasyonu
            if (!/^\d{4}-\d{2}-\d{2}$/.test(newDate)) {
                alert("Lütfen geçerli bir tarih formatı girin (Örn: 2024-12-31)");
                return;
            }

            try {
                const dateObj = new Date(newDate);
                const res = await fetchWithAuth("http://localhost:8000/batches/" + batchId, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ expiration_date: dateObj.toISOString() })
                });
                const data = await res.json();
                if (data.status === "success") {
                    fetchLiveStock(); // Tabloyu anında yenile
                } else {
                    alert("Güncelleme başarısız: " + data.detail);
                }
            } catch(e) {
                alert("Sunucu ile iletişim kurulamadı.");
            }
        }
    };

    window.wasteBatch = async function(batchId) {
        if (localStorage.getItem("userRole") === "worker") {
            alert("Yetkiniz yok!");
            return;
        }
        if (!confirm("Bu partideki tüm koliler çöpe atılacak/imha edilecek. Onaylıyor musunuz?")) return;

        try {
            await fetch(`http://localhost:8000/batches/${batchId}/waste`, { method: "POST" });
            fetchLiveStock(); // Tabloyu anında yenile
        } catch (e) {
            console.error("İmha hatası", e);
        }
    };

    window.renderAllBatches = function(expirations) {
        if (!batchesList) return;
        batchesList.innerHTML = "";

        if (expirations.length === 0) {
            batchesList.innerHTML = `<tr><td colspan="7" style="padding: 10px; text-align: center;">Depoda kayitli koli bulunmamaktadir.</td></tr>`;
            return;
        }

        expirations.forEach(exp => {
            const tr = document.createElement("tr");
            tr.style.borderBottom = "1px solid #eee";

            let statusText = "Güvenli";
            let statusColor = "#4ade80";
            if (exp.status === "expired") {
                statusText = "Süresi Geçmiş";
                statusColor = "#ef4444";
            } else if (exp.status === "critical") {
                statusText = "Kritik (0 gün)";
                statusColor = "#f97316";
            } else if (exp.status === "warning") {
                statusText = "Yaklaşıyor";
                statusColor = "#fbbf24";
            }

            const brandText = exp.brand_name === "-" ? "<i style='opacity:0.5; font-size:12px;'>Belirtilmedi</i>" : exp.brand_name;
            const brandHtml = localStorage.getItem("userRole") === "admin"
                ? `<span style="cursor: pointer; border-bottom: 1px dashed #ccc;" onclick="promptEditBrand(${exp.batch_id}, '${exp.brand_name}')">${brandText} ✏️</span>`
                : brandText;

            const productName = exp.product_name === "Gida" ? "Gıda" : exp.product_name === "Kirtasiye" ? "Kırtasiye" : exp.product_name;

            tr.innerHTML = `
                <td style="padding: 10px;">#${exp.batch_id}</td>
                <td style="padding: 10px; font-weight: bold;">${productName}</td>
                <td style="padding: 10px;">${brandHtml}</td>
                <td style="padding: 10px;">${exp.quantity} Adet</td>
                <td style="padding: 10px;">${exp.expiration_date}</td>
                <td style="padding: 10px; color: ${statusColor}; font-weight: bold;">${statusText} (${exp.days_left} gün)</td>
                <td style="padding: 10px; display: flex; gap: 5px;">
                    ${localStorage.getItem("userRole") !== "worker" ? `
                    <button onclick="promptEditSKT(${exp.batch_id}, '${exp.expiration_date}')" style="background-color: #f59e0b; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">📅 SKT Düzenle</button>
                    <button onclick="wasteBatch(${exp.batch_id})" style="background-color: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">İmha Et</button>
                    <button onclick="generateQR(${exp.batch_id}, '${productName}', '${exp.expiration_date}')" style="background-color: #64748b; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 3px;">
                        <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><rect x="7" y="7" width="3" height="3"></rect><rect x="14" y="7" width="3" height="3"></rect><rect x="7" y="14" width="3" height="3"></rect><rect x="14" y="14" width="3" height="3"></rect></svg>
                        Karekod
                    </button>
                    ` : '<span style="color: var(--text-secondary); font-size: 12px; font-style: italic;">Yetki Yok</span>'}
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

    // Satırları her saniye yeniden kurmamak için: veri değişmedikçe DOM'a dokunma.
    // Böylece kullanıcı e-posta yazarken input içeriği asla silinmez.
    let lastLowStockSignature = "";

    // value="..." icin guvenli kacirma
    const escAttr = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

let audioCtx = null;
function playBeep() {
    try {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) audioCtx = new AudioContext();
        }
        if (audioCtx) {
            // Resume if suspended (browser auto-play policy)
            if (audioCtx.state === 'suspended') audioCtx.resume();

            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();

            oscillator.type = 'triangle';
            oscillator.frequency.setValueAtTime(600, audioCtx.currentTime);

            gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);

            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);

            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.5);
        }
    } catch(e) { console.log("Audio not supported or blocked"); }
}

const notifiedLowStockIds = new Set();

    window.checkLowStock = async function() {
        if (localStorage.getItem("userRole") === "worker") return; // Görevli uyarı görmez
        const container = document.getElementById("low-stock-alerts-container");
        const list = document.getElementById("low-stock-list");
        if (!container || !list) return;

        try {
            const res = await fetch("http://localhost:8000/alerts/low-stock", { cache: "no-store" });
            const alerts = await res.json();

            // Eğer daha önce sipariş verdiğimiz ürünler varsa listeden gizleyelim
            const activeAlerts = alerts.filter(a => !orderedProductsThisSession.has(a.product_id));

            let hasNewAlert = false;
            activeAlerts.forEach(a => {
                if (!notifiedLowStockIds.has(a.product_id)) {
                    hasNewAlert = true;
                    notifiedLowStockIds.add(a.product_id);
                }
            });

            // Eger listede olmayan ama onceden bildirilmis varsa (stoğu artmissa) listeden cikar
            notifiedLowStockIds.forEach(id => {
                if (!activeAlerts.find(a => a.product_id === id)) {
                    notifiedLowStockIds.delete(id);
                }
            });

            if (hasNewAlert) {
                playBeep();
            }

            if (activeAlerts.length === 0) {
                container.style.display = "none";
                lastLowStockSignature = "";
                return;
            }

            // Ürünlerin kaydedilmiş toptancı e-postalarını çek (sadece eksikse)
            if (activeAlerts.some(a => !(a.product_id in supplierEmailCache))) {
                const pRes = await fetch("http://localhost:8000/products", { cache: "no-store" });
                if (pRes.ok) {
                    (await pRes.json()).forEach(p => { supplierEmailCache[p.id] = p.supplier_email || ""; });
                }
            }

            container.style.display = "block";

            // Veri aynıysa listeyi yeniden kurmadan çık (input koruma)
            const signature = activeAlerts
                .map(a => `${a.product_id}:${a.current_quantity}:${a.critical_threshold}:${supplierEmailCache[a.product_id] ?? ""}`)
                .join("|");
            if (signature === lastLowStockSignature) return;
            lastLowStockSignature = signature;

            // Yeniden kurmadan önce kullanıcının henüz kaydetmediği girdileri sakla
            list.querySelectorAll("input[data-supplier-input]").forEach(inp => {
                pendingSupplierEdits[inp.dataset.productId] = inp.value;
            });

            list.innerHTML = "";

            activeAlerts.forEach(alert => {
                const pid = alert.product_id;
                const savedEmail = supplierEmailCache[pid];
                const emailValue = (pid in pendingSupplierEdits) ? pendingSupplierEdits[pid] : (savedEmail ?? "");

                const item = document.createElement("div");
                item.dataset.productId = pid;
                item.style.backgroundColor = "var(--bg-color)";
                item.style.border = "1px solid var(--border-color)";
                item.style.padding = "10px 15px";
                item.style.borderRadius = "8px";
                item.style.display = "flex";
                item.style.justifyContent = "space-between";
                item.style.alignItems = "center";
                item.style.gap = "10px";
                item.style.flexWrap = "wrap";

                item.innerHTML = `
                    <div style="flex: 1 1 220px; min-width: 200px;">
                        <strong style="font-size: 16px;">${alert.product_name}</strong> stoğu kritik seviyede!
                        <span style="color: #ef5350; font-weight: bold;">(Mevcut: ${alert.current_quantity} Kutu / Sınır: ${alert.critical_threshold})</span>
                        ${savedEmail ? '' : '<span class="supplier-missing-warning" style="display:block; font-size:12px; color:#ef6c00; margin-top:2px;">Bu ürün için toptancı e-postası tanımlı değil.</span>'}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <input type="email" data-supplier-input data-product-id="${pid}" placeholder="Toptancı e-postası girin..."
                               value="${escAttr(emailValue)}" title="Bu ürünün toptancı e-posta adresi"
                               style="padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; width: 210px; max-width: 100%; font-size: 13px;">
                        <button onclick="saveSupplierEmail(${pid}, this)" title="Bu ürünün toptancı e-postasını kaydet"
                                style="background-color: #f97316; color: white; border: none; padding: 7px 12px; border-radius: 4px; font-weight: bold; font-size: 13px; cursor: pointer;">Kaydet</button>
                        <span class="supplier-save-status" style="font-size: 12px; font-weight: bold; display: none;"></span>
                        <button onclick="placeOrder(${pid}, this)" style="background-color: #ef6c00; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold; font-size: 14px; cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.backgroundColor='#e65100'" onmouseout="this.style.backgroundColor='#ef6c00'">
                            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                            Toptancıya Sipariş Geç
                        </button>
                    </div>
                `;
                list.appendChild(item);
            });

        } catch (e) {
            console.error("Kritik stok verisi çekilemedi:", e);
        }
    };

    // Seçili ürünün toptancı e-postasını JWT ile backend'e kaydeder (sayfa yenilenmez)
    window.saveSupplierEmail = async function(productId, btn) {
        const item = btn.closest("[data-product-id]");
        const input = item ? item.querySelector("input[data-supplier-input]") : null;
        const statusEl = item ? item.querySelector(".supplier-save-status") : null;

        const showStatus = (text, color) => {
            if (!statusEl) return;
            statusEl.textContent = text;
            statusEl.style.color = color;
            statusEl.style.display = "inline";
            clearTimeout(statusEl._hideTimer);
            statusEl._hideTimer = setTimeout(() => { statusEl.style.display = "none"; }, 3000);
        };

        if (!input) {
            showStatus("Hata!", "#dc2626");
            return;
        }

        const emailVal = input.value.trim();
        if (emailVal && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
            showStatus("Geçersiz e-posta!", "#dc2626");
            return;
        }

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = "Kaydediliyor...";
        try {
            const res = await window.fetchWithAuth(`http://localhost:8000/products/${productId}/supplier`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ supplier_email: emailVal })
            });

            if (res.status === 401) return; // fetchWithAuth zaten giriş ekranını açtı

            const data = await res.json().catch(() => ({}));
            if (res.ok && data.status === "success") {
                const savedVal = data.supplier_email || "";
                supplierEmailCache[productId] = savedVal;
                delete pendingSupplierEdits[productId];

                // Aninda UI senkronu: kaydedilen degeri goster, uyarıyı guncelle
                // (1 sn'lik periyodik refresh'i beklemeden)
                input.value = savedVal;
                const warnEl = item ? item.querySelector(".supplier-missing-warning") : null;
                if (warnEl) warnEl.style.display = savedVal ? "none" : "";
                lastLowStockSignature = ""; // sonraki dongude satir tam tazelensin

                showStatus("Kaydedildi ✓", "#16a34a");
            } else {
                showStatus(data.detail ? String(data.detail) : "Kaydedilemedi!", "#dc2626");
            }
        } catch (e) {
            console.error("Toptancı e-postası kaydedilemedi:", e);
            showStatus("Bağlantı hatası!", "#dc2626");
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };

});

window.undoMovement = async function(id) {
    if(!confirm("Bu hareketi geri almak istediginize emin misiniz?")) return;
    try {
        const res = await window.fetchWithAuth("http://localhost:8000/movements/" + id + "/undo", {method: "POST"});
        if (res.ok) { alert("Basariyla geri alindi!"); window.location.reload(); }
        else { alert("Geri alma basarisiz!"); }
    } catch(e) { alert("Hata: " + e); }
};

window.placeOrder = function(productId, btn) {
    if (localStorage.getItem("userRole") === "worker") {
        alert("Sadece yetkili siparis gecebilir.");
        return;
    }

    // Aliciyi sunucu secer: urune tanimli supplier_email > varsayilan toptanci.
    // Ayrica kullanici global e-posta girmek zorunda degil; per-urun Kaydet yeterli.
    btn.innerHTML = "Sipari\u015f Ge\u00e7iliyor...";
    btn.disabled = true;

    fetch("http://localhost:8000/order/" + productId, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if (data.status === "success" && data.sent) {
                if (data.mode === "simulasyon") {
                    btn.innerHTML = "Sim\u00fclasyon \u2714\ufe0f";
                } else {
                    btn.innerHTML = "Sipari\u015f \u0130letildi \u2714\ufe0f";
                    btn.style.backgroundColor = "#4ade80";
                    btn.style.color = "white";
                }
                if (typeof orderedProductsThisSession !== 'undefined') {
                    orderedProductsThisSession.add(productId);
                }
            } else {
                btn.innerHTML = "Hata!";
                btn.style.backgroundColor = "#ef4444";
                btn.style.color = "white";
                console.error("Siparis e-postasi gonderilemedi:", data);
            }
            setTimeout(() => { checkLowStock(); }, 2000);
        })
        .catch(err => {
            console.error("Siparis hatasi:", err);
            btn.innerHTML = "Hata!";
            btn.disabled = false;
        });
};
