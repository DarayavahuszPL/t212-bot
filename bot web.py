import os
import time
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# === KONFIGURACJA STRATEGII ===
API_KEY = "49312941ZVtuHpRSorFEozfExgzYSzpMDuHuV"  # Twój klucz tajny
BASE_URL = "https://live.trading212.com/api/v0/equity"
SYMBOL = "VUSA"  
WRAZLIWOSC_SIATKI = 0.01  
ILOSC_AKCJI = 9.66  

HEADERS = {
    "Authorization": API_KEY,
    "X-Trading212-Account-Type": "ISA"
}

def pobierz_aktualna_cene():
    # Pobieramy ceny bezpośrednio z otwartej pozycji w Twoim portfelu (100% odporne na błąd 501 na ISA)
    url = f"{BASE_URL}/portfolio"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            for pozycja in response.json():
                if pozycja.get('ticker') == SYMBOL:
                    # Wyciągamy aktualny kurs rynkowy aktywa z portfela
                    return float(pozycja.get('currentPrice'))
            print(f"Nie znaleziono otwartej pozycji dla {SYMBOL} w portfelu.")
        else:
            print(f"Błąd T212 (Portfel-Cena): Status {response.status_code}.")
    except Exception as e:
        print(f"Problem z połączeniem przy pobieraniu ceny: {e}")
    return None

def sprawdz_otwarte_pozycje():
    url = f"{BASE_URL}/portfolio"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            for pozycja in response.json():
                if pozycja.get('ticker') == SYMBOL:
                    return float(pozycja.get('quantity')), float(pozycja.get('averagePrice'))
        else:
            print(f"Błąd T212 (Portfel): Status {response.status_code}")
    except Exception as e:
        print(f"Problem z portfelem: {e}")
    return 0, 0

def zloz_zlecenie(typ, ilosc, cena=None):
    url = f"{BASE_URL}/orders"
    payload = {
        "ticker": SYMBOL,
        "quantity": ilosc,
        "timeInForce": "GOOD_TILL_CANCEL"
    }
    if cena:
        payload["orderType"] = "LIMIT"
        payload["limitPrice"] = cena
    else:
        payload["orderType"] = "MARKET"
        
    try:
        if typ == "KUP":
            response = requests.post(f"{url}/market" if not cena else f"{url}/limit", json=payload, headers=HEADERS, timeout=10)
        elif typ == "SPRZEDAJ":
            response = requests.post(f"{url}/market" if not cena else f"{url}/limit", json=payload, headers=HEADERS, timeout=10)
        return response.status_code
    except Exception as e:
        print(f"Błąd zlecenia {typ}: {e}")
        return None

def uruchom_bota():
    print("Bot Hardcore T212 wystartował w stabilnej chmurze...")
    
    # Odczekaj chwilę, aż serwer WWW się podniesie
    time.sleep(5)
    
    cena_zero = pobierz_aktualna_cene()
    if not cena_zero:
        print("Nie można pobrać ceny początkowej. Bot ponawia próby w tle...")
        cena_zero = 0.0

    while True:
        try:
            cena_rynkowa = pobierz_aktualna_cene()
            if not cena_rynkowa:
                time.sleep(30)
                continue
                
            if cena_zero == 0.0:
                cena_zero = cena_rynkowa
                print(f"🌍 Punkt startowy dla ISA ustalony na: £{cena_zero}")
                
            ilosc_akcji_w_portfelu, cena_zakupu = sprawdz_otwarte_pozycje()
            
            if ilosc_akcji_w_portfelu > 0:
                cel_take_profit = cena_zakupu * (1 + WRAZLIWOSC_SIATKI)
                if cena_rynkowa >= cel_take_profit:
                    print(f"🚀 Sukces! Cena £{cena_rynkowa}. Sprzedaję!")
                    status = zloz_zlecenie("SPRZEDAJ", ilosc_akcji_w_portfelu)
                    if status in [200, 202]:
                        cena_zero = cena_rynkowa 
            else:
                poziom_dokupienia = cena_zero * (1 - WRAZLIWOSC_SIATKI)
                if cena_rynkowa <= poziom_dokupienia:
                    print(f"📉 Spadek do £{cena_rynkowa}. Dokupuję...")
                    status = zloz_zlecenie("KUP", ILOSC_AKCJI)
            
            time.sleep(30)
        except Exception as e:
            print(f"Błąd pętli głównej: {e}")
            time.sleep(60)

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running active.")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        
def uruchom_serwer_www():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), WebServer)
    print(f"Serwer WWW nasłuchuje na porcie {port}...")
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=uruchom_bota)
    t.daemon = True
    t.start()
    uruchom_serwer_www()
