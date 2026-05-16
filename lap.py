import streamlit as st
import pandas as pd
import requests

# Configuración de la página web
st.set_page_config(page_title="AI Player Placement", layout="wide", page_icon="🧠")

# --- FUNCIÓN PARA CONECTAR CON GEMINI ---
def analizar_con_gemini(prompt, api_key):
    if not api_key:
        return "⚠️ Por favor, ingresa tu API Key de Gemini en el panel lateral para generar este análisis."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # Inyectamos el glosario de métricas en el System Prompt para que la IA tenga contexto absoluto
    instrucciones_sistema = """Eres un Director Deportivo y Scout Senior experto en analítica de datos. Tu tono es sumamente profesional, estratégico y vas directo al grano.
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

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": instrucciones_sistema}]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Error al conectar con Gemini API: {e}"

# --- INICIALIZACIÓN DE ESTADO PARA EL WIZARD (PASO A PASO) ---
if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 0
if 'df_jugador' not in st.session_state: st.session_state.df_jugador = None
if 'df_equipos' not in st.session_state: st.session_state.df_equipos = None
if 'df_plantilla' not in st.session_state: st.session_state.df_plantilla = None

# --- UI: PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración del Sistema")
    api_key_gemini = st.text_input("🔑 API Key de Gemini", type="password", help="Obtén una gratis en Google AI Studio")
    
    st.divider()
    st.header("📂 Carga de Datos")
    
    archivos_subidos = st.file_uploader(
        "Arrastra los 3 archivos CSV aquí", 
        type=['csv'], 
        accept_multiple_files=True
    )

    # Botón explícito para iniciar el proceso
    if archivos_subidos:
        if st.button("🚀 Procesar Archivos y Comenzar", use_container_width=True):
            for archivo in archivos_subidos:
                archivo.seek(0)
                # Intento de lectura robusto (soporta diferentes formatos de CSV)
                try:
                    df = pd.read_csv(archivo)
                except UnicodeDecodeError:
                    archivo.seek(0)
                    df = pd.read_csv(archivo, encoding='latin1')
                
                # Limpiar nombres de columnas para evitar fallos por espacios o mayúsculas
                cols = [str(c).strip().lower() for c in df.columns.tolist()]
                
                # Clasificador Automático mejorado (detección extra robusta por fragmentos)
                es_jugador = any('mins' in c or 'minuto' in c for c in cols) and any('game' in c or 'partido' in c for c in cols)
                es_equipo = any('liga' in c for c in cols) and any('gam' in c or 'ppg' in c for c in cols)
                es_plantilla = any('edad' in c for c in cols) and any('equipo' in c for c in cols) and any('nombre' in c for c in cols)
                
                if es_jugador:
                    st.session_state.df_jugador = df
                    st.success(f"✅ Jugador detectado: {archivo.name}")
                elif es_equipo:
                    st.session_state.df_equipos = df
                    st.success(f"✅ Equipos detectados: {archivo.name}")
                elif es_plantilla:
                    st.session_state.df_plantilla = df
                    st.success(f"✅ Plantilla detectada: {archivo.name}")
            
            # Si se leyó al menos el del jugador, avanzamos al Paso 1
            if st.session_state.df_jugador is not None:
                st.session_state.paso_actual = 1
            else:
                st.error("No se detectó el archivo de Estadísticas del Jugador. Revisa que tenga las columnas 'Mins' y 'Position'.")

# --- UI: CUERPO PRINCIPAL ---
st.title("🧠 AI Player Placement & Scouting")
st.markdown("Plataforma interactiva impulsada por Python y Gemini para identificar oportunidades de mercado.")
st.divider()

# =====================================================================
# ESTADO 0: ESPERANDO ARCHIVOS
# =====================================================================
if st.session_state.paso_actual == 0:
    st.info("👈 Por favor, carga tus archivos CSV en el panel izquierdo y haz clic en el botón 'Procesar Archivos y Comenzar'.")

# =====================================================================
# PASO 1: ANÁLISIS DEL JUGADOR
# =====================================================================
if st.session_state.paso_actual >= 1:
    st.header("Paso 1: Análisis e Interpretación del Perfil del Jugador")
    df_jugador = st.session_state.df_jugador
    
    # Extraer posición y promedios
    posicion = df_jugador['Position'].mode()[0] if 'Position' in df_jugador.columns else "Jugador"
    columnas_numericas = df_jugador.select_dtypes(include='number').columns
    promedios = df_jugador[columnas_numericas].mean().round(2)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Métricas Promedio")
        st.dataframe(promedios, use_container_width=True)
    
    with col2:
        st.subheader("Análisis Cualitativo (Gemini AI)")
        if st.button("Generar Interpretación de Perfil", key="btn_p1"):
            with st.spinner("Analizando métricas con IA..."):
                stats_texto = ", ".join([f"{k}: {v}" for k, v in promedios.items() if v > 0])
                prompt = f"""
                Analiza estas métricas promedio por partido de un jugador en la posición: {posicion}. 
                Métricas: {stats_texto}.
                
                Realiza dos tareas:
                1. Redacta un análisis cualitativo de sus fortalezas y estilo de juego. NO copies sus números. Traduce los datos a conceptos tácticos de fútbol reales (ej. si tiene alta eficiencia aérea, habla de su contundencia).
                2. Sugiere y enlista las métricas específicas donde este jugador tiene un rendimiento destacado o de élite. La cantidad de métricas que sugieras NO debe ser predefinida; evalúa los números y selecciona dinámicamente solo aquellas métricas que realmente sean fortalezas clave para este jugador.
                """
                st.session_state.analisis_p1 = analizar_con_gemini(prompt, api_key_gemini)
        
        if 'analisis_p1' in st.session_state:
            st.info(st.session_state.analisis_p1)
            
    # Botón para avanzar al Paso 2
    if st.session_state.paso_actual == 1 and st.session_state.df_equipos is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➡️ Siguiente Paso: Buscar Equipos con Déficit", type="primary"):
            st.session_state.paso_actual = 2
            st.rerun()


# =====================================================================
# PASO 2: GAP ANALYSIS
# =====================================================================
if st.session_state.paso_actual >= 2:
    st.divider()
    st.header("Paso 2: Búsqueda de Oportunidades en el Mercado")
    df_equipos = st.session_state.df_equipos
    
    # Filtrar solo métricas relevantes (excluir Año, etc.)
    kpis_equipos = df_equipos.select_dtypes(include='number').columns.tolist()
    kpis_limpios = [k for k in kpis_equipos if k.lower() not in ['año', 'gam', 'ppg', 'p', 'xp']]
    
    kpis_clave = st.multiselect(
        "Selecciona las métricas fuertes de tu jugador para buscar clubes que necesiten mejorar en eso:",
        options=kpis_limpios,
        default=kpis_limpios[:2] if len(kpis_limpios) >= 2 else None
    )
    
    if kpis_clave:
        df_equipos['Deficit_Score'] = df_equipos[kpis_clave].rank(ascending=True).sum(axis=1)
        equipos_oportunidad = df_equipos.sort_values('Deficit_Score').head(5)
        
        col3, col4 = st.columns([1, 2])
        with col3:
            st.subheader("Top 5 Clubes con Déficit")
            st.dataframe(equipos_oportunidad[['Equipo', 'Liga'] + kpis_clave].reset_index(drop=True), use_container_width=True)
        
        with col4:
            st.subheader("Justificación Estratégica (Gemini AI)")
            if st.button("Generar Justificación de Fichaje", key="btn_p2"):
                with st.spinner("Evaluando encaje táctico..."):
                    nombres_equipos = ", ".join(equipos_oportunidad['Equipo'].tolist())
                    prompt = f"""
                    Nuestro jugador destaca en: {', '.join(kpis_clave)}.
                    Estos equipos tienen graves déficits estadísticos en esas áreas: {nombres_equipos}.
                    Redacta una justificación de scouting explicando de forma persuasiva por qué nuestro jugador solucionaría las carencias tácticas de estos equipos.
                    """
                    st.session_state.analisis_p2 = analizar_con_gemini(prompt, api_key_gemini)
                    
            if 'analisis_p2' in st.session_state:
                st.success(st.session_state.analisis_p2)

    # Botón para avanzar al Paso 3
    if st.session_state.paso_actual == 2 and st.session_state.df_plantilla is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➡️ Siguiente Paso: Analizar Viabilidad en Plantilla", type="primary"):
            st.session_state.paso_actual = 3
            st.rerun()


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
    
    # Filtro de reemplazos: Edad >= 29 o Minutos bajos
    col_edad = [c for c in df_club.columns if 'edad' in c.lower()][0]
    col_min = [c for c in df_club.columns if 'minuto' in c.lower()][0]
    
    # Manejo dinámico de las demás columnas por si varían o tienen espacios invisibles
    col_contrato = [c for c in df_club.columns if 'contrato' in c.lower()][0] if any('contrato' in c.lower() for c in df_club.columns) else 'Fin de contrato'
    col_nombre = [c for c in df_club.columns if 'nombre' in c.lower()][0] if any('nombre' in c.lower() for c in df_club.columns) else 'Nombre'
    col_posicion = [c for c in df_club.columns if 'posici' in c.lower()][0] if any('posici' in c.lower() for c in df_club.columns) else 'Posición'
    
    # Aseguramos que los valores sean numéricos para evitar errores de comparación
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
                
                Redacta un argumento comercial para el Director Deportivo indicando a quiénes reemplazaría nuestro jugador. Justifica los motivos deportivos y de viabilidad económica (masa salarial, fin de contratos, renovación).
                """
                st.session_state.analisis_p3 = analizar_con_gemini(prompt, api_key_gemini)
                
        if 'analisis_p3' in st.session_state:
            st.info(st.session_state.analisis_p3)
