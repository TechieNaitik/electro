# Electro

A Django-based E-commerce application.

## Features

- **User Authentication**: Custom customer registration, login system, and password reset via OTP.
- **Product Browsing**: Shop page with sorting/filtering, single product view, bestsellers, and dynamic inventory status.
- **Wishlist**: Per-user product saving system with AJAX-powered live updates and a dedicated wishlist management page.
- **Shopping Cart**: Interactive AJAX-powered cart with real-time updates and toast notifications.
- **One-Click Checkout**: Refactored checkout flow that pulls shipping and billing details directly from stored user profiles for maximum efficiency.
- **Centralized Profile Management**: Comprehensive user dashboard for managing all personal, contact, and address details in one place.
- **Inventory Management**: Real-time stock validation and automatic stock deduction upon order completion.
- **Custom Site Administration**: A premium, isolated administration dashboard (separate from Django-admin) featuring:
- **Dynamic Data Export**: Advanced administrative tools to export Customers, Orders, and Products into multiple professional formats (.pdf, .xlsx, .docx, .csv).
- **Security & Sessions**: Secure login wall with hashed passwords, brute-force protection, and independent admin session management.
- **Resource Management**: Complete CRUD operations for Products and Categories with instant search capability.
- **Inventory Insights**: Real-time stock alerts and business analytics/statistics.
- **Invoice Generation**: Pixel-perfect, downloadable A4 PDFs rendered via headless Playwright, featuring a luxury editorial layout.
- **Contact & Support**: Support pages and contact functionality.
- **Responsive Design**: Modern, glassmorphism-inspired dark mode aesthetic.

## Tech Stack

- **Backend**: Django 6.0+
- **Database**: SQLite (default)
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
