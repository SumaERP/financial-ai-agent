import frappe
from financial_bot.utils.portal import get_customer_for_user

no_cache = 1


def get_context(context):
	"""Obtiene los reportes financieros asignados al cliente logueado"""
	if frappe.session.user == "Guest":
		frappe.throw("Debe iniciar sesión para ver sus reportes", frappe.PermissionError)

	customer = get_customer_for_user(frappe.session.user)
	reportes = []

	if customer:
		reportes = frappe.get_all(
			"Financial Report",
			filters={"cliente": customer},
			fields=["name", "periodo", "tipo_periodo", "estado", "creation"],
			order_by="creation desc",
			ignore_permissions=True,
		)

	context.reportes = reportes
	context.show_sidebar = True
	return context
