# 📦 Akıllı Depo Yönetim Sistemi (Yapay Zeka Destekli B2B SaaS)

Bu proje, bir depo bandından (conveyor) veya kapısından geçen ürünleri **Kamera ve Yapay Zeka (YOLO)** kullanarak otomatik algılayan, sınıflandıran, anlık stok takibi yapan ve B2B senaryolarında toptancıya otomatik sipariş geçebilen kapsamlı bir staj otomasyon projesidir.

## 🚀 Öne Çıkan Özellikler

- **🤖 Çift Yapay Zeka Mimarisi:** YOLOv8n ile nesne tespiti (Tracking) yaparken, projeye özel eğitilmiş sınıflandırma modeli ile ürünleri (Gıda, Elektronik, Temizlik, Kırtasiye, Tekstil) otomatik tanır.
- **🛡️ Sarsılmaz Takip (Robust Centroid Tracking):** Kameradaki anlık bulanıklıklara veya ID düşmelerine karşı özel takip algoritmasıyla ürünler çizgiden geçerken hatasız sayılır.
- **🔒 Rol Bazlı Kimlik Doğrulama (JWT):** Admin (Yönetici) ve Görevli (Personel) girişleri bulunur. Kriptografik JSON Web Token'lar (JWT) ile yetkisiz işlemler engellenir.
- **✉️ Otomatik B2B Sipariş (Mailto):** Kritik eşiğin altına düşen stoklar sistem tarafından kırmızı uyarı ile tespit edilir. Tek tuşla toptancıya otomatik sipariş e-postası (taslağı) oluşturulur.
- **🏷️ Marka & Varyant Yönetimi:** Ürünlerin yanı sıra, farklı markalar sisteme kaydedilebilir ve arama/filtreleme çubuklarıyla binlerce stok saniyeler içinde filtrelenebilir.
- **📊 Gelişmiş Loglama ve Raporlama:** Depoya giren-çıkan her ürün, işlemi yapan personel ve tarih-saat ile veritabanına kalıcı olarak işlenir. İşlem geçmişleri CSV olarak indirilebilir.

## 🛠️ Kullanılan Teknolojiler

- **Görüntü İşleme (CV):** Python, OpenCV, Ultralytics (YOLOv8)
- **Arka Uç (Backend):** Python, FastAPI, Uvicorn, Pydantic
- **Veritabanı (Database):** SQLite, SQLAlchemy (ORM)
- **Ön Uç (Frontend):** HTML5, Vanilla CSS, JavaScript (Fetch API, DOM)

## 🎯 Kurulum ve Çalıştırma (Tek Tuş)

Proje, herhangi bir Python veya kütüphane kurulumu gerektirmeden, **tamamen izole bir sanal ortam (.venv)** kullanarak kendini otomatik kuracak şekilde tasarlanmıştır.

1. Projeyi masaüstüne indirin veya `git clone` ile çekin.
2. Klasör içindeki **`baslat.bat`** dosyasına çift tıklayın.

**`baslat.bat` sizin için neleri otomatik yapar?**
- Sisteme özel bir sanal ortam oluşturur.
- Gerekli tüm kütüphaneleri (FastAPI, OpenCV, YOLO vb.) indirir.
- Arka planda **FastAPI sunucusunu** ve **Yapay Zeka Kamerası'nı** senkron bir şekilde çalıştırır.

3. Siyah terminal ekranları açıldıktan sonra web tarayıcınızda (Chrome/Edge) **`frontend/index.html`** dosyasına çift tıklayarak sistemi kullanmaya başlayabilirsiniz!

## 🔐 Giriş Bilgileri

**Yönetici (Admin) Hesabı:**
- Kullanıcı Adı: `admin`
- Şifre: `12345`

**Personel (Görevli) Hesabı:**
- Kullanıcı Adı: `gorevli`
- Şifre: `12345`

---
*Geliştirici:*Ghofrane Saadi - Fatmanur Bay - Staj Projesi
