import pytest
from io import StringIO
from django.core.management import call_command
from django.contrib.auth.models import User
from myapp.models import SiteAdmin, Product, Customer, Order, Category, Brand
from unittest.mock import patch

@pytest.mark.django_db
class TestManagementCommands:
    def test_create_site_admin_success(self):
        out = StringIO()
        call_command('create_site_admin', 'newadmin', 'admin@test.com', 'password123', stdout=out)
        
        # Verify user created
        user = User.objects.get(username='newadmin')
        assert user.email == 'admin@test.com'
        assert user.check_password('password123')
        
        # Verify profile created
        assert SiteAdmin.objects.filter(user=user).exists()
        assert "Successfully created site admin" in out.getvalue()

    def test_create_site_admin_duplicate(self):
        User.objects.create_user('existing', 'e@test.com', 'p')
        out = StringIO()
        call_command('create_site_admin', 'existing', 'e2@test.com', 'p2', stdout=out)
        
        assert "already exists" in out.getvalue()
        # Verify no second user or profile
        assert User.objects.filter(username='existing').count() == 1

    @patch('django.contrib.auth.models.UserManager.create_user')
    def test_create_site_admin_failure(self, mock_create):
        mock_create.side_effect = Exception("Database Down")
        out = StringIO()
        call_command('create_site_admin', 'failuser', 'f@t.com', 'p', stdout=out)
        
        assert "Crucial failure: Database Down" in out.getvalue()

    @patch('myapp.management.commands.reset_db.call_command')
    def test_reset_db_command(self, mock_call):
        # We mock migrate and flush to avoid actual DB wipe during other tests 
        # (though django_db handles it, it's safer and faster)
        # But we want to test the data creation logic inside handle()
        
        out = StringIO()
        # To test the whole thing, we'd need to let it run.
        # Let's mock only migrate and flush.
        def side_effect(command_name, *args, **kwargs):
            if command_name in ['migrate', 'flush']:
                return None
            # For others, we might want them to run, but reset_db calls itself via call_command? 
            # No, it calls migrate and flush.
        
        mock_call.side_effect = side_effect
        
        call_command('reset_db', stdout=out)
        
        # Verify data creation
        assert Customer.objects.count() == 5
        assert Category.objects.count() > 0
        assert Brand.objects.count() > 0
        assert User.objects.filter(username='admin').exists()
        assert "DATABASE RESET" in out.getvalue()

@pytest.mark.django_db
def test_reset_db_root_script():
    """Test the root reset_db.py script via mocking."""
    import sys
    import os
    # Append root to path to import reset_db
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
        
    import reset_db
    
    with patch('subprocess.run') as mock_run, \
         patch('os.chdir') as mock_chdir:
        
        reset_db.run_reset_db()
        
        assert mock_chdir.called
        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert 'manage.py' in args
        assert 'reset_db' in args

    # Test error handling
    with patch('subprocess.run') as mock_run, \
         patch('os.chdir'), \
         patch('sys.exit') as mock_exit:
        
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'cmd')
        
        reset_db.run_reset_db()
        assert mock_exit.called
