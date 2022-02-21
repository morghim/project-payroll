// Copyright (c) 2021, Ibrahim Morghim and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Projects Payroll', {
	refresh: function(frm) {
		frm.set_query("cost_center", "employee_project", function() {
			
			return {
				"filters": {
					"is_group": "0",
				}
			};
		});
	}
});
