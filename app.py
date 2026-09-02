from flask import Flask, render_template_string, request
import requests

app = Flask(__name__)

# Binance'den aktif tüm vadeli USDT çiftlerini çekme
def get_futures_symbols():
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url, timeout=5)
        data = response.json()
        symbols = []
        for s in data.get("symbols", []):
            if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT":
                symbols.append(s["symbol"])
        return sorted(symbols)
    except Exception as e:
        print(f"Semboller çekilemedi: {e}")
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

# Seçilen coinin anlık fiyatını çekme
def get_current_price(symbol):
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=3)
        data = response.json()
        price = float(data.get("price", 0))
        # Fiyata göre dinamik formatlama (örn: virgülden sonra 2 veya 4 basamak)
        if price >= 10:
            return f"{price:,.2f}"
        else:
            return f"{price:,.4f}"
    except:
        return "0.00"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ağırlıklı Ortalama Girişler - Smart Money</title>
    <meta http-equiv="refresh" content="300">
    <style>
        body { background-color: #0b0e11; color: #eaecef; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 15px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; background: #1e2329; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2b313a; padding-bottom: 12px; margin-bottom: 15px; }
        .header h3 { margin: 0; font-size: 16px; color: #eaecef; display: flex; align-items: center; gap: 8px; }
        
        .selector-box { margin-bottom: 15px; text-align: center; }
        select { width: 100%; background: #2b313a; color: #f0b90b; border: 1px solid #474d57; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: bold; outline: none; cursor: pointer; }
        option { background: #1e2329; color: #eaecef; padding: 10px; }
        
        .filter-title { text-align: center; font-size: 13px; color: #848e9c; margin-bottom: 10px; }
        .filters { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 20px; }
        .filter-btn { background: #2b313a; border: 1px solid #2b313a; color: #848e9c; padding: 10px; border-radius: 8px; text-align: center; font-size: 12px; cursor: pointer; transition: 0.2s; }
        .filter-btn.active { border-color: #0ecb81; background: #1e2329; color: #eaecef; font-weight: bold; }
        
        .coin-header-box { display: flex; justify-content: space-between; align-items: center; background: #2b313a; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; }
        .coin-title { color: #f0b90b; font-size: 16px; font-weight: bold; letter-spacing: 1px; margin: 0; }
        .coin-price { color: #eaecef; font-size: 15px; font-family: monospace; font-weight: bold; margin: 0; }
        
        .card { border-radius: 8px; padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .card-long { background: rgba(14, 203, 129, 0.1); border: 1px solid rgba(14, 203, 129, 0.2); }
        .card-short { background: rgba(246, 70, 93, 0.1); border: 1px solid rgba(246, 70, 93, 0.2); }
        .card-neutral { background: #2b313a; border: 1px solid #363c4e; }
        
        .card-left .title { font-size: 13px; font-weight: bold; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
        .card-left .sub { font-size: 11px; color: #848e9c; }
        .card-right { font-size: 15px; font-weight: bold; font-family: monospace; }
        
        .dot-green { width: 8px; height: 8px; background: #0ecb81; border-radius: 50%; display: inline-block; }
        .dot-red { width: 8px; height: 8px; background: #f6465d; border-radius: 50%; display: inline-block; }
        .dot-white { width: 8px; height: 8px; background: #eaecef; border-radius: 50%; display: inline-block; }
        
        .text-green { color: #0ecb81; }
        .text-red { color: #f6465d; }
        .text-white { color: #eaecef; }
        .refresh-info { text-align: center; font-size: 10px; color: #848e9c; margin-top: 15px; }
    </style>
</head>
<body>

    <div class="container">
        <div class="header">
            <h3>📊 Ağırlıklı Ortalama Girişler</h3>
            <span style="color: #0ecb81; font-size: 12px;">● Canlı</span>
        </div>

        <!-- COİN SEÇİM MENÜSÜ -->
        <div class="selector-box">
            <form method="GET" action="/">
                <select name="symbol" onchange="this.form.submit()">
                    {% for s in symbols %}
                        <option value="{{ s }}" {% if s == selected_symbol %}selected{% endif %}>{{ s }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>

        <div class="filter-title">Veri Kaynağı Seçin:</div>
        <div class="filters">
            <div class="filter-btn active">👥 Sadece Copy Liderler</div>
            <div class="filter-btn">🐳 Sadece Balinalar</div>
            <div class="filter-btn">👥🐳 Tümü</div>
            <div class="filter-btn">📊 Veritabanı</div>
        </div>

        <!-- COİN ADI VE ANLIK FİYAT BÖLÜMÜ -->
        <div class="coin-header-box">
            <div class="coin-title">{{ selected_symbol }}</div>
            <div class="coin-price">Anlık: ${{ current_price }}</div>
        </div>

        <!-- LONG KARTI -->
        <div class="card card-long">
            <div class="card-left">
                <div class="title"><span class="dot-green"></span> <span class="text-green">LONG Ort. Giriş:</span></div>
                <div class="sub">(1,842 işlem, $64.20M size)</div>
            </div>
            <div class="card-right text-green">Veri Bekleniyor</div>
        </div>

        <!-- SHORT KARTI -->
        <div class="card card-short">
            <div class="card-left">
                <div class="title"><span class="dot-red"></span> <span class="text-red">SHORT Ort. Giriş:</span></div>
                <div class="sub">(1,520 işlem, $51.90M size)</div>
            </div>
            <div class="card-right text-red">Veri Bekleniyor</div>
        </div>

        <!-- ORTALAMA GİRİŞ KARTI -->
        <div class="card card-neutral">
            <div class="card-left">
                <div class="title"><span class="dot-white"></span> <span class="text-white">Ortalama Giriş:</span></div>
            </div>
            <div class="card-right text-white">Veri Bekleniyor</div>
        </div>

        <div class="refresh-info">Veriler her 5 dakikada bir otomatik güncellenir.</div>
    </div>

</body>
</html>
"""

@app.route("/")
def index():
    symbols = get_futures_symbols()
    selected_symbol = request.args.get("symbol", "BTCUSDT")
    if selected_symbol not in symbols:
        selected_symbol = "BTCUSDT"
        
    current_price = get_current_price(selected_symbol)
        
    return render_template_string(
        HTML_TEMPLATE, 
        symbols=symbols, 
        selected_symbol=selected_symbol,
        current_price=current_price
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
