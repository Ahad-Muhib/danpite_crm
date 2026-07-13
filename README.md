# danpite_crm

Django CRM with built-in auth, staff management, client listing, invoices, payments, expenses, and an accounts section.

## Features

- Login and logout using Django auth
- Staff creation and listing
- Client listing and creation
- Invoice creation and listing
- Payment recording and listing
- Expense tracking
- Accounts ledger view

## Setup

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Apply migrations to the default SQLite database:

```bash
python manage.py migrate
```

3. Create an admin user so you can log in:

```bash
python manage.py createsuperuser
```

4. Run the development server:

```bash
python manage.py runserver
```

## Notes

- The project uses SQLite only. No external database is configured.
- Staff-only screens require a logged-in user with the `is_staff` flag.