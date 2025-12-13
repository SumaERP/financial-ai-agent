import frappe

no_cache = 1

def get_context(context):
    """Obtiene los reportes financieros asignados al cliente logueado"""

    # DEBUG: mostrar info
    context.debug_user = frappe.session.user

    # Verificar que el usuario esté logueado
    if frappe.session.user == "Guest":
        frappe.throw("Debe iniciar sesión para ver sus reportes", frappe.PermissionError)

    # Obtener el Customer vinculado al usuario actual
    customer = get_customer_for_user(frappe.session.user)
    context.debug_customer = customer

    if customer:
        # Obtener reportes asignados a este cliente
        # Usamos ignore_permissions porque ya validamos el acceso por Customer
        reportes = frappe.get_all(
            "Financial Report",
            filters={"cliente": customer},
            fields=["name", "periodo", "tipo_periodo", "estado", "creation"],
            order_by="creation desc",
            ignore_permissions=True
        )
    else:
        reportes = []

    context.debug_reportes_count = len(reportes)
    context.reportes = reportes
    return context


def get_customer_for_user(user):
    """Obtiene el Customer vinculado al usuario actual"""
    
    # Buscar si hay un Contact con este usuario que esté vinculado a un Customer
    contact = frappe.db.get_value(
        "Contact",
        {"user": user},
        "name"
    )
    
    if contact:
        # Buscar el Link dinámico a Customer
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
    
    return None

