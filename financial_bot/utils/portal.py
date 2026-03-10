import frappe


def get_customer_for_user(user):
	"""Obtiene el Customer vinculado al usuario via tabPortal User del Customer"""
	return frappe.db.get_value(
		"Portal User",
		{"user": user, "parenttype": "Customer"},
		"parent",
	)


def get_portal_users_for_customer(customer):
	"""Obtiene los usuarios del portal vinculados a un Customer via Contact"""
	contacts = frappe.db.sql(
		"""
		SELECT DISTINCT c.user
		FROM `tabContact` c
		INNER JOIN `tabDynamic Link` dl ON dl.parent = c.name AND dl.parenttype = 'Contact'
		WHERE dl.link_doctype = 'Customer'
		AND dl.link_name = %s
		AND c.user IS NOT NULL
		AND c.user != ''
	""",
		(customer,),
		as_dict=True,
	)

	return [c.user for c in contacts]
