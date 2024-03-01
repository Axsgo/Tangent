from odoo import fields, api, models
import xlwt
import base64
from io import BytesIO


class ResUsers(models.Model):
	_inherit = 'res.users'
	
	def _project_profit_manager_scheduler(self):
		user_ids = self.env['project.project'].search([]).mapped('user_id')
		for user in user_ids:
			project_ids = self.env['project.project'].search([('user_id','=',user.id)])
			if project_ids:
				workbook = xlwt.Workbook(encoding="UTF-8")
				format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
				format2 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
				format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
				format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
				format5 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
				format6 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
				sheet = workbook.add_sheet('Stage wise cost report')
				for r in range(20):
					sheet.col(r).width = int(20*260)
				i=0
				for project in project_ids:
					sheet.write_merge(i, i, 0, 7, project.name, format6)
					i+=1;k=i;l=3;x=i+1;y=3;tot_est=0;tot_amt=0
					sheet.write(k, 0, 'Stage', format1)
					sheet.write(k, 1, 'Est Amount', format1)
					sheet.write(k, 2, 'Total Amount', format1)
					k+=1
					timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',project.id)])
					employee_ids = self.env['hr.employee'].search([('id','in',timesheet_ids.mapped('employee_id').ids)],order='name asc')
					for line in project.stage_cost_ids:
						sheet.write(k, 0, line.stage_id.name, format2)
						sheet.write(k, 1, line.amount, format3)
						tot_est += line.amount
						k+=1
					for employee in employee_ids:
						sheet.write(i, l, employee.name, format4)
						l+=1
					for line in project.stage_cost_ids:
						z=y;tot=0
						for employee in employee_ids:
							time_id = self.env['account.analytic.line'].search([('project_id','=',project.id),('status_id','=',line.stage_id.id),('employee_id','=',employee.id)])    
							sheet.write(x, z, time_id.unit_amount*employee.timesheet_cost, format5)
							tot += time_id.unit_amount*employee.timesheet_cost
							z+=1
						tot_amt += tot
						sheet.write(x, 2, tot, format3)
						x+=1
					sheet.write(x, 1, tot_est, format3)
					sheet.write(x, 2, tot_amt, format3)
					i=x+2
				fp = BytesIO()
				workbook.save(fp)     
				report_id = self.env['ir.attachment'].create({'name': 'Project Profit Report','type': 'binary',
                    'datas': base64.encodestring(fp.getvalue()),'res_model': 'res.users','res_id': self.id})
				context = {
						'email_to':user.email,
						'email_from':self.env.company.erp_email,
					}
				template = self.env.ref('sttl_timesheet_calendar.email_template_project_profit')
				template.write({'attachment_ids': [(6,0,[report_id.id])]})
				template.with_context(context).send_mail(self.id, force_send=True)
				report_id.unlink()
				
	def _project_profit_admin_scheduler(self):
		group_id = self.env.ref('ax_groups.admin_user_group')
		for user in group_id.users:
			project_ids = self.env['project.project'].search([])
			workbook = xlwt.Workbook(encoding="UTF-8")
			format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
			format2 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
			format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
			format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
			format5 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
			format6 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
			sheet = workbook.add_sheet('Stage wise cost report')
			for r in range(20):
				sheet.col(r).width = int(20*260)
			i=0
			for project in project_ids:
				sheet.write_merge(i, i, 0, 7, project.name, format6)
				i+=1;k=i;l=3;x=i+1;y=3;tot_est=0;tot_amt=0
				sheet.write(k, 0, 'Stage', format1)
				sheet.write(k, 1, 'Est Amount', format1)
				sheet.write(k, 2, 'Total Amount', format1)
				k+=1
				timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',project.id)])
				employee_ids = self.env['hr.employee'].search([('id','in',timesheet_ids.mapped('employee_id').ids)],order='name asc')
				for line in project.stage_cost_ids:
					sheet.write(k, 0, line.stage_id.name, format2)
					sheet.write(k, 1, line.amount, format3)
					tot_est += line.amount
					k+=1
				for employee in employee_ids:
					sheet.write(i, l, employee.name, format4)
					l+=1
				for line in project.stage_cost_ids:
					z=y;tot=0
					for employee in employee_ids:
						time_id = self.env['account.analytic.line'].search([('project_id','=',project.id),('status_id','=',line.stage_id.id),('employee_id','=',employee.id)])    
						sheet.write(x, z, time_id.unit_amount*employee.timesheet_cost, format5)
						tot += time_id.unit_amount*employee.timesheet_cost
						z+=1
					tot_amt += tot
					sheet.write(x, 2, tot, format3)
					x+=1
				sheet.write(x, 1, tot_est, format3)
				sheet.write(x, 2, tot_amt, format3)
				i=x+2
			fp = BytesIO()
			workbook.save(fp)     
			report_id = self.env['ir.attachment'].create({'name': 'Project Profit Report','type': 'binary',
                'datas': base64.encodestring(fp.getvalue()),'res_model': 'res.users','res_id': self.id})
			context = {
					'email_to':user.email,
					'email_from':self.env.company.erp_email,
				}
			template = self.env.ref('sttl_timesheet_calendar.email_template_project_profit')
			template.write({'attachment_ids': [(6,0,[report_id.id])]})
			template.with_context(context).send_mail(self.id, force_send=True)
			report_id.unlink()
		