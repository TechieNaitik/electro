# Electro

A Django-based E-commerce application.

## Features

- **User Authentication**: Custom customer registration, login system, and password reset via OTP.
- **Product Browsing**: Shop page with sorting/filtering, single product view, bestsellers, and dynamic inventory status.
- **Wishlist**: Per-user product saving system with AJAX-powered live updates and a dedicated wishlist management page.
- **Shopping Cart**: Interactive AJAX-powered cart with real-time updates and toast notifications.
- **Checkout Process**: Streamlined checkout flow with logical payment method selections.
- **Inventory Management**: Real-time stock validation and automatic stock deduction upon order completion.
- **Custom Site Administration**: A dedicated administration dashboard separate from the default Django admin, featuring key business statistics and streamlined store management tools.
- **Contact & Support**: Support pages and contact functionality.
- **Responsive Design**: Friendly interfaces with a premium aesthetic.

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
