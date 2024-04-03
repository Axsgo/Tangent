from odoo import models,_
from odoo.exceptions import UserError

	
class ResUsers(models.Model):
	_inherit = "res.users"
	
	def write(self, vals):
		old_groups = self.groups_id.ids
		res = super(ResUsers, self).write(vals)
		new_groups = self.groups_id.ids
		for l in self.returnNotMatches(old_groups,new_groups):
			for r in l:
				if r in (self.env.ref('account.group_account_invoice').id,self.env.ref('account.group_account_manager').id) and self.env.ref('ax_groups.admin_super_group').id not in self.env.user.groups_id.ids:
					raise UserError(_("Please contact your super admin, you do not have access to the accounting."))
		return res
	
	def returnNotMatches(self,a, b):
		return [[x for x in a if x not in b], [x for x in b if x not in a]]
	