import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kwduielzkoxlbwycuxdc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3ZHVpZWx6a294bGJ3eWN1eGRjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTgyMzgzMSwiZXhwIjoyMDk1Mzk5ODMxfQ.6npoHKX2OE7HBdSmd6Ruxt9qNngSrSYQWYoi-IUE6Ak") # Pon tu sb_secret aquí si pruebas local

KWORB_URL = "https://kworb.net/spotify/artist/5t5FqBwTcgKTaWmfEbwQY9_songs.html"

def run_scraper():
    print("⏳ Iniciando el Web Scraper de Compatibilidad Máxima...")
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Error al conectar con Supabase: {e}")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(KWORB_URL, headers=headers)
    if response.status_code != 200:
        print(f"❌ No se pudo acceder a Kworb: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # CAMBIO CRÍTICO: Buscamos TODAS las tablas sin importar su clase o atributos
    tables = soup.find_all('table')
    
    songs_data = []
    seen_codes = set()

    print(f"🔍 Analizando {len(tables)} tabla(s) detectada(s) en Kworb...")
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            # Aseguramos que la fila tenga al menos el título y los streams totales
            if not cells or len(cells) < 2:
                continue
                
            try:
                cell_title = cells[0]
                link_tag = cell_title.find('a')
                
                if link_tag and 'href' in link_tag.attrs:
                    raw_href = link_tag['href']
                    track_code = raw_href.split('/')[-1].replace('.html', '').strip()
                else:
                    # Alternativa si no hay enlace directo
                    track_code = cell_title.text.strip().lower().replace(" ", "_")

                # Si ya procesamos este código, lo saltamos para evitar duplicados en la misma subida
                if track_code in seen_codes:
                    continue

                raw_title = cell_title.text.strip()
                title = raw_title.replace("ENHYPEN - ", "").strip()
                
                # Extraer números limpiando comas
                total_streams_str = cells[1].text.replace(',', '').strip()
                total_streams = int(total_streams_str) if total_streams_str.isdigit() else 0
                
                daily_streams = 0
                if len(cells) > 2:
                    daily_streams_str = cells[2].text.replace(',', '').strip()
                    if daily_streams_str.isdigit():
                        daily_streams = int(daily_streams_str)

                # Saltamos filas basura (cabeceras duplicadas o strings vacíos)
                if title == "" or total_streams == 0:
                    continue

                song_entry = {
                    "title": title,
                    "total_streams": total_streams,
                    "daily_streams": daily_streams,
                    "track_code": track_code,
                    "updated_at": datetime.utcnow().isoformat() # Formato de fecha nativo y válido
                }
                
                songs_data.append(song_entry)
                seen_codes.add(track_code)
                
            except Exception:
                continue

    print(f"✔️ ¡Scraping terminado! Se detectaron {len(songs_data)} tracks individuales únicos.")

    if not songs_data:
        print("⚠️ No se encontraron datos válidos. Verifica si la URL de Kworb sigue activa.")
        return

    # Subida masiva controlada por track_code
    print(f"⏳ Realizando upsert masivo en Supabase de los {len(songs_data)} tracks...")
    try:
        result = supabase.table("spotify_songs").upsert(songs_data, on_conflict="track_code").execute()
        print(f"🎉 ¡Éxito total! Las {len(songs_data)} canciones han sido sincronizadas en Supabase.")
    except Exception as e:
        print(f"❌ Error al guardar datos en Supabase: {e}")

if __name__ == "__main__":
    run_scraper()
