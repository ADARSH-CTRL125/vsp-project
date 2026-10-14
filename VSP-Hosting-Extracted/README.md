# VSP Vehicle Spare Parts

VSP is a responsive vehicle parts storefront with a FastAPI backend and SQLite for local review. The project also retains the existing inventory management page.

## Start the review site

From this folder in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the VSP shop. The catalogue is initialized on first start and stored in `vsp.db` in this folder. No PostgreSQL server or payment gateway is needed for local review.

## Store pages

- `/` — public parts shop, vehicle finder, catalogue, cart and COD/UPI checkout.
- `/manage` — Admin sign-in, customer orders and requests, catalogue, and the Selling Bills workspace.
- `/inventory` — original internal inventory management application.
- `/docs` — interactive API documentation.
- `/health` — service health check.

To create the first manager account, start the service once so it creates the local database, then stop it and run:

```powershell
py scripts/create_admin.py
```

Choose a private password of at least 12 characters. The setup script also asks for an optional email; add one if you plan to enable Admin password resets. Start the service again and sign in at `/manage`. Manager accounts use the existing Admin/Staff roles. The default local JWT key is for development only; set a private `JWT_SECRET` in `.env` before sharing the review site or deploying it.

## Current shop features

- Responsive desktop and mobile storefront with VSP logo and supplied car-brand logos.
- Customer registration and sign-in. New registrations receive the restricted `Viewer` role; they cannot access staff or admin routes.
- Password reset links are one-time and expire after 30 minutes. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, and `PUBLIC_BASE_URL` in `.env` to deliver reset emails. Without SMTP, no reset email can be delivered.
- Catalogue search by part, part number, brand, compatible model or category.
- Vehicle make/model/year/variant finder, cart, cash-on-delivery orders, and UPI QR orders with manual Admin verification.
- Part sourcing request form for items not in the starter catalogue.
- Admin tools to add/edit catalogue parts and update stock or visibility, review orders and update order status, verify UPI payments, print bills, open a WhatsApp bill draft addressed to the customer's checkout number, and review customer requests.
- Admin-only CSV catalogue import supports up to 10,000 products per file. Use `scripts/store_catalog_template.csv` for the field names; existing product IDs are updated and new IDs are added.
- The backend checks order totals and stock. COD orders reserve available stock at checkout. UPI orders remain pending and reserve stock only after Admin verifies payment. Both provide an order reference and can be tracked with the order number and checkout phone. Admin uploads the genuine VSP UPI QR (PNG, up to 5 MB) under Selling Bills; UPI checkout stays disabled until then. WhatsApp opens a prefilled customer chat for Admin to review and send. Debit-card gateway processing is not enabled yet.
- Existing inventory API and staff application remain available.

## API summary

Public endpoints: `GET /api/store/products`, `GET /api/store/brands`, `GET /api/store/categories`, `GET /api/store/payment-qr`, `POST /api/store/orders`, `POST /api/store/orders/track`, `POST /api/store/leads`, `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/forgot-password`, and `POST /api/auth/reset-password`.

Admin endpoints require `Authorization: Bearer <token>`: `GET /api/admin/store/products`, `POST/PUT /api/store/products`, `GET /api/store/orders`, `PATCH /api/store/orders/{id}/status`, `PATCH /api/store/orders/{id}/payment?status=Paid|Failed`, `POST /api/admin/store/payment-qr`, and `GET /api/store/leads`. Sign in through `POST /api/auth/login`.

The included SQLite database is a VSP starter database with sample catalogue rows. AutoDukan's private production database is not publicly available to this project. To migrate data from it, export the permitted product data from its database/API as CSV, map it to `scripts/store_catalog_template.csv`, then sign in at `/manage` as Admin and use **Import CSV**. The importer validates the file and updates products by ID; it does not copy passwords, customer accounts, payment records or private AutoDukan data.

## Customer accounts and catalogue scope

Use **Profile** in the shop to create a customer account or sign in with username/email and password. Passwords are hashed; public registration cannot create Admin or Staff accounts. Existing SQLite installations add the nullable account email field and reset-token table when the app next starts. The password reset form is at `/reset-password` and requires an SMTP provider to send the email link.

The brand and vehicle finder includes 12 common Indian-market makes and example models. The seeded catalogue currently has 572 sample rows: at least 40 brand-specific starter listings for each of the 12 makes, 40 Nut & Bolt types, and 24 additional Car Care examples such as car perfumes and foam wash products, plus the original starter rows. These are college-project/demo listings with zero stock, illustrative prices and synthetic `DEMO-*` references; they are not an exhaustive or verified fitment database. Replace sample stock, prices, compatibility and part numbers with authorized supplier data before accepting real orders. The store manager and its catalogue/order/request data require the Admin role; public customer accounts do not receive that role.

## Hosting later

Before production, configure PostgreSQL and a strong private `JWT_SECRET`, add the public frontend origin to `CORS_ORIGINS`, use HTTPS, configure persistent database backups, and set up rate limiting and monitoring. UPI uses a manually verified QR transfer and is not gateway-integrated. Debit-card acceptance needs a payment provider account, server-side secrets, verified payment callbacks, and deployment configuration before it can be offered. Run database migrations before upgrading an existing production database. Do not deploy the development secret or an unreviewed demo catalogue as production data.
