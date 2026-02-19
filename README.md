# Electro

A Django-based E-commerce application.

## Features

- **User Authentication**: Custom customer registration and login system.
- **Product Browsing**: Shop page, single product view, bestsellers.
- **Shopping Cart**: Cart management and checkout process.
- **Contact & Support**: Contact page.
- **Responsive Design**: Compatible with various devices.

## Tech Stack

- **Backend**: Django 6.0+
- **Database**: SQLite (default)
- **Frontend**: HTML, CSS (Django Templates)

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
