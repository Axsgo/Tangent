from odoo import api,fields,models,_
from datetime import date,datetime,time,timedelta
from pytz import UTC
from dateutil.rrule import rrule, DAILY
from odoo.exceptions import UserError
from dateutil import parser


class AxLeave(models.Model):
	_name = "ax.leave"
	_description = "Employee Leave Form"
	_order = "id desc"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	from_date = fields.Date("From Date",default=fields.Date.today,tracking=True)
	to_date = fields.Date("To Date",default=fields.Date.today,tracking=True)
	employee_id = fields.Many2one("hr.employee",'Employee',tracking=True,required=True)
	holiday_status_id = fields.Many2one("hr.leave.type",'Time Off Type',tracking=True)
	number_of_days = fields.Float("Duration",compute='_get_number_of_days',store=True,tracking=True)
	name = fields.Char("Description",related='employee_id.name',store=True,tracking=True)
	description = fields.Char("Reason",tracking=True,required=True)
	user_id = fields.Many2one("res.users",'Created By',default=lambda self:self.env.user.id)
	company_id = fields.Many2one("res.company",'Company',default=lambda self:self.env.company.id)
	entry_date = fields.Date("Entry Date",default=fields.Date.today)
	state = fields.Selection([('draft','Draft'),('confirm','Apply'),('cancel','Cancalled')],default='draft',string="Status",tracking=True)

	@api.depends('from_date','to_date')
	def _get_number_of_days(self):
		for rec in self:
			if self.from_date and self.to_date:
				day_diff = ((self.to_date-self.from_date).days)+1
				rec.number_of_days = day_diff

	def entry_confirm(self):
		if self.state == 'draft':
			self.write({
				'state':'confirm'
			})

	@api.model
	def get_unusual_days(self, from_date, to_date=None):
		# Checking the calendar directly allows to not grey out the leaves taken
		# by the employee
		calendar = self.env.user.employee_id.resource_calendar_id
		if not calendar:
			return {}
		dfrom = datetime.combine(fields.Date.from_string(from_date), time.min).replace(tzinfo=UTC)
		dto = datetime.combine(fields.Date.from_string(to_date), time.max).replace(tzinfo=UTC)

		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
	
	
class CalendarLeaves(models.Model):
	_inherit = "resource.calendar.leaves"
	
	date_from = fields.Datetime('Start Date', required=True, default=datetime.now().replace(hour=0, minute=0, second=0) - timedelta(hours=5.5))
	date_to = fields.Datetime('End Date', required=True, default=datetime.now().replace(hour=23, minute=59, second=59) - timedelta(hours=5.5))


class HrLeave(models.Model):
	_inherit = "hr.leave"
	
	message = fields.Text('Message')
	
	@api.onchange('holiday_status_id')
	def _onchange_holiday_status_id(self):
		leave_ids = self.env['hr.leave'].search([('employee_id','=',self.employee_id.id),('holiday_status_id.code','=','SL'),('state','not in',('cancel','refuse'))])
		leave_count = 0
		if self.holiday_status_id.code == 'SL':
			for leave in leave_ids:
				leave_days = leave.get_unusual_days(leave.request_date_from,leave.request_date_to)
				leave_count += list(leave_days.values()).count(False)
			if leave_count > self.holiday_status_id.leave_limit:
				self.message = (("Alreday you applied %s days sick leaves")%leave_count)
			else:
				self.message = False
		else:
			self.message = False
	
	@api.model
	def create(self, vals):
		type_id = self.env['hr.leave.type'].search([('id','=',vals.get('holiday_status_id'))])
		if type_id.future_days == True:
			if parser.parse(vals.get('request_date_from')).date()>date.today() or parser.parse(vals.get('request_date_to')).date()>date.today():
				raise UserError(_("You can't apply leave for future date"))
		return super(HrLeave, self).create(vals)
	
	
class HrLeaveType(models.Model):
	_inherit = "hr.leave.type"
	
	leave_limit = fields.Integer('Leave warning Limit')
	future_days = fields.Boolean('Restrict future dates')
	
	