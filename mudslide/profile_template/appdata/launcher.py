

def RunOperation(op, args, unknown_args):
    from . config import Config
    gameconf = Config()
    gameconf.setup()
    from django.core.management import call_command
    call_command(*([op] + unknown_args))
