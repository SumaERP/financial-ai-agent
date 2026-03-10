import frappe


def after_install():
	"""Configuración inicial del app Financial Bot"""
	create_financial_bot_settings()


def create_financial_bot_settings():
	"""Financial AI Settings es Single DocType, Frappe lo crea automáticamente."""
	print("Financial Bot: Instalación completada.")
	print("Financial Bot: Configure la API Key en 'Financial AI Settings'.")
