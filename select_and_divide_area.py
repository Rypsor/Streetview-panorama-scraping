import folium
from folium.plugins import Draw
import webbrowser
import os
import time
import json
import sys

# --- Configuración ---
MAP_FILE = 'select_area.html'
EXPORT_FILE = 'data.geojson'
OUTPUT_TXT_FILE = 'areas_divididas.txt' # <-- NUEVO: Archivo de salida
MEDELLIN_COORDS = [6.244, -75.581] 
# ---------------------

def generate_map():
    """
    Crea y guarda un mapa de Folium con el plugin de Dibujo.
    """
    m = folium.Map(location=MEDELLIN_COORDS, zoom_start=13)

    # Añadir el plugin de Dibujo
    draw_plugin = Draw(
        export=True,
        filename=EXPORT_FILE, 
        draw_options={
            'rectangle': True,
            'polyline': False,
            'polygon': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': False}
    )
    m.add_child(draw_plugin)

    folium.LatLngPopup().add_to(m)
    m.save(MAP_FILE)
    print(f"Mapa guardado como '{MAP_FILE}'")

def wait_for_export():
    """
    Espera en un bucle hasta que el usuario haya movido
    el archivo 'data.geojson' a la carpeta del script.
    """
    print("\n--- INSTRUCCIONES ---")
    print(f"1. Se ha abierto el mapa '{MAP_FILE}' en tu navegador.")
    print("2. Usa la herramienta de rectángulo (cuadrado) para dibujar tu área.")
    print("3. Haz clic en el botón 'Export' (icono de guardar) en el mapa.")
    print(f"4. Tu navegador descargará un archivo llamado '{EXPORT_FILE}'.")
    print(f"5. Mueve ese archivo a esta carpeta: {os.path.abspath(os.getcwd())}")
    print("\nEsperando a que aparezca el archivo 'data.geojson'...")

    while not os.path.exists(EXPORT_FILE):
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")
            cleanup_files()
            sys.exit()

    print(f"¡Archivo '{EXPORT_FILE}' detectado!")

# --- MODIFICADO ---
# Esta función ha sido actualizada para calcular 8 áreas (4x2)
# y escribirlas en un archivo .txt
# ------------------
def parse_and_save_areas():
    """
    Lee el archivo GeoJSON, extrae las coordenadas,
    calcula los cuadrantes (8 áreas, 4x2) y guarda los resultados en un .txt.
    """
    try:
        with open(EXPORT_FILE, 'r') as f:
            data = json.load(f)

        # Extraer las coordenadas del GeoJSON
        coords = data['features'][0]['geometry']['coordinates'][0]
        
        lons = [p[0] for p in coords]
        lats = [p[1] for p in coords]

        # Encontrar las esquinas
        top_lat = max(lats)
        bottom_lat = min(lats)
        left_lon = min(lons)
        right_lon = max(lons)

        # --- Lógica para 8 áreas (Cuadrícula 4x2) ---
        
        # 1. Calcular puntos de latitud (para 2 filas)
        # Necesitamos 3 puntos: top, mid, bottom
        mid_lat = (top_lat + bottom_lat) / 2
        lat_points = [top_lat, mid_lat, bottom_lat]
        
        # 2. Calcular puntos de longitud (para 4 columnas)
        # Necesitamos 5 puntos: left, cut1, cut2, cut3, right
        total_lon_width = right_lon - left_lon
        lon_step = total_lon_width / 4
        lon_points = [
            left_lon,
            left_lon + lon_step,
            left_lon + (2 * lon_step),
            left_lon + (3 * lon_step),
            right_lon
        ]
        # --- Fin de la lógica ---

        print("\n--- ¡Cálculo Completo! ---")
        
        # Abrir el archivo de salida para escribir
        with open(OUTPUT_TXT_FILE, 'w', encoding='utf-8') as f:
            
            # Escribir el rectángulo principal
            f.write("### Rectángulo Principal (para config.yaml)\n")
            f.write(f"top_left: [{top_lat}, {left_lon}]\n")
            f.write(f"bottom_right: [{bottom_lat}, {right_lon}]\n")
            f.write("\n" + "="*30 + "\n\n")
            
            print(f"Escribiendo 8 sub-áreas en '{OUTPUT_TXT_FILE}'...")

            # Bucle para crear las 8 sub-áreas (2 filas, 4 columnas)
            box_counter = 1
            for r in range(2): # 2 filas (Fila 0 = Arriba, Fila 1 = Abajo)
                current_top_lat = lat_points[r]
                current_bottom_lat = lat_points[r+1]
                
                for c in range(4): # 4 columnas
                    current_left_lon = lon_points[c]
                    current_right_lon = lon_points[c+1]
                    
                    # Escribir la información de la sub-área
                    f.write(f"# Sub-área {box_counter} (Fila {r+1}, Col {c+1})\n")
                    f.write(f"top_left: [{current_top_lat}, {current_left_lon}]\n")
                    f.write(f"bottom_right: [{current_bottom_lat}, {current_right_lon}]\n\n")
                    
                    box_counter += 1
        
        print(f"¡Éxito! Coordenadas guardadas en '{OUTPUT_TXT_FILE}'.")
        print(f"Puedes copiar y pegar estas coordenadas en tu 'config.yaml' para procesar cada área.")


    except Exception as e:
        print(f"\nError procesando el archivo '{EXPORT_FILE}': {e}")
        print("Asegúrate de que sea un GeoJSON válido exportado desde el mapa.")

def cleanup_files():
    """
    Limpia los archivos temporales generados.
    (El .txt de salida se conserva)
    """
    if os.path.exists(MAP_FILE):
        os.remove(MAP_FILE)
        print(f"\nArchivo de mapa '{MAP_FILE}' eliminado.")
    if os.path.exists(EXPORT_FILE):
        os.remove(EXPORT_FILE)
        print(f"Archivo de datos '{EXPORT_FILE}' eliminado.")

if __name__ == "__main__":
    try:
        # 1. Crear el mapa
        generate_map()
        
        # 2. Abrir el mapa en el navegador
        webbrowser.open('file://' + os.path.realpath(MAP_FILE))
        
        # 3. Esperar a que el usuario exporte y mueva el archivo
        wait_for_export()
        
        # 4. Procesar el archivo y guardar resultados
        parse_and_save_areas() # <-- MODIFICADO

    finally:
        # 5. Limpiar los archivos
        cleanup_files()