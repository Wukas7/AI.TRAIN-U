import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error

def generar_plan_semanal(perfil, historial_mes_str):
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
        st.error(f"Error al generar el plan semanal: {e}")
        return None

def generar_plan_diario(perfil, historial_detallado_texto, datos_hoy, plan_semanal_actual, fecha_de_registro):
    """Genera el plan detallado para mañana con lógica de adaptación avanzada."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_manana = fecha_de_registro + timedelta(days=1)
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")

    prompt = f"""
    Eres un entrenador personal adaptativo de élite. Tu objetivo es crear un plan DETALLADO para mañana, tomando decisiones inteligentes basadas en la información real.

    **INFORMACIÓN DISPONIBLE:**

    1.  **PLAN ESTRATÉGICO SEMANAL:**
        - El plan original para la semana es: {plan_semanal_actual.get('Plan_Original_Completo', '')}
        - Según este plan, mañana ({dia_manana_nombre}) tocaría: **{lo_que_toca_manana}**.

    2.  **DATOS DEL DÍA REGISTRADO ({fecha_de_registro.strftime('%A, %d de %B')}):**
        - Entrenamiento Realizado y Notas: {datos_hoy.get('entreno', 'No especificado')}
        - Sensaciones: {datos_hoy.get('sensaciones', 'No especificadas')}
        - Nutrición y Descanso: Calorías={datos_hoy.get('calorias')}, Proteínas={datos_hoy.get('proteinas')}, Descanso={datos_hoy.get('descanso')} horas.

    3.  **PERFIL Y CONTEXTO DEL ATLETA:**
        - Perfil (Objetivos, Lesiones, etc.): {perfil}
        - Historial Detallado de Rendimiento (Series, Reps, Pesos): {historial_detallado_texto}

    **TU PROCESO DE DECISIÓN Y TAREAS (EN ESTE ORDEN):**

    1.  **REGLA CRÍTICA DE RECUPERACIÓN:** Compara el entrenamiento REALIZADO hoy (`{datos_hoy.get('entreno')}`) con el planificado para mañana (`{lo_que_toca_manana}`). Si los grupos musculares principales se solapan (ej: hoy hizo espalda y mañana toca espalda), **DEBES MODIFICAR EL PLAN DE MAÑANA**. Justifica el cambio de forma clara (ej: "Para asegurar una recuperación óptima..."). La salud y la recuperación son la máxima prioridad.

    2.  **PLAN DE ENTRENAMIENTO DETALLADO PARA MAÑANA:**
        - Basándote en tu decisión anterior, define el entrenamiento para mañana.
        - **Aplica Sobrecarga Progresiva:** Usa el "Historial Detallado de Rendimiento" para sugerir pesos y repeticiones que supongan un reto. Sé explícito (ej: "Press Banca: 3x8 con 82.5 kg").
        - **Respeta el Equipamiento:** Los ejercicios deben ser realizables con el equipamiento del usuario (`{perfil.get('Equipamiento')}`).

    3.  **PLAN DE DIETA Y CONSEJO:** Crea el plan de dieta y el consejo del día como de costumbre.

    4.  **RE-PLANIFICACIÓN SEMANAL (OPCIONAL):** Si el cambio realizado en el punto 1 es significativo, añade al final una sección `### 🔄 Sugerencia de Re-planificación Semanal` con una nueva estructura para los días restantes de la semana.

    **FORMATO DE SALIDA:**
    Usa el formato Markdown habitual con las secciones ### 🏋️ Plan de Entrenamiento para Mañana, ### 🥗 Plan de Dieta para Mañana, ### 💡 Consejo del Día y, si es necesario, ### 🔄 Sugerencia de Re-planificación Semanal.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None
