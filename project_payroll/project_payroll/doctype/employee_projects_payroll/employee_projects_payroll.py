# Copyright (c) 2021, Ibrahim Morghim and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _, throw


class EmployeeProjectsPayroll(Document):




    def validate_dates(self):
        employee_project = frappe.get_list("Employee Projects Payroll",filters={"docstatus": 1,"employee": self.employee,"from_date": ["<=", self.from_date],"to_date": [">=", self.to_date],},fields=["name"],)
        if employee_project:
            throw(_("there is overlaps with another Employee Projects Payroll"))



    def validate(self):
        self.validate_percent_pay()
        self.validate_project()
        self.validate_dates()

    def validate_percent_pay(self):
        percent = 0
        for i in self.employee_project:
            percent = percent + i.percent_pay
        if percent != 100:
            throw(_("precent pay for all project can not be more or less than 100 %"))

    def validate_project(self):
        projects = []
        for i in self.employee_project:
            if i.project in projects:
                throw(_("there is duplicate on project"))
            projects.append(i.project)



