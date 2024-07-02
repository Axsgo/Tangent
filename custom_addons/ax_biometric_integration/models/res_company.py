from odoo import api, fields, models, _
import mysql.connector
from odoo import exceptions
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    db_hostname = fields.Char(string='IP Address of Host', required=True, tracking=True)
    db_name = fields.Char(string='Database Name', required=True, tracking=True)
    db_port = fields.Integer(string='Port', tracking=True)
    db_username = fields.Char(string='Username', required=True, tracking=True)
    db_password = fields.Char(string='Password', required=True)
    db_test_query = fields.Text(string='Fetch Query', required=True, default= 'SELECT * FROM tmp_attendance;', tracking=True)
    db_query_result = fields.Text(string='Connection Result', readonly=True)
    fetch_date = fields.Date(string='Fetch Date', required=True, tracking=True)

    def run_testquery(self):
        try:
            con=mysql.connector.connect(host=self.db_hostname,
                                        database=self.db_name,
                                        user=self.db_username,
                                        password=self.db_password,
                                        auth_plugin='mysql_native_password')

            cursor=con.cursor()
            cursor.execute(self.db_test_query)
            recordss=cursor.fetchall()
            self.db_query_result=recordss
            con.close()
            cursor.close()

        except Exception as e:
            raise ValidationError(_('Error reading data from MySQL table'))
            raise exceptions.Warning('Warning message',e)

        finally:
            con = mysql.connector.connect(host=self.db_hostname,
                                          database=self.db_name,
                                          user=self.db_username,
                                          password=self.db_password,
                                          auth_plugin='mysql_native_password')
            if (con.is_connected()):
                con.close()
                
    def fetch_attendance_data(self):
        self = self.env['res.company'].search([('id','=',1)])
        try:
            con=mysql.connector.connect(host=self.db_hostname,
                                        database=self.db_name,
                                        user=self.db_username,
                                        password=self.db_password,
                                        auth_plugin='mysql_native_password')

            cursor=con.cursor()
            cursor.execute(self.db_test_query)
            recordss=cursor.fetchall()
            date_recordss = [record for record in recordss if record[0] == self.fetch_date]
            employee_ids = self.env['hr.employee'].search([])
            for employee in employee_ids:
                result_set = [record for record in date_recordss if record[3] == employee.bio_code]
                if result_set:
                    lines = []
                    for result in result_set:
                        if result[1].year == 1970 or result[2].year == 1970:
                            employee.missing_count+=1
                        else:
                            lines.append((0,0,{'check_in':result[1]- timedelta(hours=5.5),'check_out':result[2]- timedelta(hours=5.5)}))
                    first_check_in = min(result_set, key=lambda x: x[1])
                    last_check_out = max(result_set, key=lambda x: x[2])
                    self.env['hr.attendance'].create({'fetch_date':self.fetch_date,'employee_id':employee.id,'line_ids':lines,'check_in':first_check_in[1]- timedelta(hours=5.5),'check_out':last_check_out[2]- timedelta(hours=5.5)})
                # if employee.missing_count > 5:
                #     emails = ''
                #     group_id = self.env.ref('ax_groups.admin_user_group')
                #     emails+=",".join(group_id.users.mapped('login'))
                #     template = self.env.ref('ax_biometric_integration.email_template_manager_missing_count_alert')
                #     template.with_context({'email_to':employee.parent_id.work_email,'email_cc':emails,'email_from':self.erp_email}).send_mail(employee.id, force_send=True)
            self.fetch_date = self.fetch_date + relativedelta(days=1)
            con.close()
            cursor.close()

        except Exception as e:
            # raise ValidationError(_('Error reading data from MySQL table'))
            # raise exceptions.Warning('Warning message',e)
            raise ValidationError(_(e))
        finally:
            con = mysql.connector.connect(host=self.db_hostname,
                                          database=self.db_name,
                                          user=self.db_username,
                                          password=self.db_password,
                                          auth_plugin='mysql_native_password')
            if (con.is_connected()):
                con.close()
