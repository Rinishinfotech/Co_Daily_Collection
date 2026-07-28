# LedgerFlow Authentication Test Playbook

1. Sign in as administrator with phone `9999999999` and password `Admin@123`.
2. Confirm the administrator sees analytics, vendor management, employee management, activity panels, and logout.
3. Sign in as a seeded employee with phone `+91 98765 42100` and temporary password `Welcome@123`.
4. Confirm the employee cannot access administrator endpoints and is prompted to replace their temporary password.
5. Confirm employee collections, expenses, dashboard, and profile only show the signed-in employee's activity.
6. Add a new employee from the admin portal with a temporary password; confirm the new person can sign in and must change that password.