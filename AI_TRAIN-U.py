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

# --- 2. CONFIGURACIÓN DEL AUTENTICADOR (VERSIÓN FINAL Y A PRUEBA DE BALAS) ---
try:
    # Construimos el diccionario de credenciales
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
    
    # Leemos la configuración de la cookie explícitamente, valor por valor
    cookie_name = st.secrets['cookie']['name']
    cookie_key = st.secrets['cookie']['key']
    cookie_expiry = st.secrets['cookie']['expiry_days']

    # Creamos la instancia del autenticador con los valores correctos
    authenticator = stauth.Authenticate(
        credentials_data,
        cookie_name,
        cookie_key,
        cookie_expiry
    )

except KeyError as e:
    st.error(f"Error: No se encontró una clave en tus 'Secrets'. Revisa tu configuración.")
    st.error(f"Detalle del error (clave que falta): {e}")
    st.stop()


# --- 3. LÓGICA DE LOGIN Y EJECUCIÓN DE LA APP (MÉTODO MODERNO) ---
# Definimos las credenciales directamente en el código, sin leer de Secrets.
test_credentials = {
    "usernames": {
        "testuser": {
            "name": "Usuario de Prueba",
            # Pega aquí el hash FRESCO que acabas de generar para "1234"
            "password": "$2b$12$ivGKO5qn95vvhtZUARyxs.35SW.C1e/GwPykMcBa1eQxC.DbzVgbi" 
        }
    }
}

# Definimos la cookie directamente
cookie_name = "test_cookie"
cookie_key = "este_es_un_secreto_de_prueba"
cookie_expiry = 30

# Creamos la instancia del autenticador con los datos hardcodeados
authenticator = stauth.Authenticate(
    test_credentials,
    cookie_name,
    cookie_key,
    cookie_expiry
)
    # 3.2. Configuración de Gemini y Google Sheets (SOLO si el login es correcto)
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)

    google_creds_dict = st.secrets["gcp_service_account"] # Leemos la sección entera
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_perfil = spreadsheet.worksheet("Perfil")
    sheet_registro = spreadsheet.worksheet("Registro_Diario")

    # 3.3. Aquí van tus funciones (cargar_perfil, cargar_historial, generar_plan)
    # ... (Pega aquí tus funciones) ...

    # 3.4. Aquí va tu interfaz de Streamlit (el expander, el formulario, etc.)
    # ... (Pega aquí tu código de la interfaz) ...

# El código completo de tus funciones y la interfaz iría donde he puesto los comentarios.
# Si quieres, pego el código entero en la siguiente respuesta para que no haya dudas.
