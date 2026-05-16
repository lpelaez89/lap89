import streamlit as st
import pandas as pd
import requests

# Configuración de la página web
st.set_page_config(page_title="AI Player Placement", layout="wide", page_icon="🧠")

# --- FUNCIÓN PARA CONECTAR CON GEMINI ---
def analizar_con_gemini(prompt, api_key):
    if not api_key:
        return "⚠️ Por favor, ingresa tu API Key de Gemini en el panel lateral para ver este análisis."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "Eres un Director Deportivo y Scout Senior experto en analítica de datos. Tu tono es sumamente profesional, estratégico y vas directo al grano."}]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # Verifica si hay errores HTTP
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Error al conectar con Gemini API: {e}"

# --- INICIALIZACIÓN DE ESTADO ---
if 'df_jugador' not in st.session_state: st.session_state.df_jugador = None
if 'df_equipos' not in st.session_state: st.session_state.df_equipos = None
if 'df_plantilla' not in st.session_state: st.session_state.df_plantilla = None

# --- UI: PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración del Sistema")
    api_key_gemini = st.text_input("🔑 API Key de Gemini", type="password", help="Obtén una gratis en Google AI Studio")
    
    st.divider()
    st.header("📂 Carga de Datos (Drag & Drop)")
    st.markdown("Sube uno, varios o todos tus CSV a la vez. El sistema los clasificará automáticamente.")
    
    archivos_subidos = st.file_uploader(
        "Arrastra tus CSV aquí", 
        type=['csv'], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        for archivo in archivos_subidos:
            archivo.seek(0)
            df = pd.read_csv(archivo)
            cols = df.columns.tolist()
            
            # Clasificador Automático de Archivos según las columnas de los CSV de Driblab
            if 'Mins' in cols and 'Position' in cols:
                st.session_state.df_jugador = df
                st.success(f"✅ Estadísticas del Jugador cargadas")
            elif 'Liga' in cols and 'GAM' in cols:
                st.session_state.df_equipos = df
                st.success(f"✅ Estadísticas de Equipos cargadas")
            elif 'Edad' in cols and 'Fin de contrato' in cols:
                st.session_state.df_plantilla = df
                st.success(f"✅ Estadísticas de Plantilla cargadas")

# --- UI: CUERPO PRINCIPAL ---
st.title("🧠 AI Player Placement & Scouting")
st.markdown("Plataforma impulsada por Python y Gemini para identificar y justificar oportunidades de mercado.")

# =====================================================================
# PASO 1: ANÁLISIS DEL JUGADOR
# =====================================================================
if st.session_state.df_jugador is not None:
    st.header("Paso 1: Análisis e Interpretación del Perfil del Jugador")
    
    df_jugador = st.session_state.df_jugador
    
    # Extraer posición principal y calcular promedios (el CSV viene desglosado por partidos)
    posicion = df_jugador['Position'].mode()[0]
    columnas_numericas = df_jugador.select_dtypes(include='number').columns
    promedios = df_jugador[columnas_numericas].mean().round(2)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Métricas Promedio por Partido")
        st.dataframe(promedios, use_container_width=True)
    
    with col2:
        st.subheader("Análisis Cualitativo (Gemini AI)")
        if st.button("Generar Interpretación del Perfil", key="btn_p1"):
            with st.spinner("Analizando métricas con Inteligencia Artificial..."):
                stats_texto = ", ".join([f"{k}: {v}" for k, v in promedios.items()])
                prompt = f"""
                Analiza las siguientes métricas promedio por partido de un jugador que se desempeña como {posicion}. 
                Métricas: {stats_texto}.
                Tu tarea: Redacta un análisis cualitativo interpretando sus fortalezas y estilo de juego basándote en lo que sugieren los números. 
                NO copies y pegues sus números en el texto. Traduce los datos a conceptos tácticos de fútbol (ej. si tiene alta eficiencia aérea e intercepciones, habla de su contundencia como ancla defensiva).
                """
                respuesta_p1 = analizar_con_gemini(prompt, api_key_gemini)
                st.session_state.analisis_p1 = respuesta_p1
        
        if 'analisis_p1' in st.session_state:
            st.info(st.session_state.analisis_p1)

else:
    st.info("Esperando el archivo de Estadísticas del Jugador (CSV)...")
    st.stop() # Detiene la ejecución visual aquí hasta que se cumpla el paso


# =====================================================================
# PASO 2: IDENTIFICACIÓN DE OPORTUNIDADES (GAP ANALYSIS)
# =====================================================================
st.divider()
if st.session_state.df_equipos is not None:
    st.header("Paso 2: Búsqueda de Oportunidades en el Mercado")
    df_equipos = st.session_state.df_equipos
    
    kpis_equipos = df_equipos.select_dtypes(include='number').columns.tolist()
    
    kpis_clave = st.multiselect(
        "Selecciona en qué métricas es fuerte tu jugador para buscar equipos con DÉFICIT en ellas:",
        options=kpis_equipos,
        default=[kpis_equipos[0], kpis_equipos[1]] if len(kpis_equipos) > 1 else None
    )
    
    if kpis_clave:
        # Calcular equipos con peor rendimiento en los KPIs seleccionados (Asumimos que un valor más bajo es peor)
        # Sumamos el ranking de los equipos. Un ranking bajo significa déficit.
        df_equipos['Deficit_Score'] = df_equipos[kpis_clave].rank(ascending=True).sum(axis=1)
        equipos_oportunidad = df_equipos.sort_values('Deficit_Score').head(5)
        
        col3, col4 = st.columns([1, 2])
        with col3:
            st.subheader("Top 5 Clubes con Déficit")
            st.dataframe(equipos_oportunidad[['Equipo', 'Liga'] + kpis_clave].reset_index(drop=True), use_container_width=True)
        
        with col4:
            st.subheader("Justificación Estratégica (Gemini AI)")
            if st.button("Generar Justificación de Refuerzo", key="btn_p2"):
                with st.spinner("Buscando encaje táctico..."):
                    nombres_equipos = ", ".join(equipos_oportunidad['Equipo'].tolist())
                    prompt = f"""
                    Nuestro jugador destaca profundamente en las siguientes métricas: {', '.join(kpis_clave)}.
                    Tras analizar las ligas, hemos detectado que estos equipos tienen graves déficits estadísticos en esas mismas áreas: {nombres_equipos}.
                    Redacta una justificación de scouting explicando de forma persuasiva por qué el perfil de nuestro jugador encaja perfectamente para solucionar las carencias tácticas de estos equipos.
                    """
                    respuesta_p2 = analizar_con_gemini(prompt, api_key_gemini)
                    st.session_state.analisis_p2 = respuesta_p2
                    
            if 'analisis_p2' in st.session_state:
                st.success(st.session_state.analisis_p2)
else:
    st.warning("Para continuar, sube el archivo de Estadísticas de Ligas/Equipos (CSV).")
    st.stop()


# =====================================================================
# PASO 3: ANÁLISIS DE PLANTILLA Y REEMPLAZO
# =====================================================================
st.divider()
if st.session_state.df_plantilla is not None:
    st.header("Paso 3: Viabilidad y Reemplazo en Plantilla")
    df_plantilla = st.session_state.df_plantilla
    
    clubes_disponibles = df_plantilla['Equipo'].unique().tolist()
    club_seleccionado = st.selectbox("Selecciona la plantilla a analizar:", clubes_disponibles)
    
    df_club = df_plantilla[df_plantilla['Equipo'] == club_seleccionado]
    
    # Filtro automático: Buscamos jugadores mayores de 29 años o que acaben contrato pronto (ajustable)
    candidatos_reemplazo = df_club[(df_club['Edad'] >= 29) | (df_club['Minutos'] < 800)]
    
    col5, col6 = st.columns([1, 2])
    with col5:
        st.subheader(f"Jugadores Reemplazables en {club_seleccionado}")
        columnas_mostrar = ['Nombre', 'Posición', 'Edad', 'Fin de contrato', 'Minutos']
        # Filtramos columnas que existan para evitar errores
        columnas_seguras = [c for c in columnas_mostrar if c in candidatos_reemplazo.columns]
        st.dataframe(candidatos_reemplazo[columnas_seguras].reset_index(drop=True), use_container_width=True)
        
    with col6:
        st.subheader("Reporte de Integración (Gemini AI)")
        if st.button("Generar Sugerencia de Reemplazo", key="btn_p3"):
            with st.spinner("Evaluando viabilidad deportiva y financiera..."):
                datos_plantilla = candidatos_reemplazo[columnas_seguras].to_dict('records')
                prompt = f"""
                Estamos planeando ofrecer a nuestro jugador (fuerte en {', '.join(kpis_clave)}) al club {club_seleccionado}.
                Analizando su plantilla actual, hemos detectado a estos jugadores que podrían estar en fin de ciclo (ya sea por edad o falta de minutos):
                {datos_plantilla}
                
                Redacta un argumento indicando específicamente a quién o quiénes debería reemplazar nuestro jugador. Justifica los motivos deportivos (mejora de métricas) y de viabilidad de plantilla (liberar masa salarial, renovación generacional, expiración de contratos) por los que nuestro jugador se integraría de maravilla.
                """
                respuesta_p3 = analizar_con_gemini(prompt, api_key_gemini)
                st.session_state.analisis_p3 = respuesta_p3
                
        if 'analisis_p3' in st.session_state:
            st.info(st.session_state.analisis_p3)
else:
    st.warning("Para finalizar, sube el archivo de Estadísticas de la Plantilla (CSV).")
