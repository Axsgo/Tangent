from odoo import fields,api,models,_
from datetime import datetime,time
from pytz import UTC
from dateutil.rrule import rrule, DAILY
from odoo.exceptions import UserError


class AxAttendancePermission(models.Model):
	_name = "hr.attendance.permission"
	_description = "Attendance Permission"
	_order = "id desc"

	@api.model
	def default_get(self, field_list):
		result = super(AxAttendancePermission, self).default_get(field_list)
		if not self.env.context.get('default_employee_id') and 'employee_id' in field_list:
			result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
		return result

	def _domain_employee_id(self):
		if not self.user_has_groups('hr.group_hr_manager'):
			return [('user_id', '=', self.env.user.id)]
		return []

	name = fields.Char('Name')
	employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id, required=True)
	date = fields.Date(string='Attendance Date', required=True, tracking=True)
	check_in = fields.Datetime("Check In", required=True)
	check_out = fields.Datetime("Check Out", required=True)
	comments = fields.Text('Comments')
	state = fields.Selection([('applied','Applied'),('approved','Approved'),('rejected','Rejected')],'State',default='applied')
	
	@api.onchange('check_in','check_out')
	def _onchange_check_in_out(self):
		self.date = self.check_in.date()
	
	@api.model_create_multi
	def create(self, vals_list):
		lines = super(AxAttendancePermission, self).create(vals_list)
		for res in lines:
			if res.check_in.date() != res.check_out.date():
				raise UserError(_("Check In and Check Out dates should be the same"))
			if self.env['hr.leave'].search([('employee_id','=',res.employee_id.id),('request_date_from','<=',res.date),('request_date_to','>=',res.date)]):
				raise UserError(_("As of this date, you have already applied for the leave"))
			res.name = res.employee_id.name
		return lines
	
	def write(self, vals):
		rec = super(AxAttendancePermission, self).write(vals)
		if self.check_in.date() != self.check_out.date():
			raise UserError(_("Check In and Check Out dates should be the same"))
		if self.env['hr.leave'].search([('employee_id','=',self.employee_id.id),('request_date_from','<=',self.date),('request_date_to','>=',self.date)]):
			raise UserError(_("As of this date, you have already applied for the leave"))
		return rec
	
	def entry_approve(self):
		if self.env.user.id == self.employee_id.user_id.id:
			raise UserError(_('Only your manager can approve your request.'))
		attendance_id = self.env['hr.attendance'].search([('employee_id','=',self.employee_id.id),('fetch_date','=',self.date)])
		if attendance_id:
			if attendance_id.check_in > self.check_in:
				attendance_id.check_in = self.check_in
			if attendance_id.check_out < self.check_out:
				attendance_id.check_out = self.check_out
			check_in_id = self.env['hr.attendance.line'].search([('header_id','=',attendance_id.id),('check_in','<=',self.check_in),('check_out','>=',self.check_in)])
			check_out_id = self.env['hr.attendance.line'].search([('header_id','=',attendance_id.id),('check_in','<=',self.check_out),('check_out','>=',self.check_out)])
			check_in1_id = self.env['hr.attendance.line'].search([('header_id','=',attendance_id.id),('check_in','>=',self.check_in),('check_out','<=',self.check_out)])
			if check_in_id or check_out_id or check_in1_id:
				raise UserError(_('There was already a check-in or check-out log at this time'))
			attendance_id.line_ids = [(0,0,{'check_in':self.check_in,'check_out':self.check_out,'is_permission':True})]
			self.state = 'approved'
		else:
			raise UserError(_('As your attendance log is not during this date, you cannot apply'))
		
	def entry_cancel(self):
		self.state = 'rejected'
		
	def unlink(self):
		for line in self:
			if line.state == 'approved':
				raise UserError(_('Once the permission is approved, you cannot delete it.'))
		return super(AxAttendancePermission, self).unlink()

	@api.model
	def get_unusual_days(self, check_in, check_out=None):
		# Checking the calendar directly allows to not grey out the leaves taken
		# by the employee
		calendar = self.env.user.employee_id.resource_calendar_id
		if not calendar:
			return {}
		dfrom = datetime.combine(fields.Date.from_string(check_in), time.min).replace(tzinfo=UTC)
		dto = datetime.combine(fields.Date.from_string(check_out), time.max).replace(tzinfo=UTC)

		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
	