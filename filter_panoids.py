import json
import math
import glob
import sys
import folium
import webbrowser
import yaml

def distance(p1, p2):
    """ 
    Fórmula de Haversine: devuelve la distancia en KM entre coordenadas de latitud y longitud.
    Copiada de 1_get_panoid_info.py para consistencia.
    """
    R = 6373  # Radio de la Tierra en kilómetros
    lat1 = math.radians(p1[0])
    lon1 = math.radians(p1[1])
    lat2 = math.radians(p2[0])
    lon2 = math.radians(p2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def filter_panoids_by_distance(panoid_list, min_dist_km):
    """
    Filtra una lista de panoids, asegurando que cada panoid guardado esté
    al menos a 'min_dist_km' de distancia de todos los demás guardados.
    
    (Gracias al ordenamiento previo, si dos están muy cerca, 
    el más nuevo se guarda y el más viejo se descarta).
    """
    panos_filtrados = []

    print("Iniciando filtrado por distancia...")
    
    for i, panoid in enumerate(panoid_list):
        
        # Imprime el progreso
        if (i + 1) % 100 == 0:
            print(f"Procesando {i + 1} de {len(panoid_list)}... (Guardados: {len(panos_filtrados)})")

        current_point = (panoid['lat'], panoid['lon'])
        
        # Suponemos que lo vamos a mantener
        keep = True

        # Comparamos contra todos los panoids que ya hemos decidido mantener
        for kept_panoid in panos_filtrados:
            kept_point = (kept_panoid['lat'], kept_panoid['lon'])
            
            dist = distance(current_point, kept_point)
            
            if dist < min_dist_km:
                keep = False
                break
        
        if keep:
            panos_filtrados.append(panoid)

    print("Filtrado por distancia completado.")
    return panos_filtrados

if __name__ == "__main__":
    
    # --- Configuración ---
    # Define la distancia mínima en KILÓMETROS.
    DISTANCIA_MINIMA_KM = 0.050 # 50 metros
    
    ARCHIVO_SALIDA = "panoids_area3_50m.json"
    ARCHIVO_MAPA = "Filtro_Result.html"
    # ---------------------

    # 1. Encontrar el archivo JSON de panoids
    archivos_panoid = glob.glob('panoids_*.json')
    
    if not archivos_panoid:
        print("Error: No se encontró ningún archivo 'panoids_*.json' en esta carpeta.")
        print("Asegúrate de correr '1_get_panoid_info.py' primero.")
        sys.exit(1)
    
    if len(archivos_panoid) > 1:
        print(f"Advertencia: Se encontraron {len(archivos_panoid)} archivos 'panoids_*.json'.")
        print(f"Usando el primero encontrado: {archivos_panoid[0]}")
    
    ARCHIVO_ENTRADA = archivos_panoid[0]

    # 2. Cargar el archivo de entrada
    try:
        with open(ARCHIVO_ENTRADA, 'r') as f:
            panoids_originales = json.load(f)
        print(f"Archivo de entrada cargado: {ARCHIVO_ENTRADA} ({len(panoids_originales)} entradas)")
    except Exception as e:
        print(f"Error cargando {ARCHIVO_ENTRADA}: {e}")
        sys.exit(1)

    if not panoids_originales:
        print("Error: El archivo de panoids está vacío.")
        sys.exit(1)

    # -----------------------------------------------------------------
    # ¡NUEVO! PASO 2.5: Ordenar por fecha (más reciente primero)
    print("Ordenando panoids por fecha (más reciente primero)...")
    
    def get_date_key(panoid):
        # Asigna una fecha muy antigua (año 0) si 'year' o 'month' no existen.
        # Esto asegura que los panoids sin fecha se traten como los más antiguos.
        year = panoid.get('year', 0)
        month = panoid.get('month', 0)
        # Devolvemos una tupla (año, mes) para el ordenamiento
        return (year, month)

    panoids_originales.sort(key=get_date_key, reverse=True)
    
    # Verificación rápida (opcional)
    if panoids_originales:
        pan_nuevo = panoids_originales[0]
        pan_viejo = panoids_originales[-1]
        print(f"Panoid más reciente: {pan_nuevo.get('year')}-{pan_nuevo.get('month')} (Panoid: {pan_nuevo.get('panoid')})")
        print(f"Panoid más antiguo: {pan_viejo.get('year')}-{pan_viejo.get('month')} (Panoid: {pan_viejo.get('panoid')})")
    # -----------------------------------------------------------------

    # 3. Filtrar la lista
    print(f"Filtrando para mantener panoids con al menos {DISTANCIA_MINIMA_KM * 1000:.0f} metros de separación...")
    panoids_filtrados = filter_panoids_by_distance(panoids_originales, DISTANCIA_MINIMA_KM)

    # 4. Guardar el nuevo archivo JSON
    with open(ARCHIVO_SALIDA, 'w') as f:
        json.dump(panoids_filtrados, f, indent=2)

    print("\n--- ¡Proceso de filtrado completado! ---")
    print(f"Panoids originales: {len(panoids_originales)}")
    print(f"Panoids filtrados:   {len(panoids_filtrados)}")
    print(f"Resultados guardados en: {ARCHIVO_SALIDA}")
    
    # 5. GENERAR MAPA DE VISUALIZACIÓN
    print(f"\nGenerando mapa de visualización: {ARCHIVO_MAPA}...")

    try:
        # Cargar config.yaml para centrar el mapa
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
            center = config['center']
        zoom_start = 12
    except Exception as e:
        print(f"No se pudo cargar 'config.yaml' ({e}). Centrando el mapa en el primer panoid.")
        center = [panoids_originales[0]['lat'], panoids_originales[0]['lon']]
        zoom_start = 15

    M = folium.Map(location=center, tiles='OpenStreetMap', zoom_start=zoom_start)

    # Identificar los panoids eliminados
    panoids_filtrados_set = {p['panoid'] for p in panoids_filtrados}
    lista_eliminada = [p for p in panoids_originales if p['panoid'] not in panoids_filtrados_set]
    lista_conservada = panoids_filtrados

    print(f"Puntos conservados (Azul): {len(lista_conservada)}")
    print(f"Puntos eliminados (Rojo):  {len(lista_eliminada)}")

    # Dibujar puntos eliminados (Rojo)
    for pan in lista_eliminada:
        fecha = f"{pan.get('year', '????')}-{pan.get('month', '??')}"
        folium.CircleMarker(
            [pan['lat'], pan['lon']], 
            popup=f"ELIMINADO: {pan['panoid']}<br>Fecha: {fecha}", 
            radius=1, 
            color='red', 
            fill=True
        ).add_to(M)

    # Dibujar puntos conservados (Azul)
    for pan in lista_conservada:
        fecha = f"{pan.get('year', '????')}-{pan.get('month', '??')}"
        folium.CircleMarker(
            [pan['lat'], pan['lon']], 
            popup=f"CONSERVADO: {pan['panoid']}<br>Fecha: {fecha}", 
            radius=1, 
            color='blue', 
            fill=True
        ).add_to(M)

    # Guardar y abrir el mapa
    M.save(ARCHIVO_MAPA)
    print(f"¡Mapa guardado! Abriendo {ARCHIVO_MAPA} en tu navegador...")
    webbrowser.open(ARCHIVO_MAPA)