
# Script to reset admin password
try:
    user = env['res.users'].search([('login', '=', 'admin')], limit=1)
    if user:
        user.write({'password': 'admin'})
        env.cr.commit()
        print("SUCCESS: Password reset to 'admin'")
    else:
        print("FAILURE: User 'admin' not found.")
        # List users
        users = env['res.users'].search([])
        print("Available users:", users.mapped('login'))
except Exception as e:
    print(f"ERROR: {e}")
import sys
sys.exit()
