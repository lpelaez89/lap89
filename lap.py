import streamlit as st
import pandas as pd
import requests
import json
import base64

# Configuración de la página web
st.set_page_config(page_title="AI Player Placement", layout="wide", page_icon="🧠")

# --- FUNCIONES PARA CONECTAR CON GEMINI ---

def obtener_instrucciones_sistema():
    return """Eres un Director Deportivo y Scout Senior experto en analítica de datos. Tu tono es sumamente profesional, estratégico y vas directo al grano.
    Comprendes a la perfección textos, métricas y contextos indistintamente en INGLÉS y ESPAÑOL.
    Comprendes a la perfección el siguiente glosario de métricas:
    - APD: Distancia Media de Pases (Average Pass Distance)
    - TWD%: Tackles/Fue Regateado (Tackles Won/Dribbled %)
    - AA: Acciones Agresivas (Aggressive Actions)
    - ROH: Recuperaciones en campo contrario
    - HDA%: % Acciones Defensivas Altas (High Defensive Actions %)
    - HR: Recuperaciones Peligrosas
    - SEHR: Recuperaciones Peligrosas y Tiro
    - PFTC: Pases al Último ⅓ Concedidos (Passes into Final Third Conceded)
    - SHO: Remates (Shots)
    - xG: Goles Esperados (Expected Goals)
    - xGOP: xG en Juego (xG Open Play)
    - ASS: Asistencias (Assists)
    - OPPOPPBS: Pases Completados al Área en Juego
    - xA: Asistencias Esperadas (Expected Assists)
    - xGC: Participación xG (xG Contribution/Chain)
    - BPFT: Prog. de Balón Último ⅓ (Ball Progression to Final Third)
    - PPP: Pases por Posesión (Passes Per Possession)
    - POHP: Pases Campo Contrario por Posesión
    - DP: Profundidad (Deep Progressions/Passes)
    
    Utiliza este conocimiento para enriquecer tus análisis sin necesidad de explicar la métrica al usuario, simplemente demostrando que sabes cómo impacta en el juego."""

def analizar_con_gemini(prompt, api_key):
    if not api_key:
        return "⚠️ Por favor, ingresa tu API Key de Gemini en el panel lateral."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": obtener_instrucciones_sistema()}]}
    }
    
    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=data)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Error al conectar con Gemini API: {e}"

def extraer_datos_imagen(image_bytes, mime_type, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    base64_img = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = """
    Extrae las estadísticas del jugador de esta imagen. Puede estar en inglés o español.
    Devuelve ÚNICAMENTE un objeto JSON estrictamente estructurado con este formato exacto:
    {
        "Posicion": "Posición detectada (ej. MC, DMC, FW, etc. Si no la dice, pon 'Desconocida')",
        "Stats": {
            "Nombre Métrica 1": 85.5,
            "Nombre Métrica 2": 12.0
        }
    }
    Asegúrate de que los valores sean números (float/int). Si hay porcentajes, conviértelos a número (ej. 85% -> 85).
    """
    
    data = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime_type, "data": base64_img}}
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=data)
    response.raise_for_status()
    return json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

def leer_csv_robusto(archivo):
    """Intenta leer el CSV superando problemas comunes de delimitadores y codificación"""
    try:
        df = pd.read_csv(archivo)
        if df.shape[1] == 1: # Posiblemente separado por punto y coma
            archivo.seek(0)
            df = pd.read_csv(archivo, sep=';')
    except UnicodeDecodeError:
        archivo.seek(0)
        df = pd.read_csv(archivo, encoding='latin1')
        if df.shape[1] == 1:
            archivo.seek(0)
            df = pd.read_csv(archivo, encoding='latin1', sep=';')
    return df

# --- INICIALIZACIÓN DE ESTADO PARA EL WIZARD ---
if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 0
if 'stats_jugador' not in st.session_state: st.session_state.stats_jugador = None
if 'posicion_jugador' not in st.session_state: st.session_state.posicion_jugador = None
if 'df_equipos' not in st.session_state: st.session_state.df_equipos = None
if 'df_plantilla' not in st.session_state: st.session_state.df_plantilla = None

# --- UI: PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración del Sistema")
    api_key_gemini = st.text_input("🔑 API Key de Gemini", type="password")
    
    st.divider()
    st.header("📂 Carga de Datos")
    st.caption("Soporta múltiples CSV y reconoce automáticamente si son Ligas, Plantillas o Jugadores.")
    
    archivos_subidos = st.file_uploader(
        "Arrastra TODOS tus archivos aquí", 
        type=['csv', 'png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        if st.button("🚀 Procesar Archivos y Comenzar", use_container_width=True):
            st.session_state.stats_jugador = None
            st.session_state.posicion_jugador = None
            st.session_state.df_equipos = None
            st.session_state.df_plantilla = None
            
            for archivo in archivos_subidos:
                archivo.seek(0)
                
                # PROCESAMIENTO DE IMAGEN
                if archivo.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    if not api_key_gemini:
                        st.error("⚠️ Para procesar imágenes necesitas ingresar la API Key arriba.")
                        st.stop()
                    
                    with st.spinner(f"Analizando imagen: {archivo.name}..."):
                        mime = f"image/{archivo.name.split('.')[-1].lower()}"
                        mime = "image/jpeg" if mime == "image/jpg" else mime
                        try:
                            datos_img = extraer_datos_imagen(archivo.read(), mime, api_key_gemini)
                            st.session_state.posicion_jugador = datos_img.get("Posicion", "Desconocida")
                            st.session_state.stats_jugador = datos_img.get("Stats", {})
                            st.success(f"✅ Jugador detectado (Imagen): {archivo.name}")
                        except Exception as e:
                            st.error(f"Error procesando la imagen {archivo.name}: {e}")
                
                # PROCESAMIENTO DE CSV
                elif archivo.name.lower().endswith('.csv'):
                    df = leer_csv_robusto(archivo)
                    texto_cols = " ".join([str(c).strip().lower() for c in df.columns.tolist()])
                    
                    # Heurística ultra-flexible para que no rechace archivos
                    es_plantilla = ('edad' in texto_cols or 'age' in texto_cols) and ('nombre' in texto_cols or 'name' in texto_cols or 'jugador' in texto_cols)
                    es_jugador = ('mins' in texto_cols or 'minuto' in texto_cols) and ('position' in texto_cols or 'partido' in texto_cols) and not es_plantilla
                    es_equipo = ('liga' in texto_cols or 'league' in texto_cols or 'gam' in texto_cols or 'equipo' in texto_cols) and not es_plantilla and not es_jugador
                    
                    if es_jugador:
                        pos = df['Position'].mode()[0] if 'Position' in df.columns else "Jugador"
                        numericas = df.select_dtypes(include='number').columns
                        st.session_state.stats_jugador = df[numericas].mean().round(2).to_dict()
                        st.session_state.posicion_jugador = pos
                        st.success(f"✅ Jugador (CSV): {archivo.name}")
                        
                    elif es_plantilla:
                        if st.session_state.df_plantilla is None:
                            st.session_state.df_plantilla = df
                        else:
                            st.session_state.df_plantilla = pd.concat([st.session_state.df_plantilla, df], ignore_index=True)
                        st.success(f"✅ Plantilla cargada: {archivo.name}")
                        
                    elif es_equipo:
                        if st.session_state.df_equipos is None:
                            st.session_state.df_equipos = df
                        else:
                            st.session_state.df_equipos = pd.concat([st.session_state.df_equipos, df], ignore_index=True)
                        st.success(f"✅ Equipos/Liga: {archivo.name}")
                    else:
                        st.warning(f"⚠️ No se pudo identificar el tipo del archivo: {archivo.name}")
            
            if st.session_state.stats_jugador is not None:
                st.session_state.paso_actual = max(st.session_state.paso_actual, 1)
            else:
                st.error("No se detectó el archivo o imagen principal del Jugador.")

# --- UI: CUERPO PRINCIPAL ---
st.title("🧠 AI Player Placement & Scouting")
st.markdown("Plataforma interactiva impulsada por Python y Gemini Vision para identificar oportunidades de mercado.")
st.divider()

if st.session_state.paso_actual == 0:
    st.info("👈 Carga todos tus archivos (CSV/Imágenes) en el panel izquierdo y haz clic en 'Procesar'.")

# =====================================================================
# PASO 1: ANÁLISIS DEL JUGADOR
# =====================================================================
if st.session_state.paso_actual >= 1:
    st.header("Paso 1: Análisis e Interpretación del Perfil")
    
    stats_dict = st.session_state.stats_jugador
    posicion = st.session_state.posicion_jugador
    
    df_stats_visual = pd.DataFrame(list(stats_dict.items()), columns=["Métrica", "Valor Promedio"])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"Métricas ({posicion})")
        st.dataframe(df_stats_visual, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("Análisis Cualitativo (Gemini AI)")
        if st.button("Generar Interpretación de Perfil", key="btn_p1"):
            with st.spinner("Analizando métricas y fortalezas..."):
                stats_texto = ", ".join([f"{k}: {v}" for k, v in stats_dict.items() if isinstance(v, (int, float, str))])
                
                prompt = f"""
                Analiza estas métricas de un jugador en la posición: {posicion}. 
                Métricas: {stats_texto}.
                
                Realiza dos tareas:
                1. Redacta un análisis cualitativo de sus fortalezas y estilo de juego. NO copies sus números de manera robótica. Traduce los datos a conceptos tácticos reales de fútbol.
                2. Al final, incluye una sección destacada llamada "🎯 MÉTRICAS CLAVE SUGERIDAS PARA BÚSQUEDA:". Enumera dinámicamente las métricas de élite de este jugador y explica brevemente por qué son ideales para buscar un equipo con déficit en el siguiente paso.
                """
                st.session_state.analisis_p1 = analizar_con_gemini(prompt, api_key_gemini)
        
        if 'analisis_p1' in st.session_state:
            st.info(st.session_state.analisis_p1)
            
    if st.session_state.paso_actual == 1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.df_equipos is not None:
            if st.button("➡️ Siguiente Paso: Buscar Equipos con Déficit", type="primary"):
                st.session_state.paso_actual = 2
                st.rerun()
        else:
            st.warning("⚠️ Para avanzar a la Fase 2, asegúrate de haber cargado los CSV de Ligas/Equipos.")

# =====================================================================
# PASO 2: GAP ANALYSIS (TOP 15)
# =====================================================================
if st.session_state.paso_actual >= 2:
    st.divider()
    st.header("Paso 2: Búsqueda de Oportunidades en el Mercado")
    df_equipos = st.session_state.df_equipos
    
    # Detección segura de columnas
    col_liga = [c for c in df_equipos.columns if 'liga' in c.lower() or 'league' in c.lower()]
    if col_liga:
        ligas_cargadas = df_equipos[col_liga[0]].dropna().unique().tolist()
        st.caption(f"🌍 Analizando {len(df_equipos)} equipos de {len(ligas_cargadas)} ligas: {', '.join(map(str, ligas_cargadas))}")
    else:
        st.caption(f"🌍 Analizando un total de {len(df_equipos)} equipos.")
    
    kpis_equipos = df_equipos.select_dtypes(include='number').columns.tolist()
    kpis_limpios = [k for k in kpis_equipos if k.lower() not in ['año', 'gam', 'ppg', 'p', 'xp', 'id', 'index']]
    
    kpis_clave = st.multiselect(
        "Selecciona las métricas que te sugirió la IA para buscar clubes con déficit:",
        options=kpis_limpios,
        default=kpis_limpios[:2] if len(kpis_limpios) >= 2 else None
    )
    
    if kpis_clave:
        # Sumamos el ranking. Un equipo con valor bajo en la métrica tendrá un rank bajo.
        df_equipos['Deficit_Score'] = df_equipos[kpis_clave].rank(ascending=True).sum(axis=1)
        equipos_oportunidad = df_equipos.sort_values('Deficit_Score').head(15)
        
        col_equipo_mostrar = [c for c in equipos_oportunidad.columns if 'equipo' in c.lower() or 'team' in c.lower()][0]
        columnas_tabla = [col_equipo_mostrar] + (col_liga if col_liga else []) + kpis_clave
        
        col3, col4 = st.columns([1, 2])
        with col3:
            st.subheader("Top 15 Clubes con Déficit")
            st.dataframe(equipos_oportunidad[columnas_tabla].reset_index(drop=True), use_container_width=True)
        
        with col4:
            st.subheader("Justificación Estratégica (Gemini AI)")
            if st.button("Generar Justificación de Fichaje", key="btn_p2"):
                with st.spinner("Evaluando encaje táctico de los resultados..."):
                    nombres_equipos_clave = ", ".join(equipos_oportunidad.head(6)[col_equipo_mostrar].astype(str).tolist())
                    prompt = f"""
                    Nuestro jugador destaca en: {', '.join(kpis_clave)}.
                    Estos equipos tienen graves déficits estadísticos en esas áreas: {nombres_equipos_clave}.
                    Redacta una justificación de scouting persuasiva explicando por qué nuestro jugador solucionaría sus carencias tácticas.
                    """
                    st.session_state.analisis_p2 = analizar_con_gemini(prompt, api_key_gemini)
                    
            if 'analisis_p2' in st.session_state:
                st.success(st.session_state.analisis_p2)

    if st.session_state.paso_actual == 2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.df_plantilla is not None:
            if st.button("➡️ Siguiente Paso: Analizar Viabilidad en Plantilla", type="primary"):
                st.session_state.paso_actual = 3
                st.rerun()
        else:
            st.warning("⚠️ Para avanzar a la Fase 3, sube los CSV de 'Estadísticas de Plantilla'.")

# =====================================================================
# PASO 3: ANÁLISIS DE PLANTILLA
# =====================================================================
if st.session_state.paso_actual >= 3:
    st.divider()
    st.header("Paso 3: Viabilidad y Reemplazo en Plantilla")
    df_plantilla = st.session_state.df_plantilla
    
    # Identificación súper robusta de columnas
    col_nombres_equipo = [c for c in df_plantilla.columns if 'equipo' in c.lower() or 'team' in c.lower() or 'club' in c.lower()]
    nombre_col_equipo = col_nombres_equipo[0] if col_nombres_equipo else None
    
    if not nombre_col_equipo:
        st.error("No se detectó la columna 'Equipo' o 'Club' en los archivos de plantilla.")
        st.stop()
        
    clubes_disponibles = df_plantilla[nombre_col_equipo].dropna().unique().tolist()
    clubes_disponibles = sorted([str(c) for c in clubes_disponibles]) # Orden alfabético para el cliente
    
    st.caption(f"📚 Se han consolidado los datos de **{len(clubes_disponibles)} plantillas** exitosamente.")
    club_seleccionado = st.selectbox("Selecciona el club objetivo para evaluar recambios:", clubes_disponibles)
    
    df_club = df_plantilla[df_plantilla[nombre_col_equipo].astype(str) == club_seleccionado].copy()
    
    # Asignación segura de variables
    col_edad = next((c for c in df_club.columns if 'edad' in c.lower() or 'age' in c.lower()), None)
    col_min = next((c for c in df_club.columns if 'minuto' in c.lower() or 'mins' in c.lower()), None)
    col_contrato = next((c for c in df_club.columns if 'contrato' in c.lower() or 'contract' in c.lower()), 'Fin de contrato')
    col_nombre = next((c for c in df_club.columns if 'nombre' in c.lower() or 'name' in c.lower() or 'jugador' in c.lower()), 'Nombre')
    col_posicion = next((c for c in df_club.columns if 'posici' in c.lower() or 'position' in c.lower()), 'Posición')
    
    # Limpieza anti-crashes de datos numéricos
    if col_edad: df_club[col_edad] = pd.to_numeric(df_club[col_edad], errors='coerce').fillna(0)
    if col_min: df_club[col_min] = pd.to_numeric(df_club[col_min], errors='coerce').fillna(0)
    
    # Filtro lógico
    edad_filtro = df_club[col_edad] >= 29 if col_edad else False
    min_filtro = df_club[col_min] < 800 if col_min else False
    
    candidatos_reemplazo = df_club[edad_filtro | min_filtro]
    
    col5, col6 = st.columns([1, 2])
    with col5:
        st.subheader(f"Candidatos a salir en {club_seleccionado}")
        columnas_mostrar = [c for c in [col_nombre, col_posicion, col_edad, col_contrato, col_min] if c in df_club.columns]
        
        if candidatos_reemplazo.empty:
            st.info("No se encontraron jugadores mayores de 29 años o con menos de 800 minutos en este club.")
            st.dataframe(df_club[columnas_mostrar].reset_index(drop=True), use_container_width=True)
        else:
            st.dataframe(candidatos_reemplazo[columnas_mostrar].reset_index(drop=True), use_container_width=True)
        
    with col6:
        st.subheader("Reporte Final de Integración (Gemini AI)")
        if st.button("Generar Propuesta de Reemplazo", key="btn_p3"):
            with st.spinner("Cruzando datos financieros y deportivos..."):
                datos_para_ia = candidatos_reemplazo[columnas_mostrar].to_dict('records') if not candidatos_reemplazo.empty else df_club.head(5).to_dict('records')
                prompt = f"""
                Planeamos ofrecer a nuestro jugador al club {club_seleccionado}.
                Analizando su plantilla actual, evalúa las siguientes opciones de jugadores que podrían salir: {datos_para_ia}.
                
                Redacta un argumento comercial para el Director Deportivo indicando a quiénes reemplazaría nuestro jugador. Justifica los motivos deportivos y de viabilidad económica (edad, fin de contratos, poco rodaje).
                """
                st.session_state.analisis_p3 = analizar_con_gemini(prompt, api_key_gemini)
                
        if 'analisis_p3' in st.session_state:
            st.info(st.session_state.analisis_p3)
