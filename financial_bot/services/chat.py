import frappe
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pdf2image import convert_from_path
import base64
from io import BytesIO

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
        
        # 2. Construir el contexto (Memoria)
        messages = []
        
        # System Prompt: Le damos contexto financiero y los datos ya extraídos
        context_str = f"""
        Eres un asesor financiero experto. Estás analizando el reporte de {doc.period}.
        
        DATOS CLAVE YA EXTRAÍDOS:
        - Resumen: {doc.summary}
        - Insights: {doc.insights}
        - Riesgos: {doc.risks}
        - Recomendaciones: {doc.recomendations}
        
        Responde al usuario basándote en estos datos. Sé directo, profesional y útil.
        """
        messages.append(SystemMessage(content=context_str))
        
        # Historial de conversación previo
        for msg in doc.chat_history:
            if msg.role == "User":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        
        # 3. La nueva pregunta (Multimodal si es la primera vez, o Texto si ya hay contexto)
        # Nota: Para hacerlo rápido, usaremos el texto extraído. 
        # Si quisieras re-leer el PDF, aquí usarías pdf2image de nuevo.
        messages.append(HumanMessage(content=user_message))
        
        # 4. Llamar a la IA
        llm = get_chat_llm()
        response = llm.invoke(messages)
        ai_reply = response.content
        
        # 5. Guardar en el historial
        doc.append("chat_history", {"role": "User", "content": user_message})
        doc.append("chat_history", {"role": "AI", "content": ai_reply})
        doc.save(ignore_permissions=True)
        
        return ai_reply