import frappe
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

def get_chat_llm():
    settings = frappe.get_single("Financial AI Settings")
    if not settings.openai_api_key:
        frappe.throw("⚠️ Configura la API Key")
    return ChatOpenAI(
        model=settings.model_name or "gpt-5-mini", 
        api_key=settings.get_password("openai_api_key"), 
        temperature=0.7
    )

class ChatService:
    def chat(self, doc_name, user_message):
        # 1. Obtener el documento
        doc = frappe.get_doc("Financial Report", doc_name)

        # 2. Obtener los KPIs del reporte
        kpis = frappe.get_all(
            "Financial KPI",
            filters={"parent": doc_name, "parenttype": "Financial Report"},
            fields=["metric", "value"],
            order_by="idx asc"
        )
        kpis_str = "\n".join([f"  - {kpi.metric}: {kpi.value}" for kpi in kpis]) if kpis else "No hay KPIs disponibles"

        # 3. Construir el contexto (Memoria)
        messages = []

        # System Prompt: Le damos contexto financiero con todos los datos
        context_str = f"""
Eres un asesor financiero experto. Estás analizando el reporte financiero del periodo {doc.periodo} ({doc.tipo_periodo}).
Cliente: {doc.cliente}

INDICADORES CLAVE (KPIs):
{kpis_str}

RESUMEN EJECUTIVO:
{doc.summary or 'No disponible'}

INSIGHTS:
{doc.insights or 'No disponible'}

RIESGOS IDENTIFICADOS:
{doc.risks or 'No disponible'}

RECOMENDACIONES:
{doc.recomendations or 'No disponible'}

Responde al usuario basándote en estos datos. Sé directo, profesional y útil.
Cuando menciones cifras, usa los valores exactos de los KPIs.
        """
        messages.append(SystemMessage(content=context_str))

        # Historial de conversación previo
        for msg in doc.chat_history:
            if msg.role == "User":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        # 4. La nueva pregunta
        messages.append(HumanMessage(content=user_message))

        # 5. Llamar a la IA
        llm = get_chat_llm()
        response = llm.invoke(messages)
        ai_reply = response.content

        # 6. Guardar en el historial
        doc.append("chat_history", {"role": "User", "content": user_message})
        doc.append("chat_history", {"role": "AI", "content": ai_reply})
        doc.save(ignore_permissions=True)

        return ai_reply