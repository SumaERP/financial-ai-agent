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
    """Genera el HTML para el PDF del reporte con iconos SVG y formato mejorado"""

    # Iconos SVG que funcionan en PDF (wkhtmltopdf no soporta emojis)
    icon_bulb = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d69e2e" stroke-width="2"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.9V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.1A7 7 0 0 0 12 2z"/></svg>'
    icon_rocket = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38a169" stroke-width="2"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>'
    icon_alert = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e53e3e" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'

    # KPIs en formato tabla para PDF
    kpis_html = ""
    if kpis:
        kpis_html = """
        <div style="margin-bottom: 25px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
        """
        for kpi in kpis:
            kpis_html += f"""
                <td style="text-align: center; padding: 15px; border: 1px solid #e2e8f0; background: white;">
                    <div style="color: #718096; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">{kpi.metric}</div>
                    <div style="font-size: 18px; font-weight: 700; color: #2d3748; margin-top: 5px;">{kpi.value}</div>
                </td>
            """
        kpis_html += "</tr></table></div>"

    # Generar listas con iconos SVG
    def list_to_html_with_icons(items_str, icon, color):
        if not items_str or not items_str.strip():
            return ""
        # Dividir por saltos de línea y filtrar vacíos
        items = [item.strip() for item in items_str.split("\n") if item.strip()]
        html = ""
        for item in items:
            html += f'<div style="margin-bottom: 10px; color: #4a5568; line-height: 1.5;"><span style="color: {color}; margin-right: 8px; vertical-align: middle; display: inline-block;">{icon}</span>{item}</div>'
        return html

    insights_html = list_to_html_with_icons(doc.insights if hasattr(doc, 'insights') else "", icon_bulb, "#d69e2e")
    recs_html = list_to_html_with_icons(doc.recomendations if hasattr(doc, 'recomendations') else "", icon_rocket, "#38a169")
    risks_html = list_to_html_with_icons(doc.risks if hasattr(doc, 'risks') else "", icon_alert, "#e53e3e")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, Helvetica, sans-serif;
                padding: 20px;
                color: #333;
                font-size: 12px;
                line-height: 1.4;
            }}
            h1 {{
                color: #1a202c;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
                font-size: 22px;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #2d3748;
                font-size: 14px;
                margin-top: 0;
                margin-bottom: 12px;
            }}
            .info-box {{
                background: #f7fafc;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #e2e8f0;
            }}
            .info-item {{
                display: inline-block;
                margin-right: 30px;
            }}
            .label {{
                font-weight: bold;
                color: #718096;
            }}
            .section-card {{
                background: white;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }}
            .insights-section {{
                border-left: 4px solid #ecc94b;
            }}
            .insights-section h2 {{
                color: #744210;
            }}
            .recs-section {{
                border-left: 4px solid #48bb78;
            }}
            .recs-section h2 {{
                color: #22543d;
            }}
            .risks-section {{
                background: #fff5f5;
                border: 1px solid #fed7d7;
                border-left: 4px solid #e53e3e;
            }}
            .risks-section h2 {{
                color: #c53030;
            }}
            .summary-section {{
                background: #f7fafc;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .summary-section p {{
                color: #4a5568;
                line-height: 1.6;
                margin: 8px 0 0 0;
            }}
        </style>
    </head>
    <body>
        <h1>Reporte Financiero - {doc.name}</h1>

        <div class="info-box">
            <span class="info-item"><span class="label">Periodo:</span> {doc.periodo or '-'}</span>
            <span class="info-item"><span class="label">Tipo:</span> {doc.tipo_periodo or '-'}</span>
            <span class="info-item"><span class="label">Cliente:</span> {doc.cliente or '-'}</span>
        </div>

        {f'<div class="summary-section"><h2>Resumen Ejecutivo</h2><p>{doc.summary}</p></div>' if doc.summary else ''}

        {kpis_html}

        {f'<div class="section-card insights-section"><h2>Hallazgos Clave</h2>{insights_html}</div>' if insights_html else ''}

        {f'<div class="section-card recs-section"><h2>Recomendaciones</h2>{recs_html}</div>' if recs_html else ''}

        {f'<div class="section-card risks-section"><h2>Alertas de Riesgo</h2>{risks_html}</div>' if risks_html else ''}

        <div style="margin-top: 40px; text-align: center; color: #999; font-size: 10px; border-top: 1px solid #eee; padding-top: 15px;">
            <p>Generado automáticamente por Financial Bot</p>
        </div>
    </body>
    </html>
    """
    return html

