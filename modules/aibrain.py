import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error

# --- Funciones de IA (Con las nuevas modificaciones) ---
def generar_plan_semanal(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días con un formato estricto."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un planificador de fitness. Basado en el perfil del usuario, genera una estructura de entrenamiento para los 7 días de la semana.

    Perfil: {perfil}
    Historial del último mes: {historial_mes_str}

    **TU TAREA:**
    Genera una estructura de entrenamiento para los 7 días de la semana.

    **FORMATO OBLIGATORIO:**
    Debes responder con EXACTAMENTE 7 líneas.
    Cada línea DEBE empezar con el nombre del día de la semana (Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo), seguido de dos puntos y el plan.
    NO incluyas ninguna otra palabra, saludo o explicación antes o después de las 7 líneas.
    NO uses la palabra genérica 'Día'. Usa el nombre específico de cada día de la semana.

    **EJEMPLO DE RESPUESTA PERFECTA:**
    Lunes: Empuje (Pecho, Hombro, Tríceps)
    Martes: Tirón (Espalda, Bíceps)
    Miércoles: Pierna (Cuádriceps, Femoral)
    Jueves: Cardio y Abdominales
    Viernes: Empuje (Enfoque Hombro)
    Sábado: Tirón (Enfoque Espalda)
    Domingo: Descanso total
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semanal: {e}")
        return None

# (MODIFICADA) La IA ahora también puede sugerir una re-planificación
def generar_plan_diario(perfil, historial_str, datos_hoy, plan_semanal_actual):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # --- (NUEVO) AÑADIMOS LAS LÍNEAS QUE FALTABAN ---
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_manana_idx = (datetime.today().weekday() + 1) % 7
    dia_manana_nombre = dias_semana[dia_manana_idx]
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")
    # --------------------------------------------------

    prompt = f"""
    Eres un entrenador personal adaptativo. Tu objetivo es crear un plan DETALLADO para mañana y, si es necesario, re-planificar el resto de la semana.

    **CONTEXTO ESTRATÉGICO:**
    - El plan original para la semana es: {plan_semanal_actual.get('Plan_Original_Completo', '')}
    - Mañana es {dia_manana_nombre} y el plan dice que toca: **{lo_que_toca_manana}**.

    **REALIDAD (HOY):**
    - Perfil: {perfil}
    - Historial reciente: {historial_str}
    - Datos de hoy: {datos_hoy}

    **TU TAREA:**
    1. **Analiza el entrenamiento de hoy.** Compara lo que hice (`{datos_hoy['entreno']}`) con lo que estaba planeado.
    2. **Crea el plan detallado para mañana.** Adáptalo si mis sensaciones de hoy lo requieren (dolor, cansancio).
    3. **(IMPORTANTE) Re-planifica si es necesario.** Si el entrenamiento de hoy fue muy diferente a lo planeado (ej: hice pierna cuando tocaba pecho), el resto de la semana podría necesitar ajustes para mantener el equilibrio. Si crees que hay que cambiar el plan para los días siguientes, añade una sección al final de tu respuesta llamada `### 🔄 Sugerencia de Re-planificación Semanal` con la nueva estructura para los días que quedan. Si no hay cambios necesarios, no incluyas esta sección.
  
    **FORMATO DE RESPUESTA:**
    ### 🏋️ Plan de Entrenamiento para Mañana
    ...
    ### 🥗 Plan de Dieta para Mañana
    ...
    ### 💡 Consejo del Día
    ...
    (Opcional)
    ### 🔄 Sugerencia de Re-planificación Semanal
    Martes: ...
    Miércoles: ...
    Jueves: ...
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None
