import frappe
from financial_bot.utils.portal import get_customer_for_user

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Debe iniciar sesión para ver este reporte", frappe.PermissionError)

	report_name = frappe.form_dict.get("name")
	if not report_name:
		frappe.throw("No se especificó el reporte", frappe.DoesNotExistError)

	customer = get_customer_for_user(frappe.session.user)
	if not customer:
		frappe.throw("No tiene acceso a reportes", frappe.PermissionError)

	doc = frappe.get_doc("Financial Report", report_name)
	if doc.cliente != customer:
		frappe.throw("No tiene permiso para ver este reporte", frappe.PermissionError)

	context.doc = doc
	context.kpis = frappe.get_all(
		"Financial KPI",
		filters={"parent": report_name},
		fields=["metric", "value"],
		order_by="idx",
		ignore_permissions=True,
	)
	context.chat_history = frappe.get_all(
		"Financial Chat Message",
		filters={"parent": report_name, "parenttype": "Financial Report"},
		fields=["role", "content"],
		order_by="idx asc",
		ignore_permissions=True,
	)
	return context
