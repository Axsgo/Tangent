# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, time, timedelta
import pytz
from dateutil.rrule import rrule, DAILY
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    @api.model
    def default_get(self, field_list):
        result = super(AccountAnalyticLine, self).default_get(field_list)
        result['unit_amount'] = 0.0
        if 'date' in result:
            if not self.env['hr.timesheet.submit'].search([('from_date','<=',result.get('date')),('to_date','>=',result.get('date'))]):
                raise UserError(_("You can not create timesheet for future date"))
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
            if self.env['hr.timesheet.submit.line'].search([('employee_id','=',employee_id),('submit_id.from_date','<=',result.get('date')),('submit_id.to_date','>=',result.get('date')),('state','=','lock')]):
                result['message'] = "You can not create/update timesheet for this date"
        # date = result.get('date', False)
        # if date:
        #     date = datetime.combine(date, datetime.min.time())
        #     result['from_date'] = date.replace(hour=0, minute=0, second=0) - timedelta(hours=5.5)
        #     result['to_date'] = date.replace(hour=0, minute=0, second=0) - timedelta(hours=5.5)
        return result
    
    
    start_time = fields.Float("Start Time (HH:MM)")
    start_meridiem = fields.Selection([('AM','AM'),('PM','PM')],"Start Meridiem",default='AM')
    end_time = fields.Float("End Time (HH:MM)")
    end_meridiem = fields.Selection([('AM','AM'),('PM','PM')],"End Meridiem",default='PM')
    start = fields.Float("Start",compute='_get_railway_time')
    end = fields.Float("End",compute='_get_railway_time')
    # from_date = fields.Datetime("Start Time")
    # to_date = fields.Datetime("End Time",compute='_onchange_unit_amount')
    status_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc')
    description = fields.Text('Description')
    message = fields.Text('Message')
    # is_project_start_mail_sent = fields.Boolean("Project Start Mail Sent?",default=False,copy=False)
    
    @api.onchange('project_id','unit_amount')
    def _onchange_project_unit_amount(self):
        self.name = str(self.project_id.project_no)+' - '+str(self.project_id.name)
        
    @api.onchange('project_id')
    def onchange_project_id(self):
        self.status_id = False
        res = {'domain': {'status_id': "[('id', 'not in', False)]"}}
        if self.project_id:
            res['domain']['status_id'] = "[('id', 'in', %s)]" % self.project_id.allowed_stage_ids.ids
        return res
    
    @api.constrains('start_time','end_time','start','end')
    def timesheet_constrains(self):
        if self.start_time > 12 or self.end_time > 12:
            raise UserError("Start Time and End Time should be less than or equal to 12.")
        if self.start_time <= 0:
            raise UserError(_("Start Time should be greater than 0."))
        if self.end_time <= 0:
            raise UserError(_("End Time should be greater than 0."))

    @api.onchange("start","end")
    def update_unit_time(self):
        if self.start and self.end:
            self.unit_amount = self.end - self.start
        else:
            self.unit_amount = 0

    @api.depends('start_time','end_time','start_meridiem','end_meridiem')
    def _get_railway_time(self):
        for rec in self:
            ## Start Time
            if rec.start_time and rec.start_meridiem:
                if rec.start_meridiem == 'PM':
                    start = rec.start_time+12
                    if start >= 24:
                        rec.start = rec.start_time
                    else:
                        rec.start = start
                else:
                    rec.start = rec.start_time
            else:
                rec.start = 0
            ## End Time
            if rec.end_time and rec.end_meridiem:
                if rec.end_meridiem == 'PM':
                    end = rec.end_time+12
                    if end >= 24:
                        rec.end = rec.end_time
                    else:
                        rec.end = end
                else:
                    rec.end = rec.end_time
            else:
                rec.end = 0
    
    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountAnalyticLine, self).create(vals_list)
        for res in lines:
            if self.env['hr.timesheet.submit.line'].search([('employee_id','=',res.employee_id.id),('submit_id.from_date','<=',res.date),('submit_id.to_date','>=',res.date),('state','=','lock')]):
                raise UserError(_("You can not create/update timesheet for this date"))
            if res.unit_amount <= 0:
                raise UserError(_("You can not update zero duration timesheet"))
            # if res.to_date < res.from_date:
            #     raise UserError(_("End Time should be greater than Start Time."))
            res.project_id.stage_id = res.status_id.id
        return lines

    def write(self, vals):
        rec = super(AccountAnalyticLine, self).write(vals)
        if 'holiday_id' in vals:
            return rec
        if self.env['hr.timesheet.submit.line'].search([('employee_id','=',self.employee_id.id),('submit_id.from_date','<=',self.date),('submit_id.to_date','>=',self.date),('state','=','lock')]):
            raise UserError(_("You can not create/update timesheet for this date"))
        if self.unit_amount <= 0:
            raise UserError(_("You can not update zero duration timesheet"))
        # if self.to_date < self.from_date:
        #     raise UserError(_("End Time should be greater than Start Time."))
        # if self.date != self.from_date.date() or self.date != self.to_date.date():
        #     raise UserError("Start Time and End Time date should be same as Timesheet Date.")
        self.project_id.stage_id = self.status_id.id
        return rec
    
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone('UTC')
        dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
        dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
    
    def float_to_time(self,float_value):
        hours = int(float_value)
        minutes = int((float_value - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def _entry_send_project_start_alert(self):
        timesheet_ids = self.env['account.analytic.line'].search([('project_id','!=',False),('project_id.timesheet_count','>=',1),
            ('project_id.is_project_start_mail_sent','=',False)])
        if timesheet_ids:
            for timesheet_id in timesheet_ids:
                context = {
                    'email_to':timesheet_id.project_id.user_id.email,
                    'email_cc':'',
                    'email_from':self.env.company.erp_email,
                    'start_time':str(self.float_to_time(timesheet_id.start_time)+' '+timesheet_id.start_meridiem),
                    'end_time':str(self.float_to_time(timesheet_id.end_time)+' '+timesheet_id.end_meridiem),
                    'float_time':self.float_to_time(timesheet_id.unit_amount),
                }
                timesheet_id.project_id.is_project_start_mail_sent = True
                template = self.env['ir.model.data'].get_object('sttl_timesheet_calendar', 'email_template_project_start_alerts')
                self.env['mail.template'].browse(template.id).with_context(context).send_mail(timesheet_id.id,force_send=True)
                
                