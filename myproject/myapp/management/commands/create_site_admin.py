from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myapp.models import SiteAdmin
from django.db import transaction

class Command(BaseCommand):
    help = 'Creates a new Site Admin user with a corresponding profile and hashed password.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Admin username')
        parser.add_argument('email', type=str, help='Admin email address')
        parser.add_argument('password', type=str, help='Admin password')

    def handle(self, *args, **options):
        username = options['username']
        email    = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"Error: User '{username}' already exists."))
            return

        try:
            with transaction.atomic():
                # passwords must be hashed using Django's default hasher
                user = User.objects.create_user(username=username, email=email, password=password)
                SiteAdmin.objects.create(user=user)
            
            self.stdout.write(self.style.SUCCESS(f"Successfully created site admin: {username}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Crucial failure: {str(e)}"))
