from odoo import api,fields,models,_
from datetime import date,datetime,time,timedelta
from pytz import UTC
from dateutil.rrule import rrule, DAILY
from odoo.exceptions import UserError, ValidationError
from dateutil import parser
import math
from collections import namedtuple
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')


class AxLeave(models.Model):
	_name = "ax.leave"
	_description = "Employee Leave Form"
	_order = "id desc"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	
	from_date = fields.Date("First day of leave",default=fields.Date.today,tracking=True)
	to_date = fields.Date("Last day of leave",default=fields.Date.today,tracking=True)
	date_from = fields.Datetime('Start Date', readonly=False)
	date_to = fields.Datetime('End Date', readonly=False)
	request_date_from_period = fields.Selection([('am','Morning'),('pm','Afternoon')],default="am",string="Period")
	request_unit_half = fields.Boolean("Half Day",copy=False)
	employee_id = fields.Many2one("hr.employee",'Employee',tracking=True,required=True)
	holiday_status_id = fields.Many2one("hr.leave.type",'Time Off Type',tracking=True)
	number_of_days = fields.Float("Duration",compute='_get_number_of_days',store=True,tracking=True)
	name = fields.Char("Description",related='employee_id.name',store=True,tracking=True)
	description = fields.Char("Reason",tracking=True,required=True)
	user_id = fields.Many2one("res.users",'Created By',default=lambda self:self.env.user.id)
	company_id = fields.Many2one("res.company",'Company',default=lambda self:self.env.company.id)
	entry_date = fields.Date("Entry Date",default=fields.Date.today)
	is_leave_applied = fields.Boolean("Is Leave Applied?")
	state = fields.Selection([('draft','Draft'),('confirm','Apply'),('cancel','Cancalled')],default='draft',string="Status",tracking=True)

	@api.depends('from_date','to_date','request_unit_half')
	def _get_number_of_days(self):
		for rec in self:
			if rec.request_unit_half == True:
				if rec.from_date:
					rec.number_of_days = 12
			else:
				if rec.from_date and rec.to_date:
					day_diff = ((rec.to_date-rec.from_date).days)+1
					rec.number_of_days = day_diff
				
	def entry_confirm(self):
		self.write({'state':'confirm'})
		if self.from_date and self.to_date and self.from_date > self.to_date:
			self.to_date = self.from_date
		if not self.from_date:
			self.date_from = False
		elif not self.request_unit_half and not self.to_date:
			self.date_to = False
		else:
			if self.request_unit_half:
				self.to_date = self.from_date
			resource_calendar_id = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
			domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
			attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'], ['week_type', 'dayofweek', 'day_period'], lazy=False)
			# Must be sorted by dayofweek ASC and day_period DESC
			attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))
			default_value = DummyAttendance(0, 0, 0, 'morning', False)
		
			if resource_calendar_id.two_weeks_calendar:
				# find week type of start_date
				start_week_type = int(math.floor((self.from_date.toordinal() - 1) / 7) % 2)
				attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == start_week_type]
				attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != start_week_type]
				# First, add days of actual week coming after date_from
				attendance_filtred = [att for att in attendance_actual_week if int(att.dayofweek) >= self.from_date.weekday()]
				# Second, add days of the other type of week
				attendance_filtred += list(attendance_actual_next_week)
				# Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
				attendance_filtred += list(attendance_actual_week)
		
				end_week_type = int(math.floor((self.to_date.toordinal() - 1) / 7) % 2)
				attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == end_week_type]
				attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != end_week_type]
				attendance_filtred_reversed = list(reversed([att for att in attendance_actual_week if int(att.dayofweek) <= self.to_date.weekday()]))
				attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
				attendance_filtred_reversed += list(reversed(attendance_actual_week))
		
				# find first attendance coming after first_day
				attendance_from = attendance_filtred[0]
				# find last attendance coming before last_day
				attendance_to = attendance_filtred_reversed[0]
			else:
				# find first attendance coming after first_day
				attendance_from = next((att for att in attendances if int(att.dayofweek) >= self.from_date.weekday()), attendances[0] if attendances else default_value)
				# find last attendance coming before last_day
				attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= self.to_date.weekday()), attendances[-1] if attendances else default_value)
				
			compensated_from_date = self.from_date
			compensated_to_date = self.to_date
			
			if self.request_unit_half:
				if self.request_date_from_period == 'am':
					hour_from = float_to_time(attendance_from.hour_from)
					hour_to = float_to_time(attendance_from.hour_to)
				else:
					hour_from = float_to_time(attendance_to.hour_from)
					hour_to = float_to_time(attendance_to.hour_to)
			else:
				hour_from = float_to_time(attendance_from.hour_from)
				hour_to = float_to_time(attendance_to.hour_to)
			self.date_from = timezone(self.employee_id.resource_calendar_id.tz).localize(datetime.combine(compensated_from_date, hour_from)).astimezone(UTC).replace(tzinfo=None)
			self.date_to = timezone(self.employee_id.resource_calendar_id.tz).localize(datetime.combine(compensated_to_date, hour_to)).astimezone(UTC).replace(tzinfo=None)
			
	@api.constrains('from_date', 'to_date', 'employee_id')
	def _check_date(self):
			nholidays = self.search_count([('from_date', '<=', self.from_date),('to_date', '>=', self.to_date),
			    			('employee_id', '=', self.employee_id.id),('id', '!=', self.id)])
			if nholidays:
				raise ValidationError(_('You can not set 2 time off that overlaps on the same day for the same employee.'))

	def set_draft(self):
		self.write({'state':'draft'})

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

	def _entry_employee_absent_alert(self):
		absent_ids = self.env['ax.leave'].search([('from_date','<=',datetime.now().date()),('state','=','confirm'),
			('is_leave_applied','=',False)])
		for leave in absent_ids:
			leave_id = self.env['hr.leave'].search([('employee_id','=',leave.employee_id.id),
				('request_date_from','=',leave.from_date)])
			if leave_id:
				leave.is_leave_applied = True
			else:
				if (datetime.now().date() - leave.from_date).days >=2:
					context = {
						'email_to':leave.employee_id.user_id.email,
						'email_from':self.env.company.erp_email,
						'subject': "System Notification: Request to apply Leave on %s"%(leave.from_date.strftime("%d/%m/%Y")),
					}
					template = self.env['ir.model.data'].get_object('ax_holidays','email_template_absent_alert')
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(leave.id,force_send=True)
	
	def _employee_is_leave_applied_update(self):
		absent_ids = self.env['ax.leave'].search([('state','=','confirm'),('is_leave_applied','=',False)])
		for leave in absent_ids:
			leave_id = self.env['hr.leave'].search([('employee_id','=',leave.employee_id.id),('request_date_from','=',leave.from_date)])
			if leave_id:
				leave.is_leave_applied = True
				
	
class CalendarLeaves(models.Model):
	_inherit = "resource.calendar.leaves"
	
	date_from = fields.Datetime('Start Date', required=True, default=datetime.now().replace(hour=0, minute=0, second=0) - timedelta(hours=5.5))
	date_to = fields.Datetime('End Date', required=True, default=datetime.now().replace(hour=23, minute=59, second=59) - timedelta(hours=5.5))


class HrLeave(models.Model):
	_inherit = "hr.leave"
	
	message = fields.Text('Message')
	dr_certificate = fields.Binary("Medical Certificate")
	type_code = fields.Char("Code", related="holiday_status_id.code")
	
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
		if type_id.code == 'SL' and not vals.get('dr_certificate'):
			days = parser.parse(vals.get('request_date_to')).date() - parser.parse(vals.get('request_date_from')).date()
			if days.days > 0 or parser.parse(vals.get('request_date_from')).strftime('%A') in ('Monday','Friday') or parser.parse(vals.get('request_date_to')).strftime('%A') in ('Monday','Friday'):
				raise UserError(_("Kindly attach the Medical Certificate, then submit the leave request."))
		rec = super(HrLeave, self).create(vals)
		if vals.get('state')=='confirm':
			context = {
				'email_to':rec.employee_id.parent_id.work_email,
				'email_from':rec.env.company.erp_email,
				'subject': "System Notification: Request to approve Leave",
				}
			template = self.env['ir.model.data'].get_object('ax_holidays','email_template_approve_alert')
			self.env['mail.template'].browse(template.id).with_context(context).send_mail(rec.id,force_send=True)
		return rec
	
	def write(self, vals):
		res = super(HrLeave, self).write(vals)
		if vals.get('request_date_from') or vals.get('request_date_to'):
			if self.holiday_status_id.code == 'SL' and not self.dr_certificate:
				days = self.request_date_to - self.request_date_from
				if days.days > 0 or self.request_date_from.strftime('%A') in ('Monday','Friday') or self.request_date_to.strftime('%A') in ('Monday','Friday'):
					raise UserError(_("Kindly attach the Medical Certificate, then submit the leave request."))
		if vals.get('state')=='confirm':
			context = {
				'email_to':self.employee_id.parent_id.work_email,
				'email_from':self.env.company.erp_email,
				'subject': "System Notification: Request to approve Leave",
				}
			template = self.env['ir.model.data'].get_object('ax_holidays','email_template_approve_alert')
			self.env['mail.template'].browse(template.id).with_context(context).send_mail(self.id,force_send=True)
		return res
	
	def remainder_notification(self):
		if self.state == 'confirm':
			context = {
				'email_to':self.employee_id.parent_id.work_email,
				'email_from':self.env.company.erp_email,
				'subject': "System Notification: Request to approve Leave",
				}
			template = self.env['ir.model.data'].get_object('ax_holidays','email_template_approve_alert')
			self.env['mail.template'].browse(template.id).with_context(context).send_mail(self.id,force_send=True)
		
	
	def view_calendar(self):
		return {
                'name': _('All Time Off'),
                'view_mode': 'calendar',
                'res_model': 'hr.leave',
                'view_id': self.env.ref('hr_holidays.hr_leave_view_calendar').id,
                'type': 'ir.actions.act_window',
            }
	
class HrLeaveType(models.Model):
	_inherit = "hr.leave.type"
	
	leave_limit = fields.Integer('Leave warning Limit')
	future_days = fields.Boolean('Restrict future dates')
	
	