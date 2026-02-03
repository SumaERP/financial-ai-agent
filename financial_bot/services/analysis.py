import frappe
import json
import base64
from io import BytesIO
import fitz  # PyMuPDF
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def get_llm():
    settings = frappe.get_single("Financial AI Settings")
    if not settings.openai_api_key:
        frappe.throw("⚠️ Configura la API Key en 'Financial AI Settings'")
    
    model = settings.model_name or "gpt-5-mini"
    # Temperatura baja para ser precisos con los números, pero creativa para el texto
    return ChatOpenAI(model=model, api_key=settings.get_password("openai_api_key"), temperature=0.5)

class AnalysisService:
    def process_document(self, doc_name):
        try:
            # 1. Cargar Documento
            doc = frappe.get_doc("Financial Report", doc_name)
            file_doc = frappe.get_doc("File", {"file_url": doc.report_file})
            file_path = file_doc.get_full_path()

            # 2. Convertir PDF a Imágenes (Primeras 5 páginas) usando PyMuPDF
            images = []
            pdf_document = fitz.open(file_path)
            max_pages = min(5, len(pdf_document))
            for page_num in range(max_pages):
                page = pdf_document[page_num]
                # Renderizar página a imagen con buena resolución (2x zoom)
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            pdf_document.close()
            
            # 3. Prompt de "CFO Experto"
            prompt_text = """
            Actúa como un Director Financiero (CFO) experto. Analiza este reporte financiero.
            
            Tu objetivo es generar un JSON estructurado con insights estratégicos.
            NO des explicaciones previas, solo el JSON.

            Formato JSON requerido:
            {
                "period": "YYYY-MM",
                "summary": "Resumen ejecutivo profesional (2-3 oraciones enfocadas en rentabilidad y solvencia).",
                "kpis": [
                    {"metric": "Ingresos Totales", "value": "10M"},
                    {"metric": "Margen Neto", "value": "15%"},
                    {"metric": "ROE", "value": "12%"},
                    {"metric": "Deuda/Patrimonio", "value": "0.5x"}
                ],
                "insights": [
                    "Insight 1: Tendencia positiva en...",
                    "Insight 2: Se observa una caída en..."
                ],
                "recommendations": [
                    "Recomendación 1: Optimizar costos en...",
                    "Recomendación 2: Renegociar deuda..."
                ],
                "risks": [
                    "Riesgo 1: Posible falta de liquidez...",
                    "Riesgo 2: Alta exposición a..."
                ]
            }
            """
            
            content = [{"type": "text", "text": prompt_text}]
            for img in images:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}})

            # 4. Invocar a la IA
            llm = get_llm()
            response = llm.invoke([HumanMessage(content=content)])
            
            # 5. Limpiar y Parsear Respuesta
            clean_json = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # =========================================================
            # 🛑 SOLUCIÓN DEFINITIVA AL ERROR 1020
            # Instanciamos el documento de CERO justo antes de guardar
            # =========================================================
            
            # 1. Obtenemos el documento fresco de la base de datos
            new_doc = frappe.get_doc("Financial Report", doc_name)
            
            # 2. Actualizamos los campos en este nuevo objeto
            new_doc.period = data.get("period")
            new_doc.summary = data.get("summary")
            new_doc.insights = "\n".join(data.get("insights", []))
            new_doc.recomendations = "\n".join(data.get("recommendations", []))
            new_doc.risks = "\n".join(data.get("risks", []))
            new_doc.dashboard_view = self.generate_dashboard_html(data)
            
            # 3. Limpiamos y llenamos la tabla hija en el nuevo objeto
            new_doc.set("kpis", [])
            for kpi in data.get("kpis", []):
                new_doc.append("kpis", {
                    "metric": kpi.get("metric"),
                    "value": str(kpi.get("value"))
                })
            
            # 4. Cambiamos estado y guardamos
            new_doc.estado = "Listo"
            new_doc.flags.ignore_version = True
            new_doc.save(ignore_permissions=True)

            frappe.db.commit() # Forzar escritura en DB inmediatamente

            frappe.publish_realtime("msgprint", f"✅ Análisis completado para {new_doc.name}")

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Financial Bot Error: {str(e)}")
            # Intentar marcar como error en una instancia nueva
            try:
                err_doc = frappe.get_doc("Financial Report", doc_name)
                err_doc.estado = "Error"
                err_doc.flags.ignore_version = True
                err_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except:
                pass

    def list_to_html(self, items, icon, color):
        html = ""
        for item in items:
            html += f'<div style="margin-bottom: 8px; color: #4a5568;"><span style="color: {color}; margin-right: 8px;">{icon}</span>{item}</div>'
        return html

    def generate_dashboard_html(self, data):
        # Estilos Inline para que se vea bien en Frappe
        kpi_cards = ""
        for k in data.get("kpis", []):
            kpi_cards += f"""
            <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; min-width: 140px; flex: 1;">
                <div style="color: #718096; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">{k['metric']}</div>
                <div style="font-size: 20px; font-weight: 700; color: #2d3748; margin-top: 5px;">{k['value']}</div>
            </div>
            """

        insights_html = self.list_to_html(data.get('insights', []), "💡", "#d69e2e")
        recs_html = self.list_to_html(data.get('recommendations', []), "🚀", "#38a169")
        risks_html = self.list_to_html(data.get('risks', []), "⚠️", "#e53e3e")

        return f"""
        <div style="font-family: system-ui, -apple-system, sans-serif; background: #f7fafc; padding: 20px; border-radius: 12px;">
            
            <!-- Header -->
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0; color: #1a202c; font-size: 18px;">Resumen Ejecutivo</h3>
                <p style="color: #4a5568; line-height: 1.6; margin-top: 8px;">{data.get('summary')}</p>
            </div>

            <!-- KPIs -->
            <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px;">
                {kpi_cards}
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                
                <!-- Insights -->
                <div style="background: white; padding: 20px; border-radius: 10px; border-left: 4px solid #ecc94b; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <h4 style="margin-top: 0; color: #744210;">Hallazgos Clave</h4>
                    {insights_html}
                </div>

                <!-- Recomendaciones -->
                <div style="background: white; padding: 20px; border-radius: 10px; border-left: 4px solid #48bb78; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <h4 style="margin-top: 0; color: #22543d;">Recomendaciones</h4>
                    {recs_html}
                </div>

                <!-- Riesgos -->
                <div style="background: #fff5f5; padding: 20px; border-radius: 10px; border: 1px solid #fed7d7;">
                    <h4 style="margin-top: 0; color: #c53030;">Alertas de Riesgo</h4>
                    {risks_html}
                </div>
            </div>
        </div>
        """

def run_analysis_job(doc_name):
    service = AnalysisService()
    service.process_document(doc_name)

@frappe.whitelist()
def regenerate_dashboard(doc_name):
    """Regenera el dashboard HTML desde los datos existentes sin llamar a la IA"""
    doc = frappe.get_doc("Financial Report", doc_name)

    if doc.estado != "Listo":
        frappe.throw("El documento debe estar en estado 'Listo' para regenerar el dashboard")

    # Reconstruir datos desde los campos existentes
    kpis = []
    for row in doc.kpis:
        kpis.append({"metric": row.metric, "value": row.value})

    insights = [doc.insights] if doc.insights else []
    recommendations = [doc.recomendations] if doc.recomendations else []
    risks = [doc.risks] if doc.risks else []

    analysis_data = {
        "period": doc.period or "",
        "summary": doc.summary or "",
        "kpis": kpis,
        "insights": insights,
        "recommendations": recommendations,
        "risks": risks
    }

    # Regenerar el HTML del dashboard
    service = AnalysisService()
    dashboard_html = service.generate_dashboard_html(analysis_data)

    # Guardar
    doc.dashboard_view = dashboard_html
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return True