import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime
import streamlit_authenticator as stauth

# --- CONFIGURACIÓN DEL LOGIN ---
# Lee la configuración desde los secrets
config = {
    'credentials': {
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
    },
    'cookie': {'name': 'ai_train_u_cookie', 'key': 'abcdef123456', 'expiry_days': 30},
}

# Crea la instancia del autenticador
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# --- PÁGINA DE LOGIN ---
authenticator.login(location='main')

# --- LÓGICA DE LA APLICACIÓN ---
if authenticator.login(location='main'):
    # Accedemos a los datos desde el objeto authenticator
    name = authenticator.credentials['usernames'][authenticator.username]['name']
    username = authenticator.username

    # Mostramos el botón de logout
    authenticator.logout(location='main')
    
    # Mensaje de bienvenida
    st.title(f"Bienvenido de nuevo, {name}!")
    st.write(f"Estás conectado como: **{username}**")
    st.divider()

elif authenticator.authentication_status == False:
    st.error('Usuario/contraseña es incorrecta')
elif authenticator.authentication_status == None:
    st.warning('Por favor, introduce tu usuario y contraseña para continuar')


# --- CONFIGURACIÓN INICIAL ---

# Configura el título de la página de Streamlit
st.set_page_config(page_title="AI.TRAIN-U", layout="wide")

# Clave de API de Google Gemini (¡REEMPLAZA ESTO!)
# Es más seguro usar st.secrets para desplegar, pero para uso local está bien así.
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Autenticación con Google Sheets
# Define los permisos (scopes) que necesita la aplicación
scopes = ["https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive"]

# Carga las credenciales desde los secrets de Streamlit
google_creds_dict = {
    "type": st.secrets["gcp_service_account"]["type"],
    "project_id": st.secrets["gcp_service_account"]["project_id"],
    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
    "private_key": st.secrets["gcp_service_account"]["private_key"], # SIN el .replace()
    "client_email": st.secrets["gcp_service_account"]["client_email"],
    "client_id": st.secrets["gcp_service_account"]["client_id"],
    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
}

creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)


client = gspread.authorize(creds)

# Abre la hoja de cálculo por su nombre
#spreadsheet_id = "1QWMMCp-nJkVucsqlSEYchpbZ9NNXi3rQK3NjT0jjnvs"
#spreadsheet = client.open_by_key(spreadsheet_id)
# O si prefieres open_by_url (pero con open_by_key es más directo si ya tienes el ID)
# spreadsheet = client.open_by_url(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
spreadsheet = client.open("AI.TRAIN-U")
sheet_perfil = spreadsheet.worksheet("Perfil")
sheet_registro = spreadsheet.worksheet("Registro_Diario")


# --- FUNCIONES AUXILIARES ---

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
    # El modelo de Gemini a utilizar
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Este es el "prompt", la instrucción que le damos a la IA. ¡Es la parte más importante!
    prompt = f"""
    Eres un entrenador personal y nutricionista experto en IA. Tu objetivo es crear un plan de entrenamiento y dieta para mañana basado en mi perfil, mi historial y mis datos de hoy.

    **MI PERFIL:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    - Peso: {perfil.get('Peso (kg)', 'No especificado')} kg
    - Altura: {perfil.get('Altura (cm)', 'No especificado')} cm
    - Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
    - Preferencias: {perfil.get('Preferencias Comida', 'Ninguna')}

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

# --- INTERFAZ DE STREAMLIT ---

st.title("🤖 Mi Entrenador Personal IA")
st.write("Registra tus datos diarios y obtén un plan personalizado para mañana.")

# Cargar datos
perfil_usuario = cargar_perfil()
historial_df = cargar_historial()

# Mostrar el perfil y el historial en la app
with st.expander("Ver mi Perfil y Historial"):
    st.subheader("Mi Perfil")
    st.write(perfil_usuario)
    st.subheader("Historial de Registros")
    st.dataframe(historial_df.tail(7)) # Mostrar los últimos 7 días

# Formulario para la entrada de datos del día
st.header(f"Registro del día: {datetime.now().strftime('%d/%m/%Y')}")

with st.form("registro_diario_form"):
    calorias = st.number_input("Calorías consumidas hoy (aprox.)", min_value=0, step=100)
    proteinas = st.number_input("Proteínas consumidas hoy (g)", min_value=0, step=10)
    entreno = st.text_area("¿Qué entrenamiento has hecho hoy? (Ej: Pecho y tríceps, 3 series de press banca...)")
    sensaciones = st.text_area("¿Cómo te sientes? (energía, dolor, motivación, etc.)")
    descanso = st.slider("¿Cuántas horas has dormido?", 0, 12, 8)
    
    submitted = st.form_submit_button("✅ Generar mi plan para mañana")

# Lógica cuando se envía el formulario
if submitted:
#    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSyAwLP-kMUy824nRxc3JiKseNXriJwV5dag":
#        st.error("Por favor, introduce tu clave de API de Gemini en el código.")
#    else:
        with st.spinner("Tu entrenador IA está pensando... 🧠"):
            # Preparar los datos para la IA
            datos_de_hoy = {
                "calorias": calorias,
                "proteinas": proteinas,
                "entreno": entreno,
                "sensaciones": sensaciones,
                "descanso": descanso
            }
            historial_texto = historial_df.tail(5).to_string() # últimos 5 días

            # Generar el plan
            plan_generado = generar_plan(perfil_usuario, historial_texto, datos_de_hoy)

            if plan_generado:
                # Guardar el registro en Google Sheets
                nueva_fila = [
                    datetime.now().strftime('%Y-%m-%d'), 
                    calorias, 
                    proteinas, 
                    entreno, 
                    sensaciones, 
                    descanso, 
                    plan_generado # Guardamos también lo que la IA generó
                ]
                sheet_registro.append_row(nueva_fila)
                
                # Mostrar el plan en la app
                st.success("¡Plan generado con éxito!")
                st.markdown(plan_generado)
