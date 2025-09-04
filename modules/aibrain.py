import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error

def generar_plan_semana(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días con un formato estricto."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un entrenador personal de élite. Tu tarea es diseñar una estructura de entrenamiento semanal.

    **PERFIL DEL USUARIO:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    - Lesiones/Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
    - Disponibilidad: {perfil.get('Disponibilidad', 'No especificada')}
    - Equipamiento: {perfil.get('Equipamiento', 'No especificado')}
    
    **HISTORIAL DEL ÚLTIMO MES:**
    {historial_mes_str}

    **INSTRUCCIONES:**
    1.  **Analiza la Disponibilidad:** Diseña un plan que se ajuste estrictamente al número de días disponibles. Si el usuario solo puede 3 días, el plan debe tener 3 días de entrenamiento y 4 de descanso/recuperación.
    2.  **Considera el Equipamiento:** Los tipos de entrenamiento que sugieras deben ser realizables con el material disponible.
    3.  **Usa el Historial:** Observa el historial para asegurar variedad y una progresión lógica.

    **FORMATO DE SALIDA OBLIGATORIO:**
    - Responde con EXACTAMENTE 7 líneas.
    - Cada línea DEBE empezar con el nombre del día de la semana (Lunes, Martes,...), seguido de dos puntos y el plan.
    - NO incluyas saludos, introducciones o cualquier otro texto. Solo las 7 líneas del plan.

    **EJEMPLO DE RESPUESTA PERFECTA (para disponibilidad de 4 días):**
    Lunes: Empuje (Pecho, Hombro, Tríceps)
    Martes: Tirón (Espalda, Bíceps)
    Miércoles: Descanso total
    Jueves: Pierna (Cuádriceps, Femoral)
    Viernes: Cardio y Abdominales
    Sábado: Descanso total
    Domingo: Descanso total
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semana: {e}")
        return None

def generar_plan_diario(perfil, historial_detallado_texto, datos_hoy, plan_semanal_actual, fecha_de_registro):
    """Genera el plan detallado para mañana con lógica de adaptación avanzada."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_manana = fecha_de_registro + timedelta(days=1)
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]

    
    try:
        lo_que_toca_manana = plan_semana_confirmado[plan_semana_confirmado['Día'] == dia_manana_nombre]['Plan'].iloc[0]
    except (IndexError, KeyError):
        lo_que_toca_manana = "Día libre"

    
    prompt = f"""
    Eres un entrenador personal de élite. Tu única tarea es crear un plan de entrenamiento y dieta DETALLADO para el objetivo específico que te doy.

    **TAREA PRINCIPAL:**
    Crear un plan detallado para el siguiente objetivo de entrenamiento: **{lo_que_toca_manana}**.

    **CONTEXTO ADICIONAL PARA TU DECISIÓN:**
    - **Perfil del Atleta:** {perfil}
    - **Rendimiento Histórico (Series, Reps, Pesos):** {historial_detallado_texto}
    - **Datos del Último Entrenamiento Registrado ({fecha_de_registro.strftime('%A')}):** {datos_dia_registrado}
    
     **INSTRUCCIONES DETALLADAS:**
    1.  **Plan de Entrenamiento:** Diseña la sesión para **{lo_que_toca_manana}**.
        - **Aplica Sobrecarga Progresiva:** Basándote en el "Rendimiento Histórico", sugiere pesos y repeticiones explícitos para progresar.
        - **Respeta el Equipamiento y las Sensaciones:** Asegúrate de que los ejercicios son adecuados. Adaptate a la disponibilidad.
    2.  **Plan de Dieta:** Proporciona un plan nutricional acorde.
    3.  **Consejo del Día:** Ofrece un consejo útil.
    4.  **RE-PLANIFICACIÓN SEMANAL (OPCIONAL):** Si el cambio realizado en el punto 1 es significativo, añade al final una sección `### 🔄 Sugerencia de Re-planificación Semanal` con una nueva estructura para los días restantes de la semana.


    **FORMATO DE SALIDA:**
    Usa el formato Markdown habitual con las secciones:
    ### 🏋️ Plan de Entrenamiento para Mañana
    ### 🥗 Plan de Dieta para Mañana
    ### 💡 Consejo del Día
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None
