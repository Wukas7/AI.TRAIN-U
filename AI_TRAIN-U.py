import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime

# --- 1. FUNCIONES DE LOGIN ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

# --- 2. FUNCIONES DE LA APP ---
def cargar_perfil(client, username):
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Perfil")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
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
        df.columns = df.columns.str.strip()
        return df[df['UserID'] == username]
    except Exception:
        return pd.DataFrame()

def guardar_registro(client, username, nueva_fila_datos):
    sheet = client.open("AI.TRAIN-U").worksheet("Registro_Diario")
    fila_completa = [username] + nueva_fila_datos
    sheet.append_row(fila_completa)

def generar_plan_diario(perfil, historial_str, datos_hoy):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un entrenador personal y nutricionista experto en IA. Tu objetivo es crear un plan de entrenamiento y dieta para mañana basado en mi perfil, mi historial y mis datos de hoy.

    MI PERFIL: {perfil}
    MI HISTORIAL RECIENTE: {historial_str}
    DATOS DE HOY: {datos_hoy}

    TU TAREA:
    Basado en TODA esta información, genera un plan claro y conciso para MAÑANA.
    Responde en formato Markdown con las siguientes secciones:
    ### 🏋️ Plan de Entrenamiento para Mañana
    ### 🥗 Plan de Dieta para Mañana
    ### 💡 Consejo del Día
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA: {e}")
        return None

# --- 3. CÓDIGO PRINCIPAL ---
def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("🤖 AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.image("https://mir-s3-cdn-cf.behance.net/project_modules/fs/218fc8735831.5bf1e45999c40.gif")
        st.sidebar.header("Login")
        username_input = st.sidebar.text_input("Usuario")
        password_input = st.sidebar.text_input("Contraseña", type='password')
        if st.sidebar.button("Login"):
            hashed_pswd = make_hashes(password_input)
            result = login_user(username_input, hashed_pswd)
            if result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username_input
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrecta")
        st.info("Por favor, introduce tus credenciales para continuar.")
    
    else:
        # --- APP PRINCIPAL (SI EL LOGIN ES CORRECTO) ---
        username = st.session_state['username']
        
        st.sidebar.success(f"Conectado como: **{username}**")
        if st.sidebar.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            st.rerun()

        try:
            creds_dict = st.secrets["gcp_service_account"]
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            gspread_client = gspread.authorize(creds)
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

            perfil_usuario = cargar_perfil(gspread_client, username)
            historial_df = cargar_historial(gspread_client, username)

            if "Error" in perfil_usuario:
                st.error(perfil_usuario["Error"])
            else:
                with st.expander("Ver mi Perfil y Historial Completo"):
                    st.subheader("Mi Perfil")
                    st.write(perfil_usuario)
                    st.subheader("Historial de Registros")
                    st.dataframe(historial_df)
                
                st.header(f"✍️ Registro del Día")
                with st.form("registro_diario_form"):
                    entreno = st.text_area("¿Qué entrenamiento has hecho hoy?")
                    sensaciones = st.text_area("¿Cómo te sientes?")
                    calorias = st.number_input("Calorías consumidas (aprox.)", min_value=0, step=100)
                    proteinas = st.number_input("Proteínas consumidas (g)", min_value=0, step=10)
                    descanso = st.slider("¿Cuántas horas has dormido?", 0.0, 12.0, 8.0, 0.5)
                    submitted = st.form_submit_button("✅ Generar plan para mañana")

                if submitted:
                    with st.spinner("Tu entrenador IA está pensando... 🧠"):
                        datos_de_hoy = {"entreno": entreno, "sensaciones": sensaciones, "calorias": calorias, "proteinas": proteinas, "descanso": descanso}
                        historial_texto = historial_df.tail(5).to_string()
                        plan_generado = generar_plan_diario(perfil_usuario, historial_texto, datos_de_hoy)

                        if plan_generado:
                            nueva_fila_datos = [datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno, sensaciones, descanso, plan_generado]
                            guardar_registro(gspread_client, username, nueva_fila_datos)
                            st.success("¡Plan para mañana generado!")
                            st.markdown(plan_generado)
        
        except Exception as e:
            st.error("Ha ocurrido un error al conectar con los servicios de Google. Revisa tus credenciales y los permisos del Google Sheet.")
            st.error(f"Error detallado: {e}")

if __name__ == '__main__':
    main()
