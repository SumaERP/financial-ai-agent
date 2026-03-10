// Copyright (c) 2025, Quanta and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Report", {
	refresh(frm) {
		// Renderizar el dashboard HTML si existe contenido
		if (frm.doc.dashboard_view) {
			frm.fields_dict.dashboard_view.$wrapper.html(frm.doc.dashboard_view);
		}

		// Colorear el indicador de estado
		frm.trigger('actualizar_indicador_estado');

		// Botón principal: PROCESAR REPORTE
		// Solo mostrar si el estado es "Por Subir" o "Error" y hay archivo adjunto
		if ((frm.doc.estado === "Por Subir" || frm.doc.estado === "Error") && frm.doc.report_file) {
			frm.add_custom_button(__("Procesar Reporte"), function() {
				frappe.confirm(
					__("¿Está seguro de que desea iniciar el procesamiento del reporte?"),
					function() {
						frappe.call({
							method: "financial_bot.financial_bot.doctype.financial_report.financial_report.procesar_reporte",
							args: { doc_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Iniciando procesamiento..."),
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: __("El reporte está siendo procesado. Puede tomar algunos minutos."),
										indicator: "blue"
									});
									frm.reload_doc();
								}
							},
							error: function(r) {
								frappe.show_alert({
									message: __("Error al iniciar el procesamiento"),
									indicator: "red"
								});
							}
						});
					}
				);
			}).addClass("btn-primary");
		}

		// Mensaje informativo si falta el archivo
		if (frm.doc.estado === "Por Subir" && !frm.doc.report_file && !frm.is_new()) {
			frm.dashboard.set_headline_alert(
				__("Adjunte un archivo PDF para poder procesar el reporte"),
				"yellow"
			);
		}

		// Mensaje de procesamiento en curso
		if (frm.doc.estado === "Procesando") {
			frm.dashboard.set_headline_alert(
				__("El reporte está siendo procesado. Por favor espere..."),
				"blue"
			);
			// Auto-refresh cada 10 segundos mientras está procesando
			setTimeout(function() {
				if (frm.doc.estado === "Procesando") {
					frm.reload_doc();
				}
			}, 10000);
		}

		// Botón para regenerar dashboard desde datos existentes
		if (frm.doc.estado === "Listo" && !frm.doc.dashboard_view) {
			frm.add_custom_button(__("Regenerar Dashboard"), function() {
				frappe.call({
					method: "financial_bot.api.reports.regenerate_dashboard",
					args: { doc_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Regenerando dashboard..."),
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
							frappe.show_alert({
								message: __("Dashboard regenerado exitosamente"),
								indicator: "green"
							});
						}
					}
				});
			}, __("Acciones"));
		}

		// Deshabilitar campos de resultado cuando está procesando o es nuevo
		if (frm.doc.estado === "Procesando" || frm.is_new()) {
			frm.set_df_property('summary', 'read_only', 1);
			frm.set_df_property('kpis', 'read_only', 1);
			frm.set_df_property('dashboard_view', 'read_only', 1);
		}
	},

	actualizar_indicador_estado(frm) {
		// Agregar indicador visual del estado
		const estado = frm.doc.estado;
		const colores = {
			"Por Subir": "orange",
			"Procesando": "blue",
			"Listo": "green",
			"Error": "red"
		};

		if (estado && colores[estado]) {
			frm.page.set_indicator(__(estado), colores[estado]);
		}
	},

	tipo_periodo(frm) {
		// Limpiar el periodo cuando cambia el tipo
		if (frm.doc.periodo) {
			frm.set_value('periodo', '');
		}

		// Actualizar placeholder según el tipo
		if (frm.doc.tipo_periodo === "Mensual") {
			frm.fields_dict.periodo.set_description("Formato: YYYY-MM (ej: 2025-07)");
		} else if (frm.doc.tipo_periodo === "Anual") {
			frm.fields_dict.periodo.set_description("Formato: YYYY (ej: 2025)");
		}
	}
});
