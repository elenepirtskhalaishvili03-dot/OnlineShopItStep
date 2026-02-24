## OnlineShop – Django + MSSQL Online Store

This is a simple **full‑stack Django application** (no DRF) for an online shop with:

- **JWT-based authentication** using cookies (no REST API).
- **Products** listing and detail pages.
- **Shopping cart** for logged-in users.
- **Order placement** and **order history**.
- **Custom admin dashboard** (plus regular `django-admin`) where admins can **add, edit, delete, deactivate, and re-activate products**, and view orders.
- **MSSQL** as the database using `mssql-django`.

---

## 1. Tech stack

- **Backend**: Django 5.x (`Django==5.2.11`)
- **Database**: Microsoft SQL Server (MSSQL) via `mssql-django`
- **Auth**: Django `User` model + JWT (`pyjwt`) stored in HttpOnly cookies
- **Frontend**: Django templates + Bootstrap 5

---

## 2. Project structure (key files)

- `manage.py` – Django management script.
- `onlineshop/`
  - `settings.py` – Django settings (MSSQL, JWT middleware, templates, static).
  - `urls.py` – Root URL configuration; includes `shop.urls`.
- `shop/`
  - `models.py` – `Product`, `Cart`, `CartItem`, `Order`, `OrderItem`.
  - `views.py` – All views for auth, products, cart, orders, admin dashboard.
  - `urls.py` – URL routing for the shop.
  - `middleware.py` – `JWTAuthenticationMiddleware` and `create_jwt_for_user`.
  - `forms.py` – `UserRegistrationForm`, `LoginForm`, `ProductForm`.
  - `admin.py` – Model registrations for Django admin.
- `templates/`
  - `base.html` – Global Bootstrap layout, navbar, and shared styling.
  - `shop/*.html` – Pages for products, cart, orders, auth, and admin dashboard (polished with modern Bootstrap UI).
- `requirements.txt` – Python dependencies.

---

## 3. Installation & setup

### 3.1. Clone project and create virtual environment

From your machine (pick the commands for your OS):

```bash
cd "<PROJECT_ROOT>"
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# . venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> If you already created the virtual environment, you can skip recreating it and just activate it.

---

## 4. SQL Server & ODBC configuration

This project supports **SQL Server + `mssql-django`**. For Windows Authentication (Integrated Security), you’ll typically use:

- **SQL Server instance**: e.g. `localhost\SQLEXPRESS` (replace with your instance)
- **Database name**: `OnlineShop` (or your chosen DB name)
- **Auth**: Windows Authentication (uses the Windows account running Django)
- **ODBC driver**: `ODBC Driver 17 for SQL Server` (or 18 — just match what’s installed)
- **Trust server certificate**: `yes`

### 4.1. Install / verify the Microsoft ODBC driver (Windows)

1. Install one of:
   - Microsoft ODBC Driver 17 for SQL Server
   - Microsoft ODBC Driver 18 for SQL Server
2. Verify the driver name on your machine:

```powershell
Get-OdbcDriver -Name "*SQL Server*" | Select-Object Name
```

Or from Python:

```powershell
python -c "import pyodbc; print(pyodbc.drivers())"
```

### 4.2. Django `DATABASES` (Windows Authentication)

Make sure `onlineshop/settings.py` uses **trusted connection** and your SQL Server instance name:

```python
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'OnlineShop',
        'HOST': r'localhost\SQLEXPRESS',
        'PORT': '',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',  # or 18, match your system
            'trusted_connection': 'yes',
            'trust_server_certificate': 'yes',
        },
    }
}
```

### 4.3. Create the `OnlineShop` database and grant permissions

`mssql-django` expects the database to exist already.

In **SQL Server Management Studio (SSMS)** or **Azure Data Studio**, run:

```sql
CREATE DATABASE [OnlineShop];
```

Then ensure **your Windows login** has access to that DB:

- Create/Login user if needed (SSMS: **Security → Logins**)
- Map it to `OnlineShop` (SSMS: Login → **User Mapping**)
- For development, you can grant `db_owner` on `OnlineShop` (or a more restricted role if you prefer)

> Tip for named instances: make sure the **SQL Server** service for your instance is running. Starting **SQL Server Browser** can help clients discover the port for named instances.

---

## 5. Django database migrations & superuser

Once the database and ODBC driver are ready:

```bash
cd "<PROJECT_ROOT>"
# Activate venv (Windows PowerShell):
.\venv\Scripts\Activate.ps1

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Follow the prompts to create an admin user. That user will have access to:

- The standard Django admin at `/admin/`.
- The custom admin dashboard at `/dashboard/` (because `is_staff=True`).

---

## 6. Running the development server

With the virtual environment active:

```bash
cd "<PROJECT_ROOT>"
# Activate venv (Windows PowerShell):
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Open the app in your browser:

- Shop front page: `http://127.0.0.1:8000/`
- Django admin: `http://127.0.0.1:8000/admin/`
- Custom admin dashboard: `http://127.0.0.1:8000/dashboard/`

---

## 7. Application features

### 7.1. Authentication (JWT + Django)

- Uses Django’s built-in `User` model (`django.contrib.auth`).
- `shop/forms.UserRegistrationForm` provides a registration form for new customers.
- `shop/forms.LoginForm` handles username/password login.
- `shop.middleware.JWTAuthenticationMiddleware`:
  - Reads an `access_token` JWT from an **HttpOnly cookie**.
  - Verifies it using `SECRET_KEY`.
  - Loads the user and sets `request.user`.
- The login view (`shop.views.login_view`) issues a new JWT on successful authentication and sets it as a cookie.
- The logout view (`shop.views.logout_view`) clears the cookie.

**Token details:**

- Created via `create_jwt_for_user(user)` in `shop/middleware.py`.
- Includes `user_id` and an expiry of **1 day**.
- Signed with HS256 using Django’s `SECRET_KEY`.

> Note: This is a simple JWT setup for learning/demo purposes. For production, consider refresh tokens, HTTPS-only cookies, and rotation strategy.

### 7.2. User roles

- **Customer**: default for newly registered users (`is_staff=False`).
- **Admin**: any user with `is_staff=True` (usually created via `createsuperuser`).

Admins can:

- Access `/admin/` (Django admin).
- Access `/dashboard/`, `/dashboard/products/add/`, `/dashboard/products/<id>/edit/`, `/dashboard/products/<id>/delete/`, `/dashboard/products/<id>/activate/`, and `/dashboard/orders/`.

---

## 8. Data model (tables)

Defined in `shop/models.py`:

- **`Product`**
  - `name` – product name.
  - `description` – text description.
  - `price` – decimal, max 10 digits, 2 decimals.
  - `stock` – current stock quantity.
  - `image_url` – optional URL to product image.
  - `is_active` – whether product is visible in the shop.
  - Timestamps: `created_at`, `updated_at`.

- **`Cart`**
  - One-to-one with `User` (`user = OneToOneField(User, ...)`).
  - `created_at` timestamp.
  - `total_amount` property: sum of subtotals of its items.

- **`CartItem`**
  - `cart` – FK to `Cart`.
  - `product` – FK to `Product`.
  - `quantity` – positive integer.
  - `subtotal` property: `product.price * quantity`.
  - Unique constraint on (`cart`, `product`).

- **`Order`**
  - `user` – FK to `User`.
  - `created_at` – timestamp.
  - `status` – `pending`, `completed`, or `cancelled` (default `pending`).
  - `total_amount` – total price at the time of order placement.

- **`OrderItem`**
  - `order` – FK to `Order`.
  - `product` – FK to `Product` (with `PROTECT` to keep history).
  - `quantity` – positive integer.
  - `price_at_purchase` – snapshot of the product price when order was placed.

---

## 9. URLs & views

### 9.1. Root URLs (`onlineshop/urls.py`)

- `admin/` → Django admin.
- `''` (root) → includes `shop.urls`.

### 9.2. Shop URLs (`shop/urls.py`)

- `/` – `product_list`: list of active products.
- `/product/<int:pk>/` – `product_detail`: single product page.
- `/register/` – `register_view`: user registration.
- `/login/` – `login_view`: user login (JWT cookie).
- `/logout/` – `logout_view`.
- `/cart/` – `cart_view`: view current user’s cart.
- `/cart/add/<int:product_id>/` – `add_to_cart` (POST): add a product to cart.
- `/cart/remove/<int:item_id>/` – `remove_from_cart` (POST): remove an item.
- `/orders/place/` – `place_order` (POST): convert cart into an order, clear cart.
- `/orders/history/` – `order_history`: list of user’s orders.
- `/dashboard/` – `admin_dashboard`: custom dashboard (admins only) with product summary table.
- `/dashboard/products/add/` – `admin_add_product`: add new product (admins only).
- `/dashboard/products/<int:pk>/edit/` – `admin_edit_product`: edit product (admins only).
- `/dashboard/products/<int:pk>/delete/` – `admin_delete_product`: delete/deactivate product (admins only).
- `/dashboard/products/<int:pk>/activate/` – `admin_activate_product`: activate previously deactivated product (admins only).
- `/dashboard/orders/` – `admin_order_list`: see all orders (admins only).

---

## 10. Frontend templates

All templates use **Bootstrap 5** and extend `base.html`.

- `base.html`
  - Navbar with links for products, cart, order history, admin dashboard.
  - Login/logout/register controls.
  - Message alerts for feedback.
  - Global Bootstrap-based styling (background, card hover effects, rounded buttons).

- `shop/product_list.html`
  - Displays all active products in a responsive grid of hoverable cards with image, name, price badge, and short description.

- `shop/product_detail.html`
  - Shows product details, image, price badge, stock, and buttons to add to cart or view cart.

- `shop/cart.html`
  - Modern card + table layout of cart items with right-aligned numeric columns and a clear total + checkout button.

- `shop/order_history.html`
  - Shadowed cards listing each order with date, status badge, items, and total.

- `shop/login.html` / `shop/register.html`
  - Centered card-style forms for authentication and registration.

- `shop/admin_dashboard.html`
  - Summary cards for product count and order count.
  - Buttons to add products and view orders.
  - A product table showing name, price, stock, active status, and **Edit/Delete/Activate** actions (activate only visible for inactive products).

- `shop/admin_product_form.html`
  - Card-based form used for both creating and editing products (title and button text adapt).

- `shop/admin_product_confirm_delete.html`
  - Confirmation card for deleting a product.

- `shop/admin_orders.html`
  - Table containing all orders with user, status, total, and created date.

---

## 11. Common errors & troubleshooting

- **ODBC driver not found**  
  Error like:
  > Can't open lib 'ODBC Driver 17/18 for SQL Server'

  - Ensure you installed `msodbcsql17` or `msodbcsql18`.
  - Check drivers via `odbcinst -q -d`.
  - Set the exact driver name in `DATABASES['default']['OPTIONS']['driver']`.

- **Cannot open database "OnlineShop" requested by the login (4060)**  
  - The `OnlineShop` database does not exist yet.
  - Create it manually via `CREATE DATABASE [OnlineShop];`.

- **Login failed / permission denied (Windows Auth)**  
  - Ensure your Windows user is mapped to the `OnlineShop` database and has permission.
  - If you run Django from a different account than expected, it will try to connect as *that* Windows user.

---

## 12. How to start from scratch (summary)

1. Create and activate virtual env; install requirements:
   ```bash
   cd "<PROJECT_ROOT>"
   python -m venv venv
   # Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Install SQL Server ODBC driver and confirm driver name.
3. Create `OnlineShop` database in SQL Server:
   ```sql
   CREATE DATABASE [OnlineShop];
   ```
4. Ensure `onlineshop/settings.py` uses the correct driver and connection settings (avoid hard-coding secrets; prefer environment variables).
5. Run:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```
6. Visit `http://127.0.0.1:8000/` and start using the shop.

---

## 13. Next steps / customization ideas

- Add product **categories** and filters.
- Add **pagination** to product list.
- Add **order status management** in the custom admin dashboard.
- Integrate a real **payment provider** and store payment status on `Order`.
- Switch to environment variables for secrets and DB credentials instead of hard-coding.

