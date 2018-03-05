
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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    args.insert(0, 'manage.py')
    execute_from_command_line(argv=args)


if __name__ == "__main__":
    execute()
