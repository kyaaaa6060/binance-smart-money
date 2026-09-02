from flask import Flask, render_template_string
import requests

app = Flask(__name__)

# Örnek HTML arayüz şablonu (Koyu tema, Binance tarzı)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Binance Smart Money Tracker</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #f0b90b; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e1e1e; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #2d2d2d; }
        th { background-color: #252525; color: #f0b90b; }
        .long { color: #0ecb81; font-weight: bold; }
        .short { color: #f6465d; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Binance Smart Money & Whales Dashboard</h1>
    <p style="text-align: center;">Tüm Vadeli Coinler Takipte...</p>
    <table>
        <tr>
            <th>Coin</th>
            <th>Toplam Pozisyon (USDT)</th>
            <th>Long / Short Oranı</th>
            <th>Durum</th>
        </tr>
        <tr>
            <td>AVAXUSDT</td>
            <td>35.96M</td>
            <td class="long">173.15%</td>
            <td>Aktif Taranıyor</td>
        </tr>
    </table>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
