from climate.config.config import WEB_CONFIG


def execute(args: list = None):
    """
        Executes the Django management class.
        :param args: Arguments that are directly passed to the Django management class. There is no need to pass
                     "manage.py" inside the argument list. It is automatically added.
    """
    import os
    from django.core.management import execute_from_command_line
    from utilities.postgres_util import import_psycopg2

    # This is required to work with PyPy.
    import_psycopg2()
    # Actual execution
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    execute_from_command_line(argv=args)


def create_superuser() -> bool:
    from django.contrib.auth.models import User
    from climate.validators import validate_credentials
    from os import environ

    username, password = validate_credentials(environ.get(WEB_CONFIG['SUPERUSER_USERNAME']),
                                              environ.get(WEB_CONFIG['SUPERUSER_PASSWORD']))
    try:
        if User.objects.filter(username=username).exists():
            return True  # Superuser already exists
        superuser = User(username=username)
        superuser.set_password(raw_password=password)
        superuser.is_staff = True
        superuser.is_superuser = True
        superuser.save()
        return True
    except Exception as e:
        return False


if __name__ == "__main__":
    import sys

    execute(sys.argv)
