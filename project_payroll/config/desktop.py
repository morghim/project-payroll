from frappe import _

def get_data():
	return [
		{
			"module_name": "Project Payroll",
			"color": "grey",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("Project Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Projects Payroll",
					"description": _("Employee Projects Payroll master."),
					"onboard": 1,
				},
			]
		}
	]
