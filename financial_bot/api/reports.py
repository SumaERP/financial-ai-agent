import frappe
from frappe.utils.pdf import get_pdf

from financial_bot.utils.portal import get_customer_for_user


def _validate_report_access(report_name):
	"""Valida acceso al reporte. Retorna (customer, doc)."""
	if frappe.session.user == "Guest":
		frappe.throw("Debe iniciar sesión", frappe.PermissionError)

	customer = get_customer_for_user(frappe.session.user)
	if not customer:
		frappe.throw("No tiene acceso a reportes", frappe.PermissionError)

	doc = frappe.get_doc("Financial Report", report_name)
	if doc.cliente != customer:
		frappe.throw("No tiene permiso para este reporte", frappe.PermissionError)

	return customer, doc


@frappe.whitelist()
def get_chat_history(report_name):
	"""Obtiene el historial de chat de un reporte financiero"""
	_validate_report_access(report_name)

	return frappe.get_all(
		"Financial Chat Message",
		filters={"parent": report_name, "parenttype": "Financial Report"},
		fields=["role", "content"],
		order_by="idx asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def clear_chat_history(report_name):
	"""Limpia el historial del chat de un reporte"""
	_, doc = _validate_report_access(report_name)
	doc.chat_history = []
	doc.save(ignore_permissions=True)
	return {"success": True}


@frappe.whitelist()
def generate_pdf(report_name):
	"""Genera un PDF del reporte y lo adjunta al documento"""
	_, doc = _validate_report_access(report_name)

	kpis = frappe.get_all(
		"Financial KPI",
		filters={"parent": report_name},
		fields=["metric", "value"],
		order_by="idx",
		ignore_permissions=True,
	)

	pdf_content = get_pdf(_generate_pdf_html(doc, kpis), {"orientation": "Portrait"})
	file_name = f"Reporte_Financiero_{doc.name}_{doc.periodo}.pdf"

	_file = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"content": pdf_content,
		"is_private": 1,
		"attached_to_doctype": "Financial Report",
		"attached_to_name": doc.name,
	})
	_file.save(ignore_permissions=True)

	return {"file_url": _file.file_url}


@frappe.whitelist()
def regenerate_dashboard(doc_name):
	"""Regenera el dashboard HTML sin llamar a la IA"""
	from financial_bot.services.analysis import AnalysisService

	doc = frappe.get_doc("Financial Report", doc_name)
	if doc.estado != "Listo":
		frappe.throw("El documento debe estar en estado 'Listo'")

	analysis_data = {
		"period": doc.period or "",
		"summary": doc.summary or "",
		"kpis": [{"metric": r.metric, "value": r.value} for r in doc.kpis],
		"insights": [i.strip() for i in (doc.insights or "").split("\n") if i.strip()],
		"recommendations": [r.strip() for r in (doc.recomendations or "").split("\n") if r.strip()],
		"risks": [r.strip() for r in (doc.risks or "").split("\n") if r.strip()],
	}

	doc.dashboard_view = AnalysisService().generate_dashboard_html(analysis_data)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return True


def _generate_pdf_html(doc, kpis):
	"""HTML para PDF con iconos SVG (wkhtmltopdf no soporta emojis)"""
	icon_bulb = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d69e2e" stroke-width="2"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.9V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.1A7 7 0 0 0 12 2z"/></svg>'
	icon_rocket = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38a169" stroke-width="2"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/></svg>'
	icon_alert = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e53e3e" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'

	def list_to_html(text, icon, color):
		if not text or not text.strip():
			return ""
		return "".join(
			f'<div style="margin-bottom:10px;color:#4a5568;line-height:1.5;"><span style="color:{color};margin-right:8px;">{icon}</span>{item}</div>'
			for item in text.split("\n") if item.strip()
		)

	kpis_html = ""
	if kpis:
		cells = "".join(
			f'<td style="text-align:center;padding:15px;border:1px solid #e2e8f0;">'
			f'<div style="color:#718096;font-size:10px;text-transform:uppercase;">{k.metric}</div>'
			f'<div style="font-size:18px;font-weight:700;color:#2d3748;margin-top:5px;">{k.value}</div></td>'
			for k in kpis
		)
		kpis_html = f'<table style="width:100%;border-collapse:collapse;margin-bottom:25px;"><tr>{cells}</tr></table>'

	insights_html = list_to_html(doc.insights, icon_bulb, "#d69e2e")
	recs_html = list_to_html(doc.recomendations, icon_rocket, "#38a169")
	risks_html = list_to_html(doc.risks, icon_alert, "#e53e3e")

	return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body{{font-family:Arial,sans-serif;padding:20px;color:#333;font-size:12px;line-height:1.4;}}
h1{{color:#1a202c;border-bottom:3px solid #007bff;padding-bottom:10px;font-size:22px;}}
h2{{color:#2d3748;font-size:14px;margin:0 0 12px 0;}}
.card{{background:white;padding:15px;margin-bottom:15px;border-radius:8px;border:1px solid #e2e8f0;}}
</style></head><body>
<h1>Reporte Financiero - {doc.name}</h1>
<div style="background:#f7fafc;padding:15px;border-radius:5px;margin-bottom:20px;border:1px solid #e2e8f0;">
  <strong>Periodo:</strong> {doc.periodo or '-'} &nbsp;&nbsp;
  <strong>Tipo:</strong> {doc.tipo_periodo or '-'} &nbsp;&nbsp;
  <strong>Cliente:</strong> {doc.cliente or '-'}
</div>
{f'<div class="card"><h2>Resumen Ejecutivo</h2><p style="color:#4a5568;line-height:1.6;">{doc.summary}</p></div>' if doc.summary else ''}
{kpis_html}
{f'<div class="card" style="border-left:4px solid #ecc94b;"><h2 style="color:#744210;">Hallazgos Clave</h2>{insights_html}</div>' if insights_html else ''}
{f'<div class="card" style="border-left:4px solid #48bb78;"><h2 style="color:#22543d;">Recomendaciones</h2>{recs_html}</div>' if recs_html else ''}
{f'<div class="card" style="background:#fff5f5;border:1px solid #fed7d7;"><h2 style="color:#c53030;">Alertas de Riesgo</h2>{risks_html}</div>' if risks_html else ''}
<div style="margin-top:40px;text-align:center;color:#999;font-size:10px;border-top:1px solid #eee;padding-top:15px;">
  Generado automáticamente por Financial Bot
</div>
</body></html>"""
