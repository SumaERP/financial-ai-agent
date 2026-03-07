#!/usr/bin/env python3
"""
Script para regenerar todos los dashboards de reportes financieros
Útil después de actualizar la función generate_dashboard_html
"""

import frappe
from financial_bot.services.analysis import regenerate_dashboard

def regenerate_all():
    """Regenera el dashboard HTML de todos los reportes en estado 'Listo'"""
    frappe.init(site='evidencia.localhost')
    frappe.connect()
    
    # Obtener todos los reportes en estado "Listo"
    reports = frappe.get_all(
        "Financial Report",
        filters={"estado": "Listo"},
        fields=["name", "cliente", "periodo"]
    )
    
    print(f"Encontrados {len(reports)} reportes para regenerar")
    
    success_count = 0
    error_count = 0
    
    for report in reports:
        try:
            print(f"Regenerando: {report.name} ({report.cliente} - {report.periodo})...", end=" ")
            regenerate_dashboard(report.name)
            success_count += 1
            print("✓")
        except Exception as e:
            error_count += 1
            print(f"✗ Error: {str(e)}")
    
    print(f"\n{'='*50}")
    print(f"Completado: {success_count} exitosos, {error_count} errores")
    print(f"{'='*50}")
    
    frappe.db.commit()
    frappe.destroy()

if __name__ == "__main__":
    regenerate_all()

