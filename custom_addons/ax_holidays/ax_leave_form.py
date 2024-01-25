from odoo import api,fields,models
from datetime import datetime,time,timedelta
from pytz import UTC
from dateutil.rrule import rrule, DAILY

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
	