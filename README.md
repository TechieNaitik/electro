# Electro

A Django-based E-commerce application.

## Features

- **Refactored Product Model**: Advanced data structure splitting generic names into specific `Brand`, `Model Name`, and `Variant Specs` for improved searchability and SEO.
- **Brand Management**: Dedicated ecosystem for managing brands independently, with full relationship mapping to products.
- **Multi-variant Ecosystem**: Engineered a robust relational database schema that supports infinite product variations (Color, Storage, Size, etc.) attached to a parent product. Features include custom pricing overrides, individualized stock tracking, dedicated SKU mapping, isolated multi-image galleries per variant, and an interactive, lightning-fast variant selector on the product page.
- **User Authentication**: Custom customer registration, login system, and password reset via OTP.
- **Product Browsing**: Shop page with advanced brand-wise sorting/filtering, single product view, bestsellers, and dynamic inventory status.
- **Product Pagination**: Robust, centralized pagination across Shop, Bestsellers, Home, and Category Filter pages, featuring a 3x4 grid layout (12 products per page) and persistent filter/sorting parameters across pages.
- **Wishlist**: Per-user product saving system with AJAX-powered live updates and a dedicated wishlist management page.
- **Product Comparison**: Full-featured side-by-side comparison suite, accessible exclusively from individual product pages:
  - **Highlight Differences Toggle**: Real-time row-level visual diff that yellow-flags diverging values and green-tints matching ones across all compared products.
  - **Quantity Selector**: Inline `+`/`−` stepper per product column that dynamically updates the Add-to-Cart link with the chosen quantity.
  - **Wishlist Integration**: AJAX-powered wishlist toggle within the compare table, reflecting saved state on load and updating in real-time without page refresh.
- **Shopping Cart**: Interactive AJAX-powered cart with real-time updates and toast notifications.
- **One-Click Checkout**: Refactored checkout flow that pulls shipping and billing details (including State and Phone) directly from stored user profiles.
- **Centralized Profile Management**: Comprehensive user dashboard for managing personal details, contact info, and multi-field shipping addresses (Address, City, State, Country, Zip).
- **Inventory Management**: Real-time stock validation and automatic stock deduction upon order completion.
- **Product Image Gallery**: Interactive multi-image gallery on product detail pages featuring thumbnail navigation and native touch-swipe support for mobile devices.
- **Custom Site Administration**: A premium, isolated administration dashboard featuring:
  - **Brand Ecosystem**: Full CRUD operations for Brands.
  - **Advanced Analytical Dashboard**: Real-time business intelligence using Chart.js to visualize sales trends by brand/category, order activity heatmaps, and AI-powered 7-day sales forecasting via scikit-learn.
  - **Dynamic Data Export**: Advanced administrative tools to export Customers, Orders, and Products into multiple professional formats (.pdf, .xlsx, .docx, .csv).
  - **Gallery Management**: Re-engineered administrative backend for handling secondary product images, featuring a robust "Mark for Deletion" flow to prevent accidental data loss and real-time selection success indicators with count-based update notifications.
  - **Security & Sessions**: Secure login wall with hashed passwords, brute-force protection, and independent admin session management.
  - **Resource Management**: Complete CRUD operations for Products and Categories with instant search capability.
- **Inventory Insights**: Real-time stock alerts and business analytics/statistics.
- **Invoice Generation**: Premium, professional **"Square-style" billing UI** rendered via headless Playwright. Features a space-efficient 3-column Information Grid and absolute-path asset injection for 100% layout reliability in PDF downloads.
- **Automated Order Lifecycle Notifications**: Event-driven notification system sending branded HTML updates for:
-   - **Order Confirmation**: With embedded order summary and PDF invoice attachment.
-   - **Logistics Updates**: "Shipped" and "Out for Delivery" alerts with courier name and tracking links.
-   - **Delivery Confirmation**: Success confirmation with review prompts.
-   - **Returns & Cancellations**: Specialized variants for reversed orders.
-   - **Async Execution**: Leverages Python threading to ensure zero impact on frontend performance.
- **Automated Testing & Coverage Dashboard**: Full-featured `pytest` suite integrated directly into the custom site-admin panel:
  - **Live Terminal Stream**: Real-time terminal output streaming directly to the browser via AJAX for instant test feedback and auto-scrolling terminal logs.
  - **Visual Coverage Dashboard**: Automated `pytest-cov` reporting with a dedicated, auto-refreshing interface to track code quality and logic gaps.
- **Universal Star Rating & Review System**: Comprehensive peer-review ecosystem featuring:
  - **Individual Reviews**: Per-user rating and review submission for every product.
  - **Review Interactivity**: Selective star rating on product pages and interactive feedback forms.
  - **Mandatory Feedback**: Enforced rating (1-5) and written review text for all submissions.
  - **Dynamic Aggregation**: Global average ratings calculated in real-time from all user reviews across the platform.
  - **Advanced User Tracking**: Multi-layered duplicate prevention for individual reviews (Account-based, Session-based, and IP-based).
  - **Rich UI**: Interactive star displays, hover effects, and premium gold-yellow star aesthetics.
  - **Context-Aware Forms**: Intelligent pre-filling of name and email for logged-in customers.
- **Mock Payment Gateway Integration**: Fully functional end-to-end **Razorpay (Test Mode)** integration using the **Razorpay Checkout modal**. Features include secure server-side order creation, HMAC-SHA256 signature verification for payment security, and real-time transaction finalization.
- **Dynamic Currency Converter**: Site-wide conversion system fetching live exchange rates from the **ExchangeRate-API** with a **Two-Tier Caching** strategy (L1 server-side memory, L2 client-side `localStorage`). Features reactive price updates across all templates without page reloads and a manual **Admin Sync Governance** tool for real-time rate refreshing.
- **Coupon Code Engine**: Rule-based promotional discount system supporting **Percentage** and **Fixed Amount** coupons with minimum order thresholds, usage limits, date validity, and per-customer tracking. Includes a full admin management dashboard with usage analytics, AJAX-powered cart integration, and automatic embedding in the Invoice PDF.
- **Contact & Support**: Support pages and contact functionality.
- **Comprehensive Error Handling**: Built-in diagnostic system that captures and displays detailed error context (code snippets, stack traces, line numbers) for developers, while maintaining a sleek, secure experience for end-users.
- **Responsive Design**: Modern, glassmorphism-inspired dark mode aesthetic.

## Tech Stack

- **Backend**: Django 6.0+
- **Database**: SQLite (default)
- **Testing**: Pytest, Pytest-Django, Pytest-Cov
- **Frontend**: HTML, CSS, JavaScript (AJAX)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Installation

1. **Navigate to the project directory**:

   ```bash
   cd e:\Sem-8\Maxgen\Django\electro
   ```

2. **Create and activate a virtual environment** (recommended):

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Apply database migrations**:

   ```bash
   cd myproject
   python manage.py migrate
   ```

5. **Run the development server**:

   ```bash
   python manage.py runserver
   ```

   Open your browser and navigate to `http://127.0.0.1:8000/`.

## Testing

This project uses **pytest** for automated testing and coverage reporting.

1. **Run tests via Command Line**:
   ```bash
   # From the project root
   pytest
   ```

2. **Run tests via Admin Panel**:
   - Log in to the **Site Admin** dashboard (`/admin/login/`).
   - Navigate to **"Pytest Reports"** in the sidebar.
   - Click **"Run Tests"** to initiate the live streaming test engine and view the visual coverage report.


## Project Structure

- `myproject/`: Main Django project container.
  - `manage.py`: Django's command-line utility.
  - `myapp/`: Main application containing:
    - `models.py`: Database models (e.g., Customer).
    - `views.py`: Application logic and route handlers.
    - `templates/`: HTML templates for the UI.
  - `myproject/`: Project-level settings and configuration.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
