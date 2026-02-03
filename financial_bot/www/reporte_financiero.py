import frappe
from frappe.utils.pdf import get_pdf

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

    # Obtener historial del chat
    context.chat_history = frappe.get_all(
        "Financial Chat Message",
        filters={"parent": report_name, "parenttype": "Financial Report"},
        fields=["role", "content"],
        order_by="idx asc",
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


@frappe.whitelist()
def clear_chat_history(report_name):
    """Limpia el historial del chat de un reporte"""
    if frappe.session.user == "Guest":
        frappe.throw("Debe iniciar sesión", frappe.PermissionError)

    # Verificar acceso
    customer = get_customer_for_user(frappe.session.user)
    if not customer:
        frappe.throw("No tiene acceso a reportes", frappe.PermissionError)

    doc = frappe.get_doc("Financial Report", report_name)
    if doc.cliente != customer:
        frappe.throw("No tiene permiso para este reporte", frappe.PermissionError)

    # Limpiar el historial
    doc.chat_history = []
    doc.save(ignore_permissions=True)

    return {"success": True}


@frappe.whitelist()
def generate_pdf(report_name):
    """Genera un PDF del análisis del reporte financiero"""
    if frappe.session.user == "Guest":
        frappe.throw("Debe iniciar sesión", frappe.PermissionError)

    # Verificar acceso
    customer = get_customer_for_user(frappe.session.user)
    if not customer:
        frappe.throw("No tiene acceso a reportes", frappe.PermissionError)

    doc = frappe.get_doc("Financial Report", report_name)
    if doc.cliente != customer:
        frappe.throw("No tiene permiso para ver este reporte", frappe.PermissionError)

    # Obtener KPIs
    kpis = frappe.get_all(
        "Financial KPI",
        filters={"parent": report_name},
        fields=["metric", "value"],
        order_by="idx",
        ignore_permissions=True
    )

    # Generar HTML para el PDF
    html_content = generate_pdf_html(doc, kpis)

    # Generar PDF
    pdf_content = get_pdf(html_content, {"orientation": "Portrait"})

    # Guardar como archivo adjunto
    file_name = f"Reporte_Financiero_{doc.name}_{doc.periodo}.pdf"

    # Crear el archivo en Frappe
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": pdf_content,
        "is_private": 1,
        "attached_to_doctype": "Financial Report",
        "attached_to_name": doc.name
    })
    _file.save(ignore_permissions=True)

    return {"file_url": _file.file_url}


def generate_pdf_html(doc, kpis):
    """Genera el HTML para el PDF del reporte"""
    kpis_html = ""
    if kpis:
        kpis_html = "<h2>Indicadores Clave (KPIs)</h2><table style='width:100%; border-collapse: collapse;'><tr>"
        for kpi in kpis:
            kpis_html += f"""
            <td style='text-align: center; padding: 15px; border: 1px solid #ddd;'>
                <div style='color: #666; font-size: 12px;'>{kpi.metric}</div>
                <div style='font-size: 20px; font-weight: bold; color: #007bff;'>{kpi.value}</div>
            </td>
            """
        kpis_html += "</tr></table>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .info-item {{ display: inline-block; margin-right: 30px; }}
            .label {{ font-weight: bold; color: #666; }}
            .section {{ margin-bottom: 25px; padding: 15px; background: #fff; border: 1px solid #eee; border-radius: 5px; }}
            .dashboard-section {{ background: #f8f9fa; padding: 15px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h1>Reporte Financiero - {doc.name}</h1>

        <div class="info-box">
            <span class="info-item"><span class="label">Periodo:</span> {doc.periodo or '-'}</span>
            <span class="info-item"><span class="label">Tipo:</span> {doc.tipo_periodo or '-'}</span>
            <span class="info-item"><span class="label">Cliente:</span> {doc.cliente or '-'}</span>
        </div>

        {f'<div class="section"><h2>Resumen Ejecutivo</h2>{doc.summary}</div>' if doc.summary else ''}

        {kpis_html}

        {f'<div class="dashboard-section">{doc.dashboard_view}</div>' if doc.dashboard_view else ''}

        <div style="margin-top: 40px; text-align: center; color: #999; font-size: 11px;">
            <p>Generado automáticamente por Financial Bot</p>
        </div>
    </body>
    </html>
    """
    return html

