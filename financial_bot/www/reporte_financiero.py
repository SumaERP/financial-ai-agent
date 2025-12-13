import frappe

no_cache = 1

def get_context(context):
    # Verificar usuario logueado
    if frappe.session.user == "Guest":
        frappe.throw("Debe iniciar sesión para ver este reporte", frappe.PermissionError)
    
    # Obtener el nombre del reporte desde la URL
    report_name = frappe.form_dict.get("name")
    if not report_name:
        frappe.throw("No se especificó el reporte", frappe.DoesNotExistError)
    
    # Obtener el Customer del usuario
    customer = get_customer_for_user(frappe.session.user)
    if not customer:
        frappe.throw("No tiene acceso a reportes", frappe.PermissionError)
    
    # Obtener el reporte y verificar pertenencia
    doc = frappe.get_doc("Financial Report", report_name)
    if doc.cliente != customer:
        frappe.throw("No tiene permiso para ver este reporte", frappe.PermissionError)
    
    context.doc = doc
    
    # Obtener KPIs si existen
    context.kpis = frappe.get_all(
        "Financial KPI",
        filters={"parent": report_name},
        fields=["metric", "value"],
        order_by="idx",
        ignore_permissions=True
    )
    
    return context


def get_customer_for_user(user):
    """Obtiene el Customer vinculado al usuario a través de Contact"""
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

