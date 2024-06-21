from odoo import fields,api,models
import xlwt,base64
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class IndividualTimesheet(models.TransientModel):
	_name = "hr.individual.timesheet.report"
	_description = "Individual Timesheet Report"

	report_type = fields.Selection([('employee','Employee Wise'),('project','Project Wise')],string="Report Type",default='employee')
	employee_id = fields.Many2one("hr.employee","Employee")
	project_id = fields.Many2one('project.project','Project')
	from_date = fields.Date("From Date")
	to_date = fields.Date("To Date")
	project_id = fields.Many2one("project.project","Project")
	file_name = fields.Binary('Report', readonly=True)
	report = fields.Char('Name')

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int(round((float_value - hours) * 60))
		return f"{hours:02d}:{minutes:02d}"

	def generate_excel(self):
		from datetime import datetime
		custom_value={}    
		workbook = xlwt.Workbook()
		date_format = xlwt.XFStyle()
		date_format.num_format_str = 'D/MMM/YYYY'
		borders = xlwt.Borders()
		borders.left = 1
		borders.right = 1
		borders.top = 1
		borders.bottom = 1
		date_format.borders = borders
		style0 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom dotted, right thin,left thin;align: horiz center;', num_format_str='#,###,##0.00')
		style1 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom double, right thin,left thin;align: horiz center, wrap 1', num_format_str='DD/MMM/YYYY')
		style2 = xlwt.easyxf('font:height 400,bold True,colour black; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='#,###,##0.00')         
		style3 = xlwt.easyxf('font:height 400,bold True,colour black; borders: top thin,bottom thin, right thin,left thin;align: horiz center;', num_format_str='DD/MMM/YYYY')
		style4 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='DD/MMM/YYYY')
		style5 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		style6 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='#,###,##0')
		style7 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz center;', num_format_str='_(###0.00_);[Red](###0.00)')
		style9 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz center;')
		style8 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		style10 = xlwt.easyxf('font: name Times New Roman,bold True, colour white;borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		pattern = xlwt.Pattern()
		pattern.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern.pattern_fore_colour = 0x34
		style1.pattern = pattern
		pattern1 = xlwt.Pattern()
		pattern1.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern1.pattern_fore_colour = xlwt.Style.colour_map['pale_blue']
		style8.pattern = pattern1
		pattern2 = xlwt.Pattern()
		pattern2.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern2.pattern_fore_colour = xlwt.Style.colour_map['black']
		style10.pattern = pattern2
		# style = xlwt.XFStyle()
		style1.alignment.wrap = 1
		day_diff = (self.to_date-self.from_date).days+1
		date_list = []
		current_date = self.from_date
		while current_date <= self.to_date:
			date_list.append(current_date.strftime("%d/%m/%Y"))
			current_date += timedelta(days=1)
		if self.report_type == 'employee': 
			timesheet = project_ids = []
			sheet = workbook.add_sheet('%s - Timesheet Report'%(self.employee_id.name))
			timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',self.employee_id.id),
				('date','>=',self.from_date),('date','<=',self.to_date)])
			if timesheet_ids:
				project_ids = timesheet_ids.mapped('project_id')
			else:
				raise UserError("Warning!!, No record found!")

			sheet.row(0).height = 500
			sheet.write_merge(0, 0, 0, 9, 'PROJECT TIMESHEET REPORT',style2)
			sheet.write(1,0,"Name",style1)
			sheet.write(1,1,self.employee_id.name,style4)
			sheet.write(2,0,"From Date",style1)
			sheet.write(2,1,self.from_date,style4)
			sheet.write(3,0,"To Date",style1)
			sheet.write(3,1,self.to_date,style4)
			
			sheet.write(5,0,"S.No",style1)
			sheet.write(5,1,"Project No",style1)
			sheet.write(5,2,"Project Name",style1)
			n = 3
			for day in date_list:
				sheet.write(5,n,day,style1)
				n += 1
			sheet.write(5,n,'Total',style1)
			i = 1; m = 6
			for rec in project_ids:
				sheet.write(m, 0, i, style9)
				sheet.write(m, 1, rec.project_no, style7)
				sheet.write(m, 2, rec.name, style4)
				startdate = self.from_date
				j=1;h=3;p_tot = 0
				while j <= day_diff:
					timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',self.employee_id.id),
						('date','>=',startdate),('date','<=',startdate),('project_id','=',rec.id)])
					sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style7)
					startdate = startdate + timedelta(days=1)
					p_tot += sum([x.unit_amount for x in timesheet_ids])
					j += 1
					h += 1
				sheet.write(m, h, self.float_to_time(p_tot), style8)
				i += 1
				m += 1
			sheet.write_merge(m,m,0,2,"Total",style1)
			j = 1;h=3
			startdate = self.from_date
			while j <= day_diff:
				timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',self.employee_id.id),
					('date','>=',startdate),('date','<=',startdate)])
				sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style8)
				startdate = startdate + timedelta(days=1)
				j+=1
				h+=1
			timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',self.employee_id.id),
					('date','>=',self.from_date),('date','<=',self.to_date)])
			sheet.write(m,h,self.float_to_time(sum([x.unit_amount for x in timesheet_ids])),style10)
			filename = ('%s Individual Timesheet Report (%s - %s)'%(self.employee_id.name,self.from_date.strftime("%d-%m-%Y"),self.to_date.strftime("%d-%m-%Y"))+'.xls')
		else:
			timesheet = employee_ids = []
			sheet = workbook.add_sheet('%s - Timesheet Report'%(self.project_id.name))
			timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
				('date','>=',self.from_date),('date','<=',self.to_date)])
			if timesheet_ids:
				employee_ids = timesheet_ids.mapped('employee_id')
			else:
				raise UserError("Warning!!, No record found!")

			sheet.row(0).height = 500
			sheet.write_merge(0, 0, 0, 9, 'PROJECT TIMESHEET REPORT',style2)
			sheet.write(1,0,"No",style1)
			sheet.write(1,1,self.project_id.project_no,style4)
			sheet.write(1,2,"Name",style1)
			sheet.write(1,3,self.project_id.name,style4)
			sheet.write(2,0,"From Date",style1)
			sheet.write(2,1,self.from_date,style4)
			sheet.write(3,0,"To Date",style1)
			sheet.write(3,1,self.to_date,style4)
			
			sheet.write(5,0,"S.No",style1)
			sheet.write(5,1,"Employee",style1)
			n = 2
			for day in date_list:
				sheet.write(5,n,day,style1)
				n += 1
			sheet.write(5,n,'Total',style1)
			i = 1; m = 6
			for rec in employee_ids:
				sheet.write(m, 0, i, style9)
				sheet.write(m, 1, rec.name, style4)
				startdate = self.from_date
				j=1;h=2;p_tot = 0
				while j <= day_diff:
					timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
						('date','>=',startdate),('date','<=',startdate),('employee_id','=',rec.id)])
					sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style7)
					startdate = startdate + timedelta(days=1)
					p_tot += sum([x.unit_amount for x in timesheet_ids])
					j += 1
					h += 1
				sheet.write(m, h, self.float_to_time(p_tot), style8)
				i += 1
				m += 1
			sheet.write_merge(m,m,0,1,"Total",style1)
			j = 1;h=2
			startdate = self.from_date
			while j <= day_diff:
				timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
					('date','>=',startdate),('date','<=',startdate)])
				sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style8)
				startdate = startdate + timedelta(days=1)
				j+=1
				h+=1
			timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
					('date','>=',self.from_date),('date','<=',self.to_date)])
			sheet.write(m,h,self.float_to_time(sum([x.unit_amount for x in timesheet_ids])),style10)
			filename = ('%s-%s Timesheet Report (%s - %s)'%(self.project_id.project_no,self.project_id.name,self.from_date.strftime("%d-%m-%Y"),self.to_date.strftime("%d-%m-%Y"))+'.xls')
		filename_tmp = '/tmp/' + filename
		workbook.save(filename_tmp)
		fp = open(filename_tmp, "rb")
		file_data = fp.read()
		out = base64.encodestring(file_data)  
		self.write({'report':filename, 'file_name':out})
		fp.close()
		
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'hr.individual.timesheet.report',
			'res_id': self.id,
			'view_type': 'form',
			'view_mode': 'form',
			'context': self.env.context,
			'target': 'new',
		}