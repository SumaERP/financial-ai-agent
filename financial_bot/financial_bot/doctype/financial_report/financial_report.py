import frappe
from frappe.model.document import Document


class FinancialReport(Document):
    def before_insert(self):
        """Establecer estado inicial al crear el documento"""
        self.estado = "Por Subir"

    def validate(self):
        """Validar el formato del periodo según el tipo"""
        if self.tipo_periodo and self.periodo:
            self._validar_formato_periodo()

    def _validar_formato_periodo(self):
        """Valida que el periodo tenga el formato correcto"""
        import re
        if self.tipo_periodo == "Mensual":
            # Formato: YYYY-MM
            if not re.match(r'^\d{4}-\d{2}$', self.periodo):
                frappe.throw("Para periodo mensual, use el formato YYYY-MM (ej: 2025-07)")
        elif self.tipo_periodo == "Anual":
            # Formato: YYYY
            if not re.match(r'^\d{4}$', self.periodo):
                frappe.throw("Para periodo anual, use el formato YYYY (ej: 2025)")


@frappe.whitelist()
def procesar_reporte(doc_name):
    """
    Inicia el procesamiento del reporte financiero.
    Este método es llamado desde el botón 'Procesar' en el formulario.
    """
    doc = frappe.get_doc("Financial Report", doc_name)

    # Validar que tenga archivo adjunto
    if not doc.report_file:
        frappe.throw("Debe adjuntar un archivo PDF antes de procesar")

    # Validar que el estado sea correcto para procesar
    if doc.estado not in ["Por Subir", "Error"]:
        frappe.throw("El reporte ya está siendo procesado o ya fue completado")

    # Cambiar estado a Procesando
    doc.estado = "Procesando"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Enviar la tarea a segundo plano (Background Job)
    frappe.enqueue(
        'financial_bot.services.analysis.run_analysis_job',
        queue='long',
        timeout=1500,
        doc_name=doc.name
    )

    return {"success": True, "message": "El reporte está siendo procesado"}


@frappe.whitelist()
def send_chat_message(doc_name, message):
    """Enviar mensaje al chat del reporte"""
    from financial_bot.services.chat import ChatService
    service = ChatService()
    return service.chat(doc_name, message)