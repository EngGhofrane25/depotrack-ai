
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
var supplierEmailCache = {};
var pendingSupplierEdits = {};
window.supplierEmailCache = supplierEmailCache;
window.pendingSupplierEdits = pendingSupplierEdits;

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // DOM ELEMENTLERİ
    // ==========================================
    const elElektronik = document.getElementById("stock-elektronik");
    const elGıda = document.getElementById("stock-gida");
    const elTemizlik = document.getElementById("stock-temizlik");
    const elKırtasiye = document.getElementById("stock-kirtasiye");
    const elTekstil = document.getElementById("stock-tekstil");
    const logList = document.getElementById("log-list");

    let currentStockData = null;
    let currentLogsData = null;
    let currentExpData = null;
    let currentAlertsData = [];

    // Stokları Ekrana Yazdır
    function updateStockDisplay(stockData) {
        elElektronik.innerText = stockData.elektronik || 0;
        elGıda.innerText = stockData.gida || 0;
        elTemizlik.innerText = stockData.temizlik || 0;
        elKırtasiye.innerText = stockData.kirtasiye || 0;
        elTekstil.innerText = stockData.tekstil || 0;

        // Summary: Total products count
        const total = Object.values(stockData).reduce((s, v) => s + (v || 0), 0);
        const summaryTotal = document.getElementById("summary-total");
        if (summaryTotal) summaryTotal.innerText = total;
    }

    // Hareket loglarını güncelle
    function updateLogs(logs) {
        logList.innerHTML = "";
        const recentLogs = logs;

        recentLogs.forEach(log => {
            const li = document.createElement("li");
            li.className = "log-item";

            const isEntry = log.direction === "IN";
            const directionText = isEntry ? "GİRDİ" : "ÇIKTI";
            const directionClass = isEntry ? "log-in" : "log-out";
            const directionIcon = isEntry
                ? '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path></svg>'
                : '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>';

            const productNames = {1: "Elektronik", 2: "Gıda", 3: "Tekstil", 4: "Kırtasiye", 5: "Temizlik"};
            const productName = productNames[log.product_id] || "Bilinmeyen Ürün";

            const date = new Date(log.timestamp);
            const timeString = date.toLocaleTimeString('tr-TR');

            li.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 6px; background: ${isEntry ? 'var(--success-light)' : 'var(--danger-light)'}; color: ${isEntry ? 'var(--success)' : 'var(--danger)'};">
                            ${directionIcon}
                        </span>
                        <div style="display: flex; flex-direction: column; gap: 1px;">
                            <span style="font-weight: 600; font-size: 0.85rem; color: var(--text-primary);">${productName}</span>
                            <span style="font-size: 0.75rem; color: var(--text-muted); font-variant-numeric: tabular-nums;">${timeString}</span>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="${directionClass}" style="font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: ${isEntry ? 'var(--success-light)' : 'var(--danger-light)'};">${directionText}</span>
                        <button onclick="undoMovement(${log.id})" style="background: var(--warning); color: white; border: none; padding: 3px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 500; font-family: inherit; transition: 0.2s;" title="Hareketi Geri Al">Geri Al</button>
                    </div>
                </div>
            `;
            logList.appendChild(li);
        });
    }

    let chartInstance = null;

    // ==========================================
    // 1. LOGIN SİSTEMİ
    // ==========================================
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
                localStorage.setItem("userRole", data.role);
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

    // ==========================================
    // 2. DARK MODE
    // ==========================================
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

    // ==========================================
    // 3. EXCEL İNDİRME
    // ==========================================
    window.downloadExcel = function() {
        window.open("http://localhost:8000/export/csv", "_blank");
    };

    // ==========================================
    // 4. CHART.JS
    // ==========================================
    window.updateChart = async function() {
        try {
            const res = await fetch("http://localhost:8000/analytics", { cache: "no-store" });
            const data = await res.json();

            const ctx = document.getElementById('inventoryChart');
            if (!ctx) return;

            const colorMap = {
                'Elektronik': '#3b82f6',
                'Gida': '#ef4444',
                'Temizlik': '#22c55e',
                'Kirtasiye': '#f59e0b',
                'Tekstil': '#8b5cf6'
            };
            const dynamicColors = data.labels.map(label => colorMap[label] || '#94a3b8');

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
                            borderWidth: 0,
                            hoverBorderWidth: 2,
                            hoverBorderColor: 'rgba(255,255,255,0.5)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '65%',
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 16,
                                    usePointStyle: true,
                                    pointStyleWidth: 10,
                                    font: { family: 'Inter', size: 12 }
                                }
                            }
                        }
                    }
                });
            }
        } catch (e) {
            console.error("Grafik verisi alınamadı", e);
        }
    };

    // ==========================================
    // 5. QR CODE MODAL
    // ==========================================
    let qrCodeObj = null;

    window.generateQR = function(batchId, productName, expDate) {
        document.getElementById('qrModal').style.display = 'flex';
        document.getElementById('qrModalTitle').innerText = `Koli #${batchId} Karekod`;
        document.getElementById('qrModalDesc').innerText = `Ürün: ${productName} | SKT: ${expDate}`;

        const qrContainer = document.getElementById('qrcode');
        qrContainer.innerHTML = '';

        qrCodeObj = new QRCode(qrContainer, {
            text: `DEPOTRACK-BATCHID:${batchId}|URUN:${productName}|SKT:${expDate}`,
            width: 150,
            height: 150,
            colorDark : "#0f172a",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        });
    };

    window.closeQRModal = function() {
        document.getElementById('qrModal').style.display = 'none';
    };

    // ==========================================
    // CANLI VERİ ÇEKME
    // ==========================================
    let previousStock = null;

    async function fetchLiveStock() {
        // 1. Stok verisi
        try {
            const response = await fetch("http://localhost:8000/stock", { cache: "no-store" });
            const currentStock = await response.json();
            currentStockData = currentStock;
            previousStock = JSON.parse(JSON.stringify(currentStock));
            updateStockDisplay(currentStock);
        } catch (error) {
            console.error("Stok verisi çekilemedi!", error);
        }

        // 2. Hareket geçmişi
        try {
            const filterVal = document.getElementById("log-time-filter") ? document.getElementById("log-time-filter").value : "5";
            const logsRes = await fetch("http://localhost:8000/movements?filter=" + filterVal, { cache: "no-store" });
            const logsData = await logsRes.json();
            currentLogsData = logsData;
            updateLogs(logsData);
            renderTimeline(logsData);

            // Update summary: movements count
            const summaryMovements = document.getElementById("summary-movements");
            if (summaryMovements) summaryMovements.innerText = logsData.length;
        } catch (error) {
            console.error("Loglar çekilemedi:", error);
        }

        // 3. SKT Uyarıları
        try {
            const expRes = await fetch("http://localhost:8000/expirations", { cache: "no-store" });
            const expData = await expRes.json();
            currentExpData = expData;
            if (typeof renderAllBatches === "function") {
                renderAllBatches(expData);
            }

            // Update summary: active batches count
            const summaryBatches = document.getElementById("summary-batches");
            if (summaryBatches) summaryBatches.innerText = expData.length;
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

        // 7. AI İçgörülerini Güncelle
        computeInsights();
    }

    // ==========================================
    // ROL YÖNETİMİ
    // ==========================================

    // ==========================================
    // AI İÇGÖRÜLERİ
    // ==========================================
    const productNames = {1: "Elektronik", 2: "Gıda", 3: "Tekstil", 4: "Kırtasiye", 5: "Temizlik"};

    function computeInsights() {
        const container = document.getElementById("ai-insights-list");
        if (!container) return;

        const insights = [];

        if (currentStockData) {
            const stockEntries = Object.entries(currentStockData);
            const totalStock = stockEntries.reduce((s, [, v]) => s + (v || 0), 0);
            const zeroStock = stockEntries.filter(([, v]) => v === 0);
            const maxProduct = stockEntries.reduce((max, [k, v]) => (v || 0) > (max[1] || 0) ? [k, v] : max, ["", 0]);

            if (totalStock === 0) {
                insights.push({
                    icon: "amber",
                    svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
                    text: "Depoda hiçbir ürün bulunmuyor.",
                    detail: "Stok girişi yapılmamış."
                });
            } else {
                insights.push({
                    icon: "blue",
                    svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>',
                    text: "Depoda toplam " + totalStock + " adet ürün bulunuyor.",
                    detail: stockEntries.length + " farklı kategoride stok mevcut."
                });

                if (maxProduct[1] > 0) {
                    const maxName = productNames[maxProduct[0]] || maxProduct[0];
                    insights.push({
                        icon: "green",
                        svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
                        text: "En fazla stoğa sahip ürün: " + maxName,
                        detail: maxProduct[1] + " adet ile depodaki en yüksek stok."
                    });
                }

                if (zeroStock.length > 0) {
                    const zeroNames = zeroStock.map(([k]) => productNames[k] || k).join(", ");
                    insights.push({
                        icon: "red",
                        svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
                        text: zeroStock.length + " ürünün stoğu tamamen bitti.",
                        detail: zeroNames
                    });
                }
            }
        }

        if (currentAlertsData && currentAlertsData.length > 0) {
            insights.push({
                icon: "amber",
                svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
                text: currentAlertsData.length + " ürün kritik stok seviyesinin altında.",
                detail: "Sipariş gerekebilir."
            });
        }

        if (currentLogsData && currentLogsData.length > 0) {
            const inCount = currentLogsData.filter(l => l.direction === "IN").length;
            const outCount = currentLogsData.filter(l => l.direction === "OUT").length;

            insights.push({
                icon: "cyan",
                svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
                text: currentLogsData.length + " hareket kaydı mevcut.",
                detail: inCount + " giriş, " + outCount + " çıkış"
            });

            const productMovements = {};
            currentLogsData.forEach(l => {
                const pid = l.product_id;
                productMovements[pid] = (productMovements[pid] || 0) + 1;
            });
            const topMover = Object.entries(productMovements).reduce((max, [k, v]) => v > (max[1] || 0) ? [k, v] : max, ["", 0]);
            if (topMover[1] > 0) {
                const topName = productNames[topMover[0]] || "Bilinmeyen";
                insights.push({
                    icon: "purple",
                    svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
                    text: "En fazla hareket gören ürün: " + topName,
                    detail: topMover[1] + " hareket kaydı"
                });
            }
        }

        if (currentExpData && currentExpData.length > 0) {
            const urgentBatches = currentExpData.filter(e => e.status === "expired" || e.status === "critical" || e.status === "danger");
            if (urgentBatches.length > 0) {
                insights.push({
                    icon: "red",
                    svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
                    text: urgentBatches.length + " partinin son kullanma tarihi yaklaşıyor veya geçmiş.",
                    detail: "FEFO akışı kontrol edilmeli."
                });
            }

            insights.push({
                icon: "green",
                svg: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
                text: currentExpData.length + " aktif parti takip ediliyor.",
                detail: "Parti bazlı envanter yönetimi aktif."
            });
        }

        if (insights.length === 0) {
            container.innerHTML = '<div class="insight-neutral">Yeterli veri bulunmuyor. Veriler toplandıkça içgörüler burada görünecek.</div>';
            return;
        }

        container.innerHTML = "";
        insights.forEach(function(insight) {
            var card = document.createElement("div");
            card.className = "insight-card";
            card.innerHTML =
                '<div class="insight-icon insight-icon-' + insight.icon + '">' + insight.svg + '</div>' +
                '<div class="insight-content">' +
                    '<div class="insight-text">' + insight.text + '</div>' +
                    '<div class="insight-detail">' + insight.detail + '</div>' +
                '</div>';
            container.appendChild(card);
        });
    }

    // ==========================================
    // KAMERA OLAY ZAMAN ÇİZELGESİ
    // ==========================================
    function renderTimeline(logs) {
        var timelineContainer = document.getElementById("camera-timeline-list");
        if (!timelineContainer) return;

        if (!logs || logs.length === 0) {
            timelineContainer.innerHTML = '<div class="camera-timeline-empty">Henüz olay kaydı yok</div>';
            return;
        }

        var recentLogs = logs.slice(0, 8);
        timelineContainer.innerHTML = "";

        recentLogs.forEach(function(log) {
            var isEntry = log.direction === "IN";
            var directionText = isEntry ? "GİRİŞ" : "ÇIKIŞ";
            var iconClass = isEntry ? "timeline-icon-in" : "timeline-icon-out";
            var badgeClass = isEntry ? "timeline-badge-in" : "timeline-badge-out";
            var iconSvg = isEntry
                ? '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path></svg>'
                : '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>';

            var productName = productNames[log.product_id] || "Bilinmeyen";
            var date = new Date(log.timestamp);
            var timeStr = date.toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit', second: '2-digit'});

            var item = document.createElement("div");
            item.className = "camera-timeline-item";
            item.innerHTML =
                '<span class="timeline-time">' + timeStr + '</span>' +
                '<span class="timeline-icon ' + iconClass + '">' + iconSvg + '</span>' +
                '<span class="timeline-product">' + productName + '</span>' +
                '<span class="timeline-badge ' + badgeClass + '">' + directionText + '</span>';
            timelineContainer.appendChild(item);
        });
    }

    // ==========================================
    // ROL YÖNETİMİ
    // ==========================================
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
            adminIcons.forEach(icon => icon.style.display = "inline-flex");
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
    // WEBSOCKET
    // ==========================================
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onmessage = (event) => {
        if(event.data === "update") {
            fetchLiveStock();
        }
    };
    ws.onopen = () => console.log("[WS] Bağlantı kuruldu.");
    ws.onclose = () => console.log("[WS] Bağlantı koptu.");

    fetchLiveStock();
    setInterval(fetchLiveStock, 1000);

    // Download report button
    const downloadBtn = document.getElementById("download-report-btn");
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            window.open("http://localhost:8000/report", "_blank");
        });
    }

    // ==========================================
    // SKT VE PARTİ YÖNETİMİ
    // ==========================================
    const batchesList = document.getElementById("batches-list");

    window.promptEditBrand = async function(batchId, currentBrand) {
        if (localStorage.getItem("userRole") === "worker") {
            alert("Sadece yetkili markayı düzenleyebilir.");
            return;
        }
        const newBrand = prompt("Lütfen yeni marka adını girin:", currentBrand === "-" ? "" : currentBrand);
        if (newBrand !== null && newBrand.trim() !== "") {
            try {
                await fetch("http://localhost:8000/batches/" + batchId + "/brand", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ brand_name: newBrand.trim() })
                });
                fetchLiveStock();
            } catch (e) {
                console.error("Marka güncelleme hatası:", e);
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
                    fetchLiveStock();
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
            fetchLiveStock();
        } catch (e) {
            console.error("İmha hatası", e);
        }
    };

    window.renderAllBatches = function(expirations) {
        if (!batchesList) return;
        batchesList.innerHTML = "";

        if (expirations.length === 0) {
            batchesList.innerHTML = `<tr><td colspan="7" style="padding: 24px; text-align: center; color: var(--text-muted);">Depoda kayıtlı koli bulunmamaktadır.</td></tr>`;
            return;
        }

        expirations.forEach(exp => {
            const tr = document.createElement("tr");

            let statusText = "Güvenli";
            let statusColor = "var(--success)";
            let statusBg = "var(--success-light)";
            if (exp.status === "expired") {
                statusText = "Süresi Geçmiş";
                statusColor = "var(--danger)";
                statusBg = "var(--danger-light)";
            } else if (exp.status === "critical") {
                statusText = "Kritik";
                statusColor = "var(--danger)";
                statusBg = "var(--danger-light)";
            } else if (exp.status === "warning") {
                statusText = "Yaklaşıyor";
                statusColor = "var(--warning)";
                statusBg = "var(--warning-light)";
            }

            const brandText = exp.brand_name === "-" ? "<span style='opacity:0.4; font-size:12px; font-style:italic;'>Belirtilmedi</span>" : exp.brand_name;
            const brandHtml = localStorage.getItem("userRole") === "admin"
                ? `<span style="cursor: pointer; border-bottom: 1px dashed var(--border); padding-bottom: 1px; transition: 0.2s;" onclick="promptEditBrand(${exp.batch_id}, '${exp.brand_name}')">${brandText} <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline; vertical-align:middle;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg></span>`
                : brandText;

            const productName = exp.product_name === "Gida" ? "Gıda" : exp.product_name === "Kirtasiye" ? "Kırtasiye" : exp.product_name;

            tr.innerHTML = `
                <td style="font-weight: 500; color: var(--text-secondary);">#${exp.batch_id}</td>
                <td style="font-weight: 600;">${productName}</td>
                <td>${brandHtml}</td>
                <td style="font-weight: 500;">${exp.quantity} Adet</td>
                <td style="font-variant-numeric: tabular-nums;">${exp.expiration_date}</td>
                <td><span style="display: inline-flex; align-items: center; gap: 5px; font-weight: 600; font-size: 0.8rem; padding: 3px 10px; border-radius: 20px; background: ${statusBg}; color: ${statusColor};"><span style="width:6px; height:6px; border-radius:50%; background:currentColor;"></span>${statusText} (${exp.days_left}g)</span></td>
                <td>
                    <div style="display: flex; gap: 5px; flex-wrap: nowrap;">
                        ${localStorage.getItem("userRole") !== "worker" ? `
                        <button onclick="promptEditSKT(${exp.batch_id}, '${exp.expiration_date}')" style="background: var(--warning); color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; font-family: inherit; transition: 0.2s;">📅 SKT</button>
                        <button onclick="wasteBatch(${exp.batch_id})" style="background: var(--danger); color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; font-family: inherit; transition: 0.2s;">İmha</button>
                        <button onclick="generateQR(${exp.batch_id}, '${productName}', '${exp.expiration_date}')" style="background: var(--bg-primary); color: var(--text-secondary); border: 1px solid var(--border); padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 500; font-family: inherit; display: flex; align-items: center; gap: 3px; transition: 0.2s;">
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                            QR
                        </button>
                        ` : '<span style="color: var(--text-muted); font-size: 11px; font-style: italic;">Yetki Yok</span>'}
                    </div>
                </td>
            `;
            batchesList.appendChild(tr);
        });
    };

    // ==========================================
    // KRİTİK STOK VE TOPTANCI SİPARİŞİ
    // ==========================================
    const orderedProductsThisSession = new Set();
    let lastLowStockSignature = "";

    const escAttr = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    let audioCtx = null;
    function playBeep() {
        try {
            if (!audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) audioCtx = new AudioContext();
            }
            if (audioCtx) {
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
        if (localStorage.getItem("userRole") === "worker") {
            currentAlertsData = [];
            return;
        }
        const container = document.getElementById("low-stock-alerts-container");
        const list = document.getElementById("low-stock-list");
        if (!container || !list) return;

        try {
            const res = await fetch("http://localhost:8000/alerts/low-stock", { cache: "no-store" });
            const alerts = await res.json();

            const activeAlerts = alerts.filter(a => !orderedProductsThisSession.has(a.product_id));
            currentAlertsData = activeAlerts;

            // Update summary critical count
            const summaryCritical = document.getElementById("summary-critical");
            if (summaryCritical) summaryCritical.innerText = activeAlerts.length;

            let hasNewAlert = false;
            activeAlerts.forEach(a => {
                if (!notifiedLowStockIds.has(a.product_id)) {
                    hasNewAlert = true;
                    notifiedLowStockIds.add(a.product_id);
                }
            });

            notifiedLowStockIds.forEach(id => {
                if (!activeAlerts.find(a => a.product_id === id)) {
                    notifiedLowStockIds.delete(id);
                }
            });

            if (hasNewAlert) playBeep();

            if (activeAlerts.length === 0) {
                container.style.display = "none";
                lastLowStockSignature = "";
                currentAlertsData = [];
                return;
            }

            if (activeAlerts.some(a => !(a.product_id in supplierEmailCache))) {
                const pRes = await fetch("http://localhost:8000/products", { cache: "no-store" });
                if (pRes.ok) {
                    (await pRes.json()).forEach(p => { supplierEmailCache[p.id] = p.supplier_email || ""; });
                }
            }

            container.style.display = "block";

            const signature = activeAlerts
                .map(a => `${a.product_id}:${a.current_quantity}:${a.critical_threshold}:${supplierEmailCache[a.product_id] ?? ""}`)
                .join("|");
            if (signature === lastLowStockSignature) return;
            lastLowStockSignature = signature;

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
                item.className = "alert-card";

                item.innerHTML = `
                    <div class="alert-card-info">
                        <div class="alert-card-header">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                            <strong style="font-size: 15px; color: var(--text-primary);">${alert.product_name}</strong>
                        </div>
                        <div class="alert-card-stats">
                            <span class="alert-stat alert-stat-danger">${alert.current_quantity} Adet</span>
                            <span style="color: var(--text-muted); font-size: 0.75rem;">/ Sınır: ${alert.critical_threshold}</span>
                        </div>
                        ${savedEmail ? '' : '<div class="supplier-missing-warning"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>Tedarikçi e-postası tanımlı değil</div>'}
                    </div>
                    <div class="alert-card-actions">
                        <div class="alert-email-row">
                            <input type="email" data-supplier-input data-product-id="${pid}" placeholder="tedarikci@ornek.com"
                                   value="${escAttr(emailValue)}" title="Toptancı e-posta adresi"
                                   class="alert-email-input">
                            <button onclick="saveSupplierEmail(${pid}, this)" class="alert-save-btn">Kaydet</button>
                            <span class="supplier-save-status"></span>
                        </div>
                        <button onclick="placeOrder(${pid}, this)" class="alert-order-btn">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                            Sipariş Geç
                        </button>
                    </div>
                `;
                list.appendChild(item);
            });

        } catch (e) {
            console.error("Kritik stok verisi çekilemedi:", e);
        }
    };

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

            if (res.status === 401) return;

            const data = await res.json().catch(() => ({}));
            if (res.ok && data.status === "success") {
                const savedVal = data.supplier_email || "";
                supplierEmailCache[productId] = savedVal;
                delete pendingSupplierEdits[productId];

                input.value = savedVal;
                const warnEl = item ? item.querySelector(".supplier-missing-warning") : null;
                if (warnEl) warnEl.style.display = savedVal ? "none" : "";
                lastLowStockSignature = "";

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
    if(!confirm("Bu hareketi geri almak istediğinize emin misiniz?")) return;
    try {
        const res = await window.fetchWithAuth("http://localhost:8000/movements/" + id + "/undo", {method: "POST"});
        if (res.ok) { alert("Başarıyla geri alındı!"); window.location.reload(); }
        else { alert("Geri alma başarısız!"); }
    } catch(e) { alert("Hata: " + e); }
};

window.placeOrder = function(productId, btn) {
    if (localStorage.getItem("userRole") === "worker") {
        alert("Sadece yetkili sipariş geçebilir.");
        return;
    }

    btn.innerHTML = "Sipariş Geçiliyor...";
    btn.disabled = true;

    fetch("http://localhost:8000/order/" + productId, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if (data.status === "success" && data.sent) {
                if (data.mode === "simulasyon") {
                    btn.innerHTML = "Simülasyon ✔";
                    btn.style.background = "var(--accent)";
                } else {
                    btn.innerHTML = "Sipariş İletildi ✔";
                    btn.style.background = "var(--success)";
                }
                if (typeof orderedProductsThisSession !== 'undefined') {
                    orderedProductsThisSession.add(productId);
                }
            } else {
                btn.innerHTML = "Hata!";
                btn.style.background = "var(--danger)";
                console.error("Sipariş e-postası gönderilemedi:", data);
            }
            setTimeout(() => { checkLowStock(); }, 2000);
        })
        .catch(err => {
            console.error("Sipariş hatası:", err);
            btn.innerHTML = "Hata!";
            btn.disabled = false;
        });
};
