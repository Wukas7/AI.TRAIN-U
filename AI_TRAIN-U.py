import streamlit as st
import streamlit_authenticator as stauth

# --- 1. LEER LA CONFIGURACIÓN DE LOS SECRETS ---
# Leemos la sección 'credentials' de nuestros secrets
credentials = st.secrets["credentials"]

# --- 2. INICIALIZAR EL AUTENTICADOR ---
# La inicialización ahora es mucho más simple según el ejemplo oficial
authenticator = stauth.Authenticate(
    credentials,
    "some_cookie_name",    # Nombre de la cookie
    "some_random_key",     # Clave secreta para la cookie
    30                     # Días de validez de la cookie
)

# --- 3. RENDERIZAR EL WIDGET DE LOGIN ---
# La función .login() ahora se encarga de todo
if authenticator.login(location='main'):
    # --- ESTE CÓDIGO SOLO SE EJECUTA SI EL LOGIN ES EXITOSO ---
    
    st.write(f"¡Bienvenido, *{st.session_state['name']}*!")
    st.title("Has iniciado sesión correctamente")
    
    # Mostramos el botón de logout
    authenticator.logout(location='main')

# La librería se encarga de mostrar los mensajes de error si el login falla,
# por lo que no necesitamos los bloques elif/else.
