import streamlit as st
import streamlit_authenticator as stauth

# --- 1. CONSTRUIR EL DICCIONARIO DE CREDENCIALES ---
# Este es el paso clave. Construimos el diccionario con la estructura exacta que la librería necesita.
# Leemos las listas de los secrets y las unimos.

try:
    credentials = {
        "usernames": {
            username: {
                "name": name,
                "password": password,
            }
            for username, name, password in zip(
                st.secrets["credentials"]["usernames"],
                st.secrets["credentials"]["names"],
                st.secrets["credentials"]["passwords"],
            )
        }
    }
except KeyError as e:
    st.error(f"Error: No se pudo encontrar una de las claves (usernames, names, passwords) en tus Secrets. Revisa la sección [credentials]. Clave que falta: {e}")
    st.stop()


# --- 2. INICIALIZAR EL AUTENTICADOR ---
# Le pasamos el diccionario completo, el nombre de la cookie, la clave y la expiración.
authenticator = stauth.Authenticate(
    credentials,
    "mi_app_cookie",      # Nombre para la cookie
    "mi_clave_secreta",   # Clave secreta para encriptar la cookie
    30                    # Días de validez de la cookie
)

# --- 3. RENDERIZAR EL LOGIN Y LA LÓGICA DE LA APP ---
if authenticator.login(location='main'):
    # Si el login es exitoso, mostramos el contenido
    
    st.write(f"¡Bienvenido, *{st.session_state['name']}*!")
    st.title("¡LOGIN CORRECTO!")
    
    # El botón de logout
    authenticator.logout(location='main')

    # A partir de aquí, añadiríamos el resto de la aplicación (Google Sheets, Gemini, etc.)
    # Por ahora, lo dejamos así para confirmar que el login funciona.
