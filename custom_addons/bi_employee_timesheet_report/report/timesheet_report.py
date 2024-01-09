# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, _

class timesheet_report(models.AbstractModel):
    _name = 'report.bi_employee_timesheet_report.timesheet_select_report'
    _description = 'timesheet report'

    def get_timesheets_list(self, docs):

        if docs.start_date and docs.end_date:

            record= self.env['account.analytic.line'].search([('employee_id', 'in', docs.employee_ids.ids),('date', '>=', docs.start_date),('date', '<=', docs.end_date)])

        else:
            record = self.env['account.analytic.line'].search(
                [('employee_id', 'in', docs.employee_ids.ids)])

        records = []

        grouped_records = {}
        for rec in record:
            employee_id = rec['employee_id']
            if employee_id in grouped_records:
                grouped_records[employee_id].append(rec)
            else:
                grouped_records[employee_id] = [rec]

        for employee_id, employee_records in grouped_records.items():
            total = 0
            blank = 0
            if employee_id.id in docs.employee_ids.ids:
                blank += int(1)

                for rec in employee_records:
                    total += rec.unit_amount

                    vals = {
                        'project': rec.project_id.name,
                        'user': rec.employee_id.name,
                        'u_name':blank,
                        'duration': rec.unit_amount,
                        'date': rec.date,
                        'description': rec.name,
                        'task':rec.task_id.name,
                        'total':total,
                    }
                    records.append(vals)
            else:
                blank = 0
                for rec in employee_records:
                    total += rec.unit_amount

                    vals = {
                        'project': rec.project_id.name,
                        'user': rec.employee_id.name,
                        'u_name': blank,
                        'duration': rec.unit_amount,
                        'date': rec.date,
                        'description': rec.name,
                        'task': rec.task_id.name,
                        'total': total,
                    }
                    records.append(vals)
        return [records]


    @api.model
    def _get_report_values(self, docids, data=None):

        docs = self.env['timesheet.select'].browse(
            self.env.context.get('active_id'))
        store_list = []
        for rec in self.env['hr.employee'].search(
                [('name', 'in', [i.name for i in docs.employee_ids])]):
            if rec:
                store_list.append({'id': rec.id, 'name': rec.name})
        timesheets = self.get_timesheets_list(docs)

        time_gap = None
        if docs.start_date and docs.end_date:
            time_gap = "From " + str(docs.start_date) + " To " + str(docs.end_date)

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'timesheets': timesheets[0],
            'store_list': store_list,
            'time_gap': time_gap,
        }