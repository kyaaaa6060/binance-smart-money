from flask import Flask, render_template_string
import requests

app = Flask(__name__)

# Ekran görüntüsündeki tasarımı birebir yansıtan HTML/CSS şablonu
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ağırlıklı Ortalama Girişler - Smart Money</title>
    <style>
        body { background-color: #0b0e11; color: #eaecef; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 15px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; background: #1e2329; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2b313a; padding-bottom: 12px; margin-bottom: 15px; }
        .header h3 { margin: 0; font-size: 16px; color: #eaecef; display: flex; align-items: center; gap: 8px; }
        
        .filter-title { text-align: center; font-size: 13px; color: #848e9c; margin-bottom: 10px; }
        .filters { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 20px; }
        .filter-btn { background: #2b313a; border: 1px solid #2b313a; color: #848e9c; padding: 10px; border-radius: 8px; text-align: center; font-size: 12px; cursor: pointer; transition: 0.2s; }
        .filter-btn.active { border-color: #0ecb81; background: #1e2329; color: #eaecef; font-weight: bold; }
        
        .coin-title { text-align: center; color: #f0b90b; font-size: 15px; font-weight: bold; margin-bottom: 15px; letter-spacing: 1px; }
        
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
    </style>
</head>
<body>

    <div class="container">
        <div class="header">
            <h3>📊 Ağırlıklı Ortalama Girişler</h3>
            <span style="color: #848e9c; cursor: pointer; font-size: 18px;">✕</span>
        </div>

        <div class="filter-title">Veri Kaynağı Seçin:</div>
        <div class="filters">
            <div class="filter-btn active">👥 Sadece Copy Liderler</div>
            <div class="filter-btn">🐳 Sadece Balinalar</div>
            <div class="filter-btn">👥🐳 Tümü</div>
            <div class="filter-btn">📊 Veritabanı</div>
        </div>

        <div class="coin-title">BTCUSDT</div>

        <!-- LONG KARTI -->
        <div class="card card-long">
            <div class="card-left">
                <div class="title"><span class="dot-green"></span> <span class="text-green">LONG Ort. Giriş:</span></div>
                <div class="sub">(2181 işlem, $75.86M size)</div>
            </div>
            <div class="card-right text-green">$77.598,27</div>
        </div>

        <!-- SHORT KARTI -->
        <div class="card card-short">
            <div class="card-left">
                <div class="title"><span class="dot-red"></span> <span class="text-red">SHORT Ort. Giriş:</span></div>
                <div class="sub">(2149 işlem, $78.43M size)</div>
            </div>
            <div class="card-right text-red">$70.055,04</div>
        </div>

        <!-- ORTALAMA GİRİŞ KARTI -->
        <div class="card card-neutral">
            <div class="card-left">
                <div class="title"><span class="dot-white"></span> <span class="text-white">Ortalama Giriş:</span></div>
            </div>
            <div class="card-right text-white">$73.826,66</div>
        </div>
    </div>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
