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
    """Usa Gemini Vision para leer una imagen de estadísticas y devolverla como un diccionario estructurado"""
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
    texto_json = response.json()['candidates'][0]['content']['parts'][0]['text']
    return json.loads(texto_json)

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
    st.caption("Soporta CSV para Ligas/Plantillas y CSV o IMAGEN (PNG/JPG) para el Jugador.")
    
    archivos_subidos = st.file_uploader(
        "Arrastra tus archivos aquí", 
        type=['csv', 'png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        if st.button("🚀 Procesar Archivos y Comenzar", use_container_width=True):
            for archivo in archivos_subidos:
                archivo.seek(0)
                
                # SI ES UNA IMAGEN (Se asume que es el perfil del jugador)
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
                            st.error(f"Error procesando la imagen: {e}")
                
                # SI ES UN ARCHIVO CSV
                elif archivo.name.lower().endswith('.csv'):
                    try:
                        df = pd.read_csv(archivo)
                    except UnicodeDecodeError:
                        archivo.seek(0)
                        df = pd.read_csv(archivo, encoding='latin1')
                    
                    # Unimos todas las columnas en un solo texto para buscar palabras clave de forma súper segura
                    texto_cols = " ".join([str(c).strip().lower() for c in df.columns.tolist()])
                    
                    es_equipo = 'liga' in texto_cols and ('gam' in texto_cols or 'ppg' in texto_cols)
                    es_plantilla = 'edad' in texto_cols and ('contrato' in texto_cols or 'altura' in texto_cols)
                    es_jugador = 'mins' in texto_cols and ('position' in texto_cols or 'partido' in texto_cols)
                    
                    if es_jugador:
                        pos = df['Position'].mode()[0] if 'Position' in df.columns else "Jugador"
                        numericas = df.select_dtypes(include='number').columns
                        st.session_state.stats_jugador = df[numericas].mean().round(2).to_dict()
                        st.session_state.posicion_jugador = pos
                        st.success(f"✅ Jugador detectado (CSV): {archivo.name}")
                    elif es_equipo:
                        st.session_state.df_equipos = df
                        st.success(f"✅ Equipos detectados: {archivo.name}")
                    elif es_plantilla:
                        st.session_state.df_plantilla = df
                        st.success(f"✅ Plantilla detectada: {archivo.name}")
            
            # CONTROL DE FLUJO CORREGIDO (Evita que vuelva al paso 1 si subes archivos más tarde)
            if st.session_state.stats_jugador is not None:
                st.session_state.paso_actual = max(st.session_state.paso_actual, 1)
            else:
                st.error("No se detectó el archivo/imagen del Jugador.")

# --- UI: CUERPO PRINCIPAL ---
st.title("🧠 AI Player Placement & Scouting")
st.markdown("Plataforma interactiva impulsada por Python y Gemini Vision para identificar oportunidades de mercado.")
st.divider()

if st.session_state.paso_actual == 0:
    st.info("👈 Carga tus archivos (CSV/Imágenes) en el panel izquierdo y haz clic en 'Procesar'.")

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
                stats_texto = ", ".join([f"{k}: {v}" for k, v in stats_dict.items() if isinstance(v, (int, float)) and v > 0])
                
                # INSTRUCCIÓN DE IA ACTUALIZADA PARA SUGERIR MÉTRICAS DINÁMICAMENTE
                prompt = f"""
                Analiza estas métricas de un jugador en la posición: {posicion}. 
                Métricas: {stats_texto}.
                
                Realiza dos tareas:
                1. Redacta un análisis cualitativo de sus fortalezas y estilo de juego. NO copies sus números de manera robótica. Traduce los datos a conceptos tácticos reales de fútbol.
                2. Al final del análisis, incluye una sección destacada llamada "🎯 MÉTRICAS CLAVE SUGERIDAS PARA BÚSQUEDA:". En esta sección, enumera las métricas específicas donde este jugador es de élite (usa los nombres o abreviaturas exactas del glosario si aplican). Explica brevemente por qué estas métricas son ideales para buscar un equipo con déficit en el siguiente paso. La cantidad de métricas sugeridas dependerá de los datos (no uses una cantidad predefinida, sugiere solo las que realmente destaquen).
                """
                st.session_state.analisis_p1 = analizar_con_gemini(prompt, api_key_gemini)
        
        if 'analisis_p1' in st.session_state:
            st.info(st.session_state.analisis_p1)
            
    # Lógica de Botón mejorada con avisos
    if st.session_state.paso_actual == 1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.df_equipos is not None:
            if st.button("➡️ Siguiente Paso: Buscar Equipos con Déficit", type="primary"):
                st.session_state.paso_actual = 2
                st.rerun()
        else:
            st.warning("⚠️ Para avanzar a la Fase 2, sube el CSV de 'Estadísticas de Equipos' en el panel lateral y dale a Procesar.")

# =====================================================================
# PASO 2: GAP ANALYSIS (TOP 15)
# =====================================================================
if st.session_state.paso_actual >= 2:
    st.divider()
    st.header("Paso 2: Búsqueda de Oportunidades en el Mercado")
    df_equipos = st.session_state.df_equipos
    
    kpis_equipos = df_equipos.select_dtypes(include='number').columns.tolist()
    kpis_limpios = [k for k in kpis_equipos if k.lower() not in ['año', 'gam', 'ppg', 'p', 'xp']]
    
    kpis_clave = st.multiselect(
        "Selecciona las métricas que te sugirió la IA para buscar clubes con déficit:",
        options=kpis_limpios,
        default=kpis_limpios[:2] if len(kpis_limpios) >= 2 else None
    )
    
    if kpis_clave:
        df_equipos['Deficit_Score'] = df_equipos[kpis_clave].rank(ascending=True).sum(axis=1)
        equipos_oportunidad = df_equipos.sort_values('Deficit_Score').head(15)
        
        col3, col4 = st.columns([1, 2])
        with col3:
            st.subheader("Top 15 Clubes con Déficit")
            st.dataframe(equipos_oportunidad[['Equipo', 'Liga'] + kpis_clave].reset_index(drop=True), use_container_width=True)
        
        with col4:
            st.subheader("Justificación Estratégica (Gemini AI)")
            if st.button("Generar Justificación de Fichaje", key="btn_p2"):
                with st.spinner("Evaluando encaje táctico de los primeros resultados..."):
                    nombres_equipos_clave = ", ".join(equipos_oportunidad.head(6)['Equipo'].tolist())
                    prompt = f"""
                    Nuestro jugador destaca en: {', '.join(kpis_clave)}.
                    Estos son algunos de los equipos que tienen graves déficits estadísticos en esas áreas: {nombres_equipos_clave}.
                    Redacta una justificación de scouting explicando de forma persuasiva por qué nuestro jugador solucionaría las carencias tácticas en estas ligas/equipos.
                    """
                    st.session_state.analisis_p2 = analizar_con_gemini(prompt, api_key_gemini)
                    
            if 'analisis_p2' in st.session_state:
                st.success(st.session_state.analisis_p2)

    # Lógica de Botón mejorada con avisos
    if st.session_state.paso_actual == 2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.df_plantilla is not None:
            if st.button("➡️ Siguiente Paso: Analizar Viabilidad en Plantilla", type="primary"):
                st.session_state.paso_actual = 3
                st.rerun()
        else:
            st.warning("⚠️ Para avanzar a la Fase 3, sube el CSV de 'Estadísticas de Plantilla' en el panel lateral y dale a Procesar.")

# =====================================================================
# PASO 3: ANÁLISIS DE PLANTILLA
# =====================================================================
if st.session_state.paso_actual >= 3:
    st.divider()
    st.header("Paso 3: Viabilidad y Reemplazo en Plantilla")
    df_plantilla = st.session_state.df_plantilla
    
    col_nombres = [c for c in df_plantilla.columns if 'equipo' in c.lower()]
    nombre_col_equipo = col_nombres[0] if col_nombres else 'Equipo'
    
    clubes_disponibles = df_plantilla[nombre_col_equipo].dropna().unique().tolist()
    club_seleccionado = st.selectbox("Selecciona la plantilla objetivo para ver a quién reemplazar:", clubes_disponibles)
    
    df_club = df_plantilla[df_plantilla[nombre_col_equipo] == club_seleccionado]
    
    col_edad = [c for c in df_club.columns if 'edad' in c.lower()][0]
    col_min = [c for c in df_club.columns if 'minuto' in c.lower()][0]
    col_contrato = [c for c in df_club.columns if 'contrato' in c.lower()][0] if any('contrato' in c.lower() for c in df_club.columns) else 'Fin de contrato'
    col_nombre = [c for c in df_club.columns if 'nombre' in c.lower()][0] if any('nombre' in c.lower() for c in df_club.columns) else 'Nombre'
    col_posicion = [c for c in df_club.columns if 'posici' in c.lower()][0] if any('posici' in c.lower() for c in df_club.columns) else 'Posición'
    
    df_club[col_edad] = pd.to_numeric(df_club[col_edad], errors='coerce').fillna(0)
    df_club[col_min] = pd.to_numeric(df_club[col_min], errors='coerce').fillna(0)
    
    candidatos_reemplazo = df_club[(df_club[col_edad] >= 29) | (df_club[col_min] < 800)]
    
    col5, col6 = st.columns([1, 2])
    with col5:
        st.subheader(f"Candidatos a salir en {club_seleccionado}")
        columnas_mostrar = [col_nombre, col_posicion, col_edad, col_contrato, col_min]
        columnas_seguras = [c for c in columnas_mostrar if c in candidatos_reemplazo.columns]
        st.dataframe(candidatos_reemplazo[columnas_seguras].reset_index(drop=True), use_container_width=True)
        
    with col6:
        st.subheader("Reporte Final de Integración (Gemini AI)")
        if st.button("Generar Propuesta de Reemplazo", key="btn_p3"):
            with st.spinner("Cruzando datos financieros y deportivos..."):
                datos_plantilla = candidatos_reemplazo[columnas_seguras].to_dict('records')
                prompt = f"""
                Planeamos ofrecer a nuestro jugador al club {club_seleccionado}.
                Analizando su plantilla actual, estos jugadores podrían estar en fin de ciclo: {datos_plantilla}.
                
                Redacta un argumento comercial para el Director Deportivo indicando a quiénes reemplazaría nuestro jugador. Justifica los motivos deportivos y de viabilidad económica.
                """
                st.session_state.analisis_p3 = analizar_con_gemini(prompt, api_key_gemini)
                
        if 'analisis_p3' in st.session_state:
            st.info(st.session_state.analisis_p3)
