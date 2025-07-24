import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. FUNCIONES DE SEGURIDAD Y BASE DE DATOS DE LOGIN ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

# --- 2. FUNCIONES DE LA APLICACIÓN (GOOGLE SHEETS & GEMINI) ---

# --- Funciones de Carga de Datos ---
def cargar_perfil(client, username):
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Perfil")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df_usuario = df[df['UserID'] == username]
        if df_usuario.empty:
            return {"Error": "No se encontró perfil para este usuario."}
        return {row['Variable']: row['Valor'] for _, row in df_usuario.iterrows()}
    except Exception as e:
        return {"Error": f"Error al cargar perfil: {e}"}

def cargar_historial(client, username):
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Registro_Diario")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df[df['UserID'] == username]
    except Exception:
        return pd.DataFrame()

def cargar_plan_semana(client, username):
    """Carga el plan de la semana actual para un usuario."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Obtener el lunes de la semana actual
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        
        df_semana = df[(df['UserID'] == username) & (df['Semana_Del'] == lunes_actual)]
        
        if df_semana.empty:
            return None # No hay plan para esta semana
        return df_semana.iloc[0].to_dict() # Devuelve la fila como un diccionario
    except Exception:
        return None

# --- Funciones de Guardado/Actualización de Datos ---
def guardar_registro(client, username, nueva_fila_datos):
    sheet = client.open("AI.TRAIN-U").worksheet("Registro_Diario")
    fila_completa = [username] + nueva_fila_datos
    sheet.append_row(fila_completa)
    
def guardar_plan_semanal_nuevo(client, username, plan_generado):
    sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
    today = datetime.today()
    lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    # Extraemos el plan para cada día (requiere que la IA responda en un formato predecible)
    planes_diarios = plan_generado.split('\n')
    nueva_fila = [username, lunes_actual]
    for dia in dias:
        plan_dia = next((s for s in planes_diarios if s.startswith(dia)), f"{dia}: Descanso")
        nueva_fila.extend([plan_dia.split(': ')[1], "Pendiente"])
    nueva_fila.append(plan_generado) # Plan_Original_Completo
    
    sheet.append_row(nueva_fila)

def actualizar_estado_semanal(client, username, dia, estado):
    sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
    today = datetime.today()
    lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
    
    # Encontrar la fila correcta
    cell = sheet.find(lunes_actual)
    # Asumimos que el estado del día correspondiente está en una columna específica (esto puede necesitar ajuste)
    # Ej: Lunes_Estado es col 4, Martes_Estado es col 6, etc.
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    columna_estado = 3 + (dias_semana.index(dia) * 2) + 1
    sheet.update_cell(cell.row, columna_estado, estado)


# --- Funciones de IA ---
def generar_plan_semanal(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un planificador de fitness a largo plazo. Basado en el perfil de este usuario y su historial del último mes, genera una estructura de entrenamiento LÓGICA y EQUILIBRADA para los próximos 7 días.
    Perfil: {perfil}
    Historial: {historial_mes_str}
    
    Responde ÚNICAMENTE con la lista de 7 días, un día por línea, con el formato 'Día: Grupo Muscular o Actividad'. Sé conciso.
    Ejemplo de respuesta:
    Lunes: Pierna (enfoque cuádriceps)
    Martes: Empuje (Pecho, Hombro, Tríceps)
    Miércoles: Descanso activo o Cardio ligero
    Jueves: Espalda y Bíceps
    Viernes: Pierna (enfoque femoral)
    Sábado: Hombro y brazos
    Domingo: Descanso total
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semanal: {e}")
        return None

def generar_plan_diario(perfil, historial_reciente_str, datos_hoy, plan_semanal_actual):
    """Genera el plan detallado para mañana, usando el plan semanal como guía."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Determinar qué toca mañana según el plan semanal
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_manana_idx = (datetime.today().weekday() + 1) % 7
    dia_manana_nombre = dias_semana[dia_manana_idx]
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre según el plan")

    prompt = f"""
    Eres un entrenador personal que ajusta el plan día a día. Tu objetivo es crear el plan DETALLADO para mañana.

    **CONTEXTO GENERAL:**
    - El plan ESTRUCTURAL para esta semana es: {plan_semanal_actual.get('Plan_Original_Completo', '')}
    - Mañana es {dia_manana_nombre} y el plan dice que toca: **{lo_que_toca_manana}**

    **MI PERFIL:** {perfil}
    **MI HISTORIAL RECIENTE (últimos 2-3 días):** {historial_reciente_str}
    **DATOS DE HOY:** {datos_hoy}

    **TU TAREA:**
    1. **Valida si el plan de mañana ({lo_que_toca_manana}) sigue teniendo sentido.** Basado en mis sensaciones de hoy (ej: dolor, cansancio), recomienda un cambio si es necesario para optimizar la recuperación. Si haces un cambio, explícalo brevemente.
    2. **Crea el plan detallado para mañana.** Mantén el formato original que ya conoces.

   ### 🏋️ Plan de Entrenamiento para Mañana
    - Describe el tipo de entrenamiento (fuerza, cardio, descanso activo, etc.).
    - Lista los ejercicios con series y repeticiones. Sé específico.
    - Si hoy reporté dolor, adapta el entreno para no forzar esa zona.

    ### 🥗 Plan de Dieta para Mañana
    - Sugiere un objetivo de calorías y macronutrientes (proteínas, grasas, carbohidratos).
    - Da ejemplos de 3-4 comidas (desayuno, almuerzo, cena, snack) que cumplan con el objetivo y mis preferencias.

    ### 💡 Consejo del Día
    - Dame un consejo breve sobre motivación, técnica, recuperación o nutrición.

    Sé motivador pero realista. ¡Vamos a por ello!
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None

# --- 3. CÓDIGO PRINCIPAL DE LA APP ---
def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("🤖 AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        # --- PANTALLA DE LOGIN ---
        st.image("https://mir-s3-cdn-cf.behance.net/project_modules/fs/218fc872735831.5bf1e45999c40.gif")
        st.sidebar.header("Login")
        # ... (código de login sin cambios) ...
    
    else:
        # --- APLICACIÓN PRINCIPAL ---
        username = st.session_state['username']
        
        st.sidebar.success(f"Conectado como: **{username}**")
        if st.sidebar.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            st.rerun()

        # --- Conexión a servicios de Google ---
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        # --- Cargar datos ---
        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)
        plan_semana_actual = cargar_plan_semana(gspread_client, username)

        # --- SECCIÓN 1: PANEL SEMANAL ---
        st.header("🗓️ Tu Hoja de Ruta Semanal")

        if not plan_semana_actual:
            st.info("Aún no tienes un plan para esta semana.")
            if st.button("💪 ¡Generar mi plan para la semana!"):
                with st.spinner("Generando tu plan semanal estratégico..."):
                    historial_mes_str = historial_df.tail(30).to_string()
                    plan_semanal_generado = generar_plan_semanal(perfil_usuario, historial_mes_str)
                    if plan_semanal_generado:
                        guardar_plan_semanal_nuevo(gspread_client, username, plan_semanal_generado)
                        st.success("¡Plan semanal generado! Recargando...")
                        st.rerun()
        else:
            st.subheader("Plan Actualizado de la Semana")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            plan_data = {
                "Día": dias,
                "Plan": [plan_semana_actual.get(f"{dia}_Plan", "-") for dia in dias],
                "Estado": [plan_semana_actual.get(f"{dia}_Estado", "-") for dia in dias]
            }
            st.table(pd.DataFrame(plan_data).set_index("Día"))
            with st.expander("Ver Plan Original de la Semana"):
                st.text(plan_semana_actual.get("Plan_Original_Completo", "No disponible."))

        # --- SECCIÓN 2: REGISTRO DIARIO Y PLAN PARA MAÑANA ---
        st.divider()
        if "Error" in perfil_usuario:
            st.error(perfil_usuario["Error"])
        else:
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("Ver mi Perfil y Historial Completo", expanded=True):
                    st.subheader("Mi Perfil")
                    st.write(perfil_usuario)
                    st.subheader("Historial de Registros")
                    st.dataframe(historial_df)

            with col2:
                st.header("✍️ Registro del Día")
                with st.form("registro_diario_form"):
                    entreno = st.text_area("¿Qué entrenamiento has hecho hoy?")
                    sensaciones = st.text_area("¿Cómo te sientes? (energía, dolor, motivación, etc.)")
                    calorias = st.number_input("Calorías consumidas (aprox.)", min_value=0, step=100)
                    proteinas = st.number_input("Proteínas consumidas (g)", min_value=0, step=10)
                    descanso = st.slider("¿Cuántas horas has dormido?", 0.0, 12.0, 8.0, 0.5)
                    submitted = st.form_submit_button("✅ Generar plan para mañana")

                if submitted:
                    if not plan_semana_actual:
                         st.error("Primero debes generar un plan semanal antes de registrar tu día.")
                    else:
                        with st.spinner("Analizando tu día y preparando el plan de mañana..."):
                            datos_de_hoy = {
                                "entreno": entreno, "sensaciones": sensaciones,
                                "calorias": calorias, "proteinas": proteinas, "descanso": descanso
                            }
                            historial_reciente_str = historial_df.tail(3).to_string()
                            
                            # Generar el plan detallado para el día siguiente
                            plan_diario_generado = generar_plan_diario(perfil_usuario, historial_reciente_str, datos_de_hoy, plan_semana_actual)

                            if plan_diario_generado:
                                # Guardar el registro del día que acaba de pasar
                                nueva_fila_datos = [datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno, sensaciones, descanso, ""] # Dejamos el plan generado en blanco para no duplicar
                                guardar_registro(gspread_client, username, nueva_fila_datos)
                                
                                # Actualizar el estado del plan semanal (lógica simplificada)
                                dia_hoy_nombre = dias[(datetime.today().weekday())]
                                plan_hoy = plan_semana_actual.get(f"{dia_hoy_nombre}_Plan", "")
                                # Una lógica simple para ver si el entreno se parece
                                if entreno.lower() in plan_hoy.lower() or plan_hoy.lower() in entreno.lower():
                                    estado_hoy = "✅ Realizado"
                                else:
                                    estado_hoy = f"🔄 Modificado (Hizo: {entreno[:20]}...)"
                                actualizar_estado_semanal(gspread_client, username, dia_hoy_nombre, estado_hoy)

                                # Mostrar el plan de mañana
                                st.header("🚀 Tu Plan para Mañana")
                                st.success("¡Plan generado! Aquí tienes tu misión para mañana. Recargando para actualizar la tabla...")
                                st.markdown(plan_diario_generado)
                                # time.sleep(5) # Opcional: una pausa para que el usuario lea
                                # st.rerun() # Descomentar para recarga automática

if __name__ == '__main__':
    main()
