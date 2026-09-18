# Rainchem

A motorcycle lubricant and parts e-commerce site for Rainchem International,
rebuilt as a React frontend backed by a Python (Flask) API and a MySQL
database, with a Python-based RAG chatbot.

```
rainchem/
  frontend/    React app (Vite)
  backend/     Flask API, RAG chatbot, business logic
  database/    MySQL schema and seed data
```

## 1. Set up MySQL

Create the database and an application user, then load the schema:

```
mysql -u root -p -e "CREATE USER 'rainchem_app'@'localhost' IDENTIFIED BY 'rainchem_pass';"
mysql -u root -p < database/schema.sql
mysql -u root -p -e "GRANT ALL PRIVILEGES ON rainchem.* TO 'rainchem_app'@'localhost'; FLUSH PRIVILEGES;"
```

`database/schema.sql` creates all tables and seeds the product catalog and
knowledge base. It does not create login accounts, since passwords need to
be hashed properly. Run the seed script for that after installing the
backend dependencies (step 2).

## 2. Backend (Flask + MySQL + RAG)

```
cd backend
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env with your DB credentials
python seed.py                  # creates the demo admin and customer accounts
python run.py
```

The API runs on `http://localhost:5000` by default.

Demo accounts created by `seed.py`:
- Admin: `admin@raincheminternational.com` / `Admin123!`
- Customer: `rider@example.com` / `Rider123!`

### RAG chatbot

`app/services/rag.py` builds a TF-IDF index over the admin-approved
knowledge base and retrieves the closest matching answer by cosine
similarity. It never invents an answer; if nothing matches confidently it
returns a fallback message and logs the question so an admin can review it.

### Email and notifications

`app/services/email_service.py` sends verification codes, password reset
links, and order notifications by SMTP if `SMTP_HOST` is set in `.env`.
Without SMTP configured, messages are printed to the console and also saved
to the `notifications` table, so nothing is lost during development.

### Google Sign-In

To enable the "Sign in with Google" button:
1. Create an OAuth Client ID (type: Web application) in the
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Add your frontend origin (e.g. `http://localhost:5173`) to Authorized
   JavaScript origins.
3. Put the client ID in `backend/.env` as `GOOGLE_CLIENT_ID` and in
   `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`.

Without a client ID configured, the button shows a disabled placeholder
instead of breaking.

## 3. Frontend (React)

```
cd frontend
npm install
cp .env.example .env       # defaults already point at localhost:5000
npm run dev
```

The storefront runs on `http://localhost:5173`. The admin dashboard is at
`/admin/login` (no public sign-up, accounts are created from inside the
dashboard's Admin Accounts page).

## Order and receipt flow

1. A customer checks out. The order is created with status
   "Pending Confirmation", the customer gets a confirmation email, and the
   order appears in the admin Orders page.
2. While pending, the customer can cancel the order themselves from
   My Orders.
3. An admin reviews the order and clicks Confirm. This generates a receipt
   (stored in the `receipts` table) and emails the customer.
4. Once confirmed, the customer sees a "Print Receipt" button on that order
   in My Orders, which opens a printable receipt page.

## Bulk pricing and shipping

Buying 5, 10, or 20+ units of the same product automatically applies a 5%,
10%, or 15% discount. Orders qualify for free shipping once the discounted
subtotal reaches PHP 1,500 or the cart holds 10 or more items. This logic
lives in `backend/app/services/pricing.py` and is mirrored on the frontend
in `frontend/src/context/CartContext.jsx` so totals display correctly
before checkout confirms them server-side.

## Notes

- This is a learning/demo project. The Flask dev server and Vite dev server
  are not meant for production; use a proper WSGI server (gunicorn) and a
  production build (`npm run build`) when deploying.
- Product photos uploaded from the admin panel are stored as base64 text in
  the `products.image_photo` column. That's fine for a handful of images,
  but a real deployment should store files in object storage instead and
  keep only a URL in the database.
