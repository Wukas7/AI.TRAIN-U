import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error

# --- Funciones de IA (Con las nuevas modificaciones) ---
def generar_plan_semana(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días con un formato estricto."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un planificador de fitness de élite. Basado en el perfil completo del usuario, incluyendo su disponibilidad y equipamiento, genera una estructura de entrenamiento para los 7 días de la semana.
     
    **Perfil del Usuario:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    - Lesiones/Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
    - **Disponibilidad:** {perfil.get('Disponibilidad', 'No especificada')}
    - **Equipamiento:** {perfil.get('Equipamiento', 'No especificado')}
    
    Historial del último mes: {historial_mes_str}

    **TU TAREA:**
    Genera una estructura de entrenamiento para los 7 días de la semana.
    **CRÍTICO:** El plan DEBE ser realista y ajustarse estrictamente a la DISPONIBILIDAD del usuario. Si solo tiene 3 días, crea un plan de 3 días de entreno y 4 de descanso/recuperación.
    Los ejercicios sugeridos DEBEN ser realizables con el EQUIPAMIENTO disponible.
    
    **FORMATO OBLIGATORIO:**
    Debes responder con EXACTAMENTE 7 líneas.
    Cada línea DEBE empezar con el nombre del día de la semana (Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo), seguido de dos puntos y el plan.
    NO incluyas ninguna otra palabra, saludo o explicación antes o después de las 7 líneas.
    NO uses la palabra genérica 'Día'. Usa el nombre específico de cada día de la semana.

    **EJEMPLO DE RESPUESTA PERFECTA (si la disponibilidad es 4 días):**
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
        st.error(f"Error al generar el plan semanal: {e}")
        return None

def generar_plan_diario(perfil, historial_texto, datos_hoy, plan_semana_actual,fecha_de_registro):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_manana = fecha_de_registro + timedelta(days=1)
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]
    lo_que_toca_manana = plan_semana_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")
    # --------------------------------------------------

    prompt = f"""
    Eres un entrenador personal adaptativo. Tu objetivo es crear un plan DETALLADO para mañana y, si es necesario, re-planificar el resto de la semana.

    **CONTEXTO ESTRATÉGICO:**
    - El plan original para la semana es: {plan_semana_actual.get('Plan_Original_Completo', '')}
    - El día del registro es {fecha_de_registro.strftime('%A, %d de %B')}.
    - Por lo tanto, el plan a generar es para **mañana, {fecha_manana.strftime('%A, %d de %B')}**, y el plan general dice que toca: **{lo_que_toca_manana}**.

    **REALIDAD (HOY Y PERFIL):**
    - Perfil Completo:
        - Objetivo: {perfil.get('Objetivo', 'No especificado')}
        - Lesiones/Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
        - **Disponibilidad:** {perfil.get('Disponibilidad', 'No especificada')}
        - **Equipamiento:** {perfil.get('Equipamiento', 'No especificado')}
    - Historial reciente: {historial_str}
       
    **DATOS DEL ENTRENAMIENTO DE HOY ({fecha_de_registro.strftime('%d/%m')}):**
    - Sensaciones y datos generales: {datos_hoy}

    **HISTORIAL DETALLADO DE EJERCICIOS (PESOS Y REPETICIONES):**
    {historial_detallado_texto}
    
    **TU TAREA:**
    1. **ANALIZA EL HISTORIAL DETALLADO.** Fíjate en los pesos y repeticiones de los ejercicios clave de las últimas sesiones.
    2. **CREA EL PLAN DE ENTRENAMIENTO PARA MAÑANA APLICANDO SOBRECARGA PROGRESIVA.** Para cada ejercicio, sugiere un peso y número de repeticiones que suponga un reto basado en el historial. Por ejemplo, si la semana pasada hizo "Press Banca 3x8 80kg", sugiere "Press Banca 3x8 82.5kg" o "Press Banca 3x9 80kg". **Sé explícito con los pesos a usar.**
    3. **Analiza el entrenamiento de hoy.** Compara lo que hice (`{datos_hoy['entreno']}`) con lo que estaba planeado.
    4. **Crea el plan detallado para mañana.** Adáptalo si mis sensaciones de hoy lo requieren (dolor, cansancio). ** Los ejercicios específicos que elijas DEBEN ser realizables con el EQUIPAMIENTO disponible. Si el equipamiento es "solo peso corporal", no puedes sugerir press banca.
    5. **(IMPORTANTE) Re-planifica si es necesario.** Si el entrenamiento de hoy fue muy diferente a lo planeado (ej: hice pierna cuando tocaba pecho), el resto de la semana podría necesitar ajustes para mantener el equilibrio. Si crees que hay que cambiar el plan para los días siguientes, añade una sección al final de tu respuesta llamada `### 🔄 Sugerencia de Re-planificación Semanal` con la nueva estructura para los días que quedan. Si no hay cambios necesarios, no incluyas esta sección.
    6. **CREA EL PLAN DE DIETA Y EL CONSEJO DEL DÍA** como siempre.

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
