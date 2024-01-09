# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, time, timedelta
import pytz
from dateutil.rrule import rrule, DAILY


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # hours = fields.Integer("Duration (Hours)")
    # minutes = fields.Integer("Duration (Minutes)")
    from_date = fields.Datetime("From Date", default=datetime.now())
    to_date = fields.Datetime("To Date",readonly=True)
    
    @api.onchange('unit_amount')
    def _onchange_unit_amount(self):
        if self.from_date:
            self.to_date = self.from_date+timedelta(hours=self.unit_amount)

    @api.onchange('name')
    def _onchange_date(self):
        if self.to_date:
            self.date = self.to_date.date()
            
    def write(self, vals):
        if 'unit_amount' in vals:
            vals.update({'to_date': self.from_date+timedelta(hours=self.unit_amount)})
        return super(AccountAnalyticLine, self).write(vals)
    
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone('UTC')
        usertime = pytz.utc.localize(datetime.now()).astimezone(tz)
        dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
        dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
