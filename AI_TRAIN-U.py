# --- 1. IMPORTS Y CONFIGURACIÓN INICIAL ---
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime
import streamlit_authenticator as stauth

# Configura el título y layout de la página. Debe ser el primer comando de Streamlit.
st.set_page_config(page_title="AI.TRAIN-U", layout="wide")


# --- 2. CONFIGURACIÓN DE CLAVES Y SERVICIOS (leídos desde Secrets) ---
# Se configuran aquí arriba para que estén disponibles para toda la app.
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

google_creds_dict = {
    "type": st.secrets["gcp_service_account"]["type"],
    "project_id": st.secrets["gcp_service_account"]["project_id"],
    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
    "private_key": st.secrets["gcp_service_account"]["private_key"],
    "client_email": st.secrets["gcp_service_account"]["client_email"],
    "client_id": st.secrets["gcp_service_account"]["client_id"],
    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
}


# --- 3. CONFIGURACIÓN DEL AUTENTICADOR ---
credentials_data = {
    'usernames': {
        username: {
            'name': name,
            'password': password
        }
        for username, name, password in zip(
            st.secrets['credentials']['usernames'],
            st.secrets['credentials']['names'],
            st.secrets['credentials']['passwords']
        )
    }
}

# Leemos la configuración de la cookie desde los secrets
cookie_data = st.secrets['cookie']

# Creamos la instancia del autenticador pasándole los datos correctos
authenticator = stauth.Authenticate(
    credentials_data,
    cookie_data['name'],
    cookie_data['key'],
    cookie_data['expiry_days']
)

# --- 4. LÓGICA DE LOGIN Y EJECUCIÓN DE LA APP ---
# La función login ahora gestiona los estados internamente.
# El código que viene después solo se ejecuta si el login es exitoso.
if authenticator.login(location='main'):
    # ---- DENTRO DE ESTE IF VA TODO LO QUE EL USUARIO LOGUEADO PUEDE HACER ----
    
    # 4.1. Acceder a los datos del usuario y mostrar bienvenida/logout
    name = authenticator.credentials['usernames'][authenticator.username]['name']
    username = authenticator.username
    
    authenticator.logout(location='main')
    
    st.title(f"Planificador de {name}")
    st.write(f"Conectado como: **{username}**")
    st.divider()

    # 4.2. Conexión a Google Sheets (ahora que sabemos que el usuario es válido)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_perfil = spreadsheet.worksheet("Perfil")  # <-- Esto lo cambiaremos en el futuro
    sheet_registro = spreadsheet.worksheet("Registro_Diario") # <-- Esto también

    # 4.3. Definición de las funciones de la aplicación
    def cargar_perfil():
        """Carga los datos del perfil del usuario desde Google Sheets."""
        data = sheet_perfil.get_all_records()
        perfil_dict = {item['Variable']: item['Valor'] for item in data}
        return perfil_dict

    def cargar_historial():
        """Carga el historial de registros diarios."""
        data = sheet_registro.get_all_records()
        df = pd.DataFrame(data)
        return df

    def generar_plan(perfil, historial_str, datos_hoy):
        """Llama a la API de Gemini para generar el plan."""
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Eres un entrenador personal y nutricionista experto en IA. Tu objetivo es crear un plan de entrenamiento y dieta para mañana basado en mi perfil, mi historial y mis datos de hoy.

        **MI PERFIL:**
        - Objetivo: {perfil.get('Objetivo', 'No especificado')}
        - Edad: {perfil.get('Edad', 'No especificado')}
        - Peso: {perfil.get('Peso (kg)', 'No especificado')} kg
        - Altura: {perfil.get('Altura (cm)', 'No especificado')} cm
        - Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
        - Preferencias Comida: {perfil.get('Preferencias Comida', 'Ninguna')}

        **MI HISTORIAL RECIENTE (últimos días):**
        {historial_str}

        **DATOS DE HOY ({datetime.now().strftime('%Y-%m-%d')}):**
        - Calorías consumidas: {datos_hoy['calorias']} kcal
        - Proteínas consumidas: {datos_hoy['proteinas']} g
        - Entrenamiento realizado: {datos_hoy['entreno']}
        - Sensaciones (dolor, energía, motivación, etc.): {datos_hoy['sensaciones']}
        - Horas de descanso/sueño: {datos_hoy['descanso']} horas

        **TU TAREA:**
        Basado en TODA esta información, genera un plan claro y conciso para MAÑANA. El plan debe ser realista, adaptarse a mis sensaciones y ayudarme a progresar hacia mi objetivo.
        Responde en formato Markdown con las siguientes secciones:
        
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
            st.error(f"Error al contactar con la IA: {e}")
            return None

    # 4.4. Interfaz de Streamlit (el formulario y la lógica)
    st.header(f"Registro del día: {datetime.now().strftime('%d/%m/%Y')}")
    
    perfil_usuario = cargar_perfil()
    historial_df = cargar_historial()

    with st.expander("Ver mi Perfil y Historial"):
        st.subheader("Mi Perfil")
        st.write(perfil_usuario)
        st.subheader("Historial de Registros")
        st.dataframe(historial_df.tail(7))
    
    with st.form("registro_diario_form"):
        calorias = st.number_input("Calorías consumidas hoy (aprox.)", min_value=0, step=100)
        proteinas = st.number_input("Proteínas consumidas hoy (g)", min_value=0, step=10)
        entreno = st.text_area("¿Qué entrenamiento has hecho hoy? (Ej: Pecho y tríceps, 3 series de press banca...)")
        sensaciones = st.text_area("¿Cómo te sientes? (energía, dolor, motivación, etc.)")
        descanso = st.slider("¿Cuántas horas has dormido?", 0, 12, 8)
        submitted = st.form_submit_button("✅ Generar mi plan para mañana")

    if submitted:
        with st.spinner("Tu entrenador IA está pensando... 🧠"):
            datos_de_hoy = {
                "calorias": calorias, "proteinas": proteinas, "entreno": entreno,
                "sensaciones": sensaciones, "descanso": descanso
            }
            historial_texto = historial_df.tail(5).to_string()
            plan_generado = generar_plan(perfil_usuario, historial_texto, datos_de_hoy)

            if plan_generado:
                nueva_fila = [
                    datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno,
                    sensaciones, descanso, plan_generado
                ]
                sheet_registro.append_row(nueva_fila)
                st.success("¡Plan generado con éxito!")
                st.markdown(plan_generado)
