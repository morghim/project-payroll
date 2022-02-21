import frappe
from frappe import _
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from frappe.utils import flt
from erpnext import get_company_currency


class PayrollEntryOverride(PayrollEntry):
    def get_salary_components_with_project(self, component_type):
        salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)
        if salary_slips:
            salary_components = frappe.db.sql(
                """
                select ssd.salary_component, ssd.amount, ssd.parentfield, ss.payroll_cost_center, ss.employee, ss.start_date, ss.end_date
                from `tabSalary Slip` ss, `tabSalary Detail` ssd
                where ss.name = ssd.parent and ssd.parentfield = '%s' and ss.name in (%s)
            """
                % (component_type, ", ".join(["%s"] * len(salary_slips))),
                tuple([d.name for d in salary_slips]),
                as_dict=True,
            )
            return self.set_employee_ammount_with_project_account_dimention(
                salary_components
            )

    def get_account(self, component_dict = None):
        if not self.is_project_payroll_:
            return super().get_account()
        account_dict = {}
        for key, amount in component_dict.items():
                account = self.get_salary_component_account(key[0])
                account_dict[(account, key[1], key[2])] = account_dict.get((account, key[1], key[2]), 0) + amount
        return account_dict

    def get_salary_component_total_with_project(self, component_type):
        salary_components = self.get_salary_components_with_project(component_type)
        if salary_components:
            component_dict = {}
            for item in salary_components:
                add_component_to_accrual_jv_entry = True
                if component_type == "earnings":
                    is_flexible_benefit, only_tax_impact = frappe.db.get_value(
                        "Salary Component",
                        item["salary_component"],
                        ["is_flexible_benefit", "only_tax_impact"],
                    )
                    if is_flexible_benefit == 1 and only_tax_impact == 1:
                        add_component_to_accrual_jv_entry = False
                if add_component_to_accrual_jv_entry:
                    if item.project:
                        cost_center = item.payroll_cost_center
                        if item.cost_center:
                            cost_center = item.cost_center
                        component_dict[
                            (
                                item.salary_component,
                                item.project,
                                cost_center,
                            )
                        ] = (
                            component_dict.get(
                                (
                                    item.salary_component,
                                    item.project,
                                    cost_center,
                                ),
                                0,
                            )
                            + flt(item.amount)
                        )

                    else:
                        component_dict[
                            (item.salary_component, item.payroll_cost_center)
                        ] = component_dict.get(
                            (item.salary_component, item.payroll_cost_center), 0
                        ) + flt(
                            item.amount
                        )

            account_details = self.get_account(component_dict=component_dict)
            return account_details

    def set_employee_ammount_with_project_account_dimention(self, salary_slips):
        salary_slips_with_project = []

        for i in salary_slips:
            projects = None
            employee_project = frappe.get_list(
                "Employee Projects Payroll",
                filters={
                    "docstatus": 1,
                    "employee": i["employee"],
                    "from_date": ["<=", i["start_date"]],
                    "to_date": [">=", i["end_date"]],
                },
                fields=["name"],
            )
            if employee_project:
                projects = frappe.get_list(
                    "Employee Project",
                    filters={"parent": employee_project[0]["name"]},
                    fields=["project", "cost_center", "percent_pay"],
                )
            if projects:
                amount = i["amount"]
                for p in projects:
                    sal_slip = i.copy()
                    sal_slip["amount"] = amount * (p["percent_pay"] / 100)
                    sal_slip["project"] = p["project"]
                    sal_slip["cost_center"] = p["cost_center"]
                    salary_slips_with_project.append(sal_slip)
            else:
                salary_slips_with_project.append(i)

        return salary_slips_with_project

    def make_accrual_jv_entry(self):
        if not self.is_project_payroll_:
            return super().make_accrual_jv_entry()
        self.check_permission("write")
        earnings = (
            self.get_salary_component_total_with_project(component_type="earnings")
            or {}
        )
        deductions = (
            self.get_salary_component_total_with_project(component_type="deductions")
            or {}
        )
        payroll_payable_account = self.payroll_payable_account
        jv_name = ""
        precision = frappe.get_precision(
            "Journal Entry Account", "debit_in_account_currency"
        )
        if earnings or deductions:
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.user_remark = _(
                "Accrual Journal Entry for salaries from {0} to {1}"
            ).format(self.start_date, self.end_date)
            journal_entry.company = self.company
            journal_entry.posting_date = self.posting_date
            accounting_dimensions = get_accounting_dimensions() or []

            accounts = []
            currencies = []
            payable_amount = 0
            multi_currency = 0
            company_currency = get_company_currency(self.company)

            # Earnings
            for acc_cc, amount in earnings.items():
                if len(acc_cc) == 2:
                    b = acc_cc + (None,)
                    acc_cc = b
                (
                    exchange_rate,
                    amt,
                ) = self.get_amount_and_exchange_rate_for_journal_entry(
                    acc_cc[0], amount, company_currency, currencies
                )
                payable_amount += flt(amount, precision)
                accounts.append(
                    self.update_accounting_dimensions(
                        {
                            "account": acc_cc[0],
                            "debit_in_account_currency": flt(amt, precision),
                            "exchange_rate": flt(exchange_rate),
                            "cost_center": acc_cc[2] or self.cost_center,
                            "project": acc_cc[1],
                        },
                        accounting_dimensions,
                    )
                )

            # Deductions
            for acc_cc, amount in deductions.items():
                if len(acc_cc) == 2:
                    b = acc_cc + (None,)
                    acc_cc = b

                (
                    exchange_rate,
                    amt,
                ) = self.get_amount_and_exchange_rate_for_journal_entry(
                    acc_cc[0], amount, company_currency, currencies
                )
                payable_amount -= flt(amount, precision)
                accounts.append(
                    self.update_accounting_dimensions(
                        {
                            "account": acc_cc[0],
                            "credit_in_account_currency": flt(amt, precision),
                            "exchange_rate": flt(exchange_rate),
                            "cost_center": acc_cc[2] or self.cost_center,
                            "project": acc_cc[1],
                        },
                        accounting_dimensions,
                    )
                )

            # Payable amount
            (
                exchange_rate,
                payable_amt,
            ) = self.get_amount_and_exchange_rate_for_journal_entry(
                payroll_payable_account, payable_amount, company_currency, currencies
            )
            accounts.append(
                self.update_accounting_dimensions(
                    {
                        "account": payroll_payable_account,
                        "credit_in_account_currency": flt(payable_amt, precision),
                        "exchange_rate": flt(exchange_rate),
                        "cost_center": self.cost_center,
                    },
                    accounting_dimensions,
                )
            )

            journal_entry.set("accounts", accounts)
            if len(currencies) > 1:
                multi_currency = 1
            journal_entry.multi_currency = multi_currency
            journal_entry.title = payroll_payable_account
            journal_entry.save()

        try:
            journal_entry.submit()
            jv_name = journal_entry.name
            self.update_salary_slip_status(jv_name=jv_name)
        except Exception as e:
            if type(e) in (str, list, tuple):
                frappe.msgprint(e)
            raise

        return jv_name
