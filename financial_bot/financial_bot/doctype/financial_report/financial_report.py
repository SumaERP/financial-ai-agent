import frappe
from frappe.model.document import Document


class FinancialReport(Document):
    def autoname(self):
        """Generar nombre automático basado en periodo y cliente"""
        import hashlib
        from datetime import datetime

        # Si tiene periodo, usarlo como base
        if self.periodo:
            # Formato: FIN-2025-07-A1B2
            # Generar un hash corto de 4 caracteres basado en timestamp + cliente
            hash_input = f"{datetime.now().isoformat()}{self.cliente or ''}"
            short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:4].upper()
            self.name = f"FIN-{self.periodo}-{short_hash}"
        else:
            # Fallback: usar timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.name = f"FIN-{timestamp}"

    def before_insert(self):
        """Establecer estado inicial al crear el documento"""
        self.estado = "Por Subir"

    def on_update(self):
        """Crear User Permission automáticamente para el cliente"""
        self._sync_user_permissions()

    def _sync_user_permissions(self):
        """Sincroniza los User Permissions para usuarios del portal vinculados al cliente"""
        if not self.cliente:
            return

        # Obtener los usuarios del portal vinculados a este cliente
        portal_users = get_portal_users_for_customer(self.cliente)

        for user in portal_users:
            # Verificar si ya existe el User Permission
            existing = frappe.db.exists(
                "User Permission",
                {
                    "user": user,
                    "allow": "Financial Report",
                    "for_value": self.name
                }
            )
            if not existing:
                # Crear User Permission
                frappe.get_doc({
                    "doctype": "User Permission",
                    "user": user,
                    "allow": "Financial Report",
                    "for_value": self.name,
                    "apply_to_all_doctypes": 1
                }).insert(ignore_permissions=True)

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


def get_portal_users_for_customer(customer):
    """
    Obtiene los usuarios del portal vinculados a un Customer.
    Busca en Contact -> Dynamic Link -> Customer.
    """
    users = []

    # Buscar contactos vinculados a este Customer
    contacts = frappe.db.sql("""
        SELECT DISTINCT c.user
        FROM `tabContact` c
        INNER JOIN `tabDynamic Link` dl ON dl.parent = c.name AND dl.parenttype = 'Contact'
        WHERE dl.link_doctype = 'Customer'
        AND dl.link_name = %s
        AND c.user IS NOT NULL
        AND c.user != ''
    """, (customer,), as_dict=True)

    for contact in contacts:
        users.append(contact.user)

    return users


def get_customer_for_user(user):
    """Obtiene el Customer vinculado al usuario actual a través de Contact"""
    contact = frappe.db.get_value("Contact", {"user": user}, "name")
    if not contact:
        return None

    customer = frappe.db.get_value(
        "Dynamic Link",
        {
            "parent": contact,
            "parenttype": "Contact",
            "link_doctype": "Customer"
        },
        "link_name"
    )
    return customer


def get_permission_query_conditions(user):
    """
    Condiciones de query para filtrar Financial Reports.
    Los usuarios del portal solo ven reportes de su Customer.
    """
    if not user:
        user = frappe.session.user

    # System Manager y Administrator ven todo
    if "System Manager" in frappe.get_roles(user) or user == "Administrator":
        return ""

    # Para usuarios del portal, filtrar por su Customer
    if "Customer" in frappe.get_roles(user):
        customer = get_customer_for_user(user)
        if customer:
            return f"`tabFinancial Report`.cliente = {frappe.db.escape(customer)}"
        else:
            # Si no tiene Customer vinculado, no ve nada
            return "1=0"

    return ""


def has_permission(doc, ptype, user):
    """
    Valida si el usuario tiene permiso sobre un Financial Report específico.
    """
    if not user:
        user = frappe.session.user

    # System Manager y Administrator tienen acceso total
    if "System Manager" in frappe.get_roles(user) or user == "Administrator":
        return True

    # Para usuarios del portal
    if "Customer" in frappe.get_roles(user):
        customer = get_customer_for_user(user)
        if customer and doc.cliente == customer:
            return True
        return False

    # Otros roles con permiso en el DocType
    return True