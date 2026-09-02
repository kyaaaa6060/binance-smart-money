import time
import requests

# Binance Vadeli İşlemler (Futures) Sembol Listesini Çeken Fonksiyon
def get_futures_symbols():
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        symbols = []
        for s in data.get("symbols", []):
            # Sadece USDT ile işlem gören vadeli coinleri alalım (örn: BTCUSDT, AVAXUSDT)
            if s["contractType"] == "PERPETUAL" and s["quoteAsset"] == "USDT":
                symbols.append(s["symbol"])
        return symbols
    except Exception as e:
        print(f"Semboller alınırken hata oluştu: {e}")
        return []

def fetch_smart_money_data():
    print("Binance vadeli coinler taranıyor...")
    symbols = get_futures_symbols()
    print(f"Toplam {len(symbols)} adet perpetual coin bulundu.")
    
    # Tüm coinler üzerinde dönüp verileri analiz edeceğimiz döngü
    for symbol in symbols:
        # Not: Binance'in o özel Smart Money ekranının arkada kullandığı
        # iç endpoint'leri buraya entegre edeceğiz.
        pass

if __name__ == "__main__":
    while True:
        fetch_smart_money_data()
        print("Tarama tamamlandı. 10 dakika sonra tekrar çalışacak...")
        time.sleep(600)
