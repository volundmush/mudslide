"""
The base Command class.

All commands in Evennia inherit from the 'Command' class in this module.

"""
import re
import inspect

from mudslide.utils.locks import LockHandler
from honahlee.utils.misc import is_iter, lazy_property, make_iter
from mudslide.utils.misc import fill


def _init_command(cls, **kwargs):
    """
    Helper command.
    Makes sure all data are stored as lowercase and
    do checking on all properties that should be in list form.
    Sets up locks to be more forgiving. This is used both by the metaclass
    and (optionally) at instantiation time.

    If kwargs are given, these are set as instance-specific properties
    on the command - but note that the Command instance is *re-used* on a given
    host object, so a kwarg value set on the instance will *remain* on the instance
    for subsequent uses of that Command on that particular object.

    """
    for i in range(len(kwargs)):
        # used for dynamic creation of commands
        key, value = kwargs.popitem()
        setattr(cls, key, value)

    cls.key = cls.key.lower()
    if cls.aliases and not is_iter(cls.aliases):
        try:
            cls.aliases = [str(alias).strip().lower() for alias in cls.aliases.split(",")]
        except Exception:
            cls.aliases = []
    cls.aliases = list(set(alias for alias in cls.aliases if alias and alias != cls.key))

    # optimization - a set is much faster to match against than a list
    cls._matchset = set([cls.key] + cls.aliases)
    # optimization for looping over keys+aliases
    cls._keyaliases = tuple(cls._matchset)

    # by default we don't save the command between runs
    if not hasattr(cls, "save_for_next"):
        cls.save_for_next = False

    # pre-process locks as defined in class definition
    temp = []
    if hasattr(cls, "permissions"):
        cls.locks = cls.permissions
    if not hasattr(cls, "locks"):
        # default if one forgets to define completely
        cls.locks = "cmd:all()"
    if "cmd:" not in cls.locks:
        cls.locks = "cmd:all();" + cls.locks
    for lockstring in cls.locks.split(";"):
        if lockstring and ":" not in lockstring:
            lockstring = "cmd:%s" % lockstring
        temp.append(lockstring)
    cls.lock_storage = ";".join(temp)

    if hasattr(cls, "arg_regex") and isinstance(cls.arg_regex, str):
        cls.arg_regex = re.compile(r"%s" % cls.arg_regex, re.I + re.UNICODE)
    if not hasattr(cls, "auto_help"):
        cls.auto_help = True
    if not hasattr(cls, "is_exit"):
        cls.is_exit = False
    if not hasattr(cls, "help_category"):
        cls.help_category = "general"
    # make sure to pick up the parent's docstring if the child class is
    # missing one (important for auto-help)
    if cls.__doc__ is None:
        for parent_class in inspect.getmro(cls):
            if parent_class.__doc__ is not None:
                cls.__doc__ = parent_class.__doc__
                break
    cls.help_category = cls.help_category.lower()

    # pre-prepare a help index entry for quicker lookup
    cls.search_index_entry = {
        "key": cls.key,
        "aliases": " ".join(cls.aliases),
        "category": cls.help_category,
        "text": cls.__doc__,
        "tags": "",
    }


class CommandMeta(type):
    """
    The metaclass cleans up all properties on the class
    """

    def __init__(cls, *args, **kwargs):
        _init_command(cls, **kwargs)
        super().__init__(*args, **kwargs)


#    The Command class is the basic unit of an Evennia command; when
#    defining new commands, the admin subclass this class and
#    define their own parser method to handle the input. The
#    advantage of this is inheritage; commands that have similar
#    structure can parse the input string the same way, minimizing
#    parsing errors.


class Command(object, metaclass=CommandMeta):
    """
    Base command

    Usage:
      command [args]

    This is the base command class. Inherit from this
    to create new commands.

    The cmdhandler makes the following variables available to the
    command methods (so you can always assume them to be there):
    self.caller - the game object calling the command
    self.cmdstring - the command name used to trigger this command (allows
                     you to know which alias was used, for example)
    cmd.args - everything supplied to the command following the cmdstring
               (this is usually what is parsed in self.parse())
    cmd.cmdset - the cmdset from which this command was matched (useful only
                seldomly, notably for help-type commands, to create dynamic
                help entries and lists)
    cmd.obj - the object on which this command is defined. If a default command,
                 this is usually the same as caller.
    cmd.rawstring - the full raw string input, including any args and no parsing.

    The following class properties can/should be defined on your child class:

    key - identifier for command (e.g. "look")
    aliases - (optional) list of aliases (e.g. ["l", "loo"])
    locks - lock string (default is "cmd:all()")
    help_category - how to organize this help entry in help system
                    (default is "General")
    auto_help - defaults to True. Allows for turning off auto-help generation
    arg_regex - (optional) raw string regex defining how the argument part of
                the command should look in order to match for this command
                (e.g. must it be a space between cmdname and arg?)

    (Note that if auto_help is on, this initial string is also used by the
    system to create the help entry for the command, so it's a good idea to
    format it similar to this one).  This behavior can be changed by
    overriding the method 'get_help' of a command: by default, this
    method returns cmd.__doc__ (that is, this very docstring, or
    the docstring of your command).  You can, however, extend or
    replace this without disabling auto_help.
    """

    # the main way to call this command (e.g. 'look')
    key = "command"
    # alternative ways to call the command (e.g. 'l', 'glance', 'examine')
    aliases = []
    # a list of lock definitions on the form
    #   cmd:[NOT] func(args) [ AND|OR][ NOT] func2(args)
    locks = "cmd:all()"
    # used by the help system to group commands in lists.
    help_category = "General"
    # This allows to turn off auto-help entry creation for individual commands.
    auto_help = True

    # define the command not only by key but by the regex form of its arguments
    arg_regex = None

    # auto-set (by Evennia on command instantiation) are:
    #   obj - which object this command is defined on
    #   session - which session is responsible for triggering this command. Only set
    #             if triggered by an account.

    def __init__(self, **kwargs):
        """
        The lockhandler works the same as for objects.
        optional kwargs will be set as properties on the Command at runtime,
        overloading evential same-named class properties.

        """
        self.caller = None

        if kwargs:
            _init_command(self, **kwargs)

    @lazy_property
    def lockhandler(self):
        return LockHandler(self)

    def __str__(self):
        """
        Print the command key
        """
        return self.key

    def __eq__(self, cmd):
        """
        Compare two command instances to each other by matching their
        key and aliases.

        Args:
            cmd (Command or str): Allows for equating both Command
                objects and their keys.

        Returns:
            equal (bool): If the commands are equal or not.

        """
        try:
            # first assume input is a command (the most common case)
            return self._matchset.intersection(cmd._matchset)
        except AttributeError:
            # probably got a string
            return cmd in self._matchset

    def __hash__(self):
        """
        Python 3 requires that any class which implements __eq__ must also
        implement __hash__ and that the corresponding hashes for equivalent
        instances are themselves equivalent.

        Technically, the following implementation is only valid for comparison
        against other Commands, as our __eq__ supports comparison against
        str, too.

        """
        return hash("\n".join(self._matchset))

    def __ne__(self, cmd):
        """
        The logical negation of __eq__. Since this is one of the most
        called methods in Evennia (along with __eq__) we do some
        code-duplication here rather than issuing a method-lookup to
        __eq__.
        """
        try:
            return self._matchset.isdisjoint(cmd._matchset)
        except AttributeError:
            return cmd not in self._matchset

    def __contains__(self, query):
        """
        This implements searches like 'if query in cmd'. It's a fuzzy
        matching used by the help system, returning True if query can
        be found as a substring of the commands key or its aliases.

        Args:
            query (str): query to match against. Should be lower case.

        Returns:
            result (bool): Fuzzy matching result.

        """
        return any(query in keyalias for keyalias in self._keyaliases)

    def _optimize(self):
        """
        Optimize the key and aliases for lookups.
        """
        # optimization - a set is much faster to match against than a list
        self._matchset = set([self.key] + self.aliases)
        # optimization for looping over keys+aliases
        self._keyaliases = tuple(self._matchset)

    def set_key(self, new_key):
        """
        Update key.

        Args:
            new_key (str): The new key.

        Notes:
            This is necessary to use to make sure the optimization
            caches are properly updated as well.

        """
        self.key = new_key.lower()
        self._optimize()

    def set_aliases(self, new_aliases):
        """
        Replace aliases with new ones.

        Args:
            new_aliases (str or list): Either a ;-separated string
                or a list of aliases. These aliases will replace the
                existing ones, if any.

        Notes:
            This is necessary to use to make sure the optimization
            caches are properly updated as well.

        """
        if isinstance(new_aliases, str):
            new_aliases = new_aliases.split(";")
        aliases = (str(alias).strip().lower() for alias in make_iter(new_aliases))
        self.aliases = list(set(alias for alias in aliases if alias != self.key))
        self._optimize()

    def match(self, cmdname):
        """
        This is called by the system when searching the available commands,
        in order to determine if this is the one we wanted. cmdname was
        previously extracted from the raw string by the system.

        Args:
            cmdname (str): Always lowercase when reaching this point.

        Returns:
            result (bool): Match result.

        """
        return cmdname in self._matchset

    def access(self, srcobj, access_type="cmd", default=False):
        """
        This hook is called by the cmdhandler to determine if srcobj
        is allowed to execute this command. It should return a boolean
        value and is not normally something that need to be changed since
        it's using the Evennia permission system directly.

        Args:
            srcobj (Object): Object trying to gain permission
            access_type (str, optional): The lock type to check.
            default (bool, optional): The fallback result if no lock
                of matching `access_type` is found on this Command.

        """
        return self.lockhandler.check(srcobj, access_type, default=default)

    def msg(self, text=None, to_conn=None, from_conn=None, **kwargs):
        """
        This is a shortcut instead of calling msg() directly on an
        object - it will detect if caller is an Object or an Account and
        also appends self.session automatically if self.msg_all_sessions is False.

        Args:
            text (str, optional): Text string of message to send.
            to_obj (Object, optional): Target object of message. Defaults to self.caller.
            from_obj (Object, optional): Source of message. Defaults to to_obj.
            session (Session, optional): Supply data only to a unique
                session (ignores the value of `self.msg_all_sessions`).

        Keyword args:
            options (dict): Options to the protocol.
            any (any): All other keywords are interpreted as th
                name of send-instructions.

        """
        from_conn = from_conn or self.caller
        to_conn = to_conn or from_conn
        to_conn.msg(text=text, from_conn=from_conn, **kwargs)

    # Common Command hooks

    def at_pre_cmd(self):
        """
        This hook is called before self.parse() on all commands.  If
        this hook returns anything but False/None, the command
        sequence is aborted.

        """
        pass

    def at_post_cmd(self):
        """
        This hook is called after the command has finished executing
        (after self.func()).

        """
        pass

    def parse(self):
        """
        Once the cmdhandler has identified this as the command we
        want, this function is run. If many of your commands have a
        similar syntax (for example 'cmd arg1 = arg2') you should
        simply define this once and just let other commands of the
        same form inherit from this. See the docstring of this module
        for which object properties are available to use (notably
        self.args).

        """
        pass

    def get_command_info(self):
        """
        This is the default output of func() if no func() overload is done.
        Provided here as a separate method so that it can be called for debugging
        purposes when making commands.

        """
        variables = "\n".join(
            " |w{}|n ({}): {}".format(key, type(val), val) for key, val in self.__dict__.items()
        )
        string = f"""
Command {self} has no defined `func()` - showing on-command variables:
{variables}
        """
        # a simple test command to show the available properties
        string += "-" * 50
        string += "\n|w%s|n - Command variables from evennia:\n" % self.key
        string += "-" * 50
        string += "\nname of cmd (self.key): |w%s|n\n" % self.key
        string += "cmd aliases (self.aliases): |w%s|n\n" % self.aliases
        string += "cmd locks (self.locks): |w%s|n\n" % self.locks
        string += "help category (self.help_category): |w%s|n\n" % self.help_category.capitalize()
        string += "object calling (self.caller): |w%s|n\n" % self.caller
        string += "object storing cmdset (self.obj): |w%s|n\n" % self.obj
        string += "command string given (self.cmdstring): |w%s|n\n" % self.cmdstring
        # show cmdset.key instead of cmdset to shorten output
        string += fill(
            "current cmdset (self.cmdset): |w%s|n\n"
            % (self.cmdset.key if self.cmdset.key else self.cmdset.__class__)
        )

        self.caller.msg(string)

    def func(self):
        """
        This is the actual executing part of the command.  It is
        called directly after self.parse(). See the docstring of this
        module for which object properties are available (beyond those
        set in self.parse())

        """
        self.get_command_info()

    def get_extra_info(self, caller, **kwargs):
        """
        Display some extra information that may help distinguish this
        command from others, for instance, in a disambiguity prompt.

        If this command is a potential match in an ambiguous
        situation, one distinguishing feature may be its attachment to
        a nearby object, so we include this if available.

        Args:
            caller (TypedObject): The caller who typed an ambiguous
            term handed to the search function.

        Returns:
            A string with identifying information to disambiguate the
            object, conventionally with a preceding space.

        """
        if hasattr(self, "obj") and self.obj and self.obj != caller:
            return " (%s)" % self.obj.get_display_name(caller).strip()
        return ""

    def get_help(self, caller, cmdset):
        """
        Return the help message for this command and this caller.

        By default, return self.__doc__ (the docstring just under
        the class definition).  You can override this behavior,
        though, and even customize it depending on the caller, or other
        commands the caller can use.

        Args:
            caller (Object or Account): the caller asking for help on the command.
            cmdset (CmdSet): the command set (if you need additional commands).

        Returns:
            docstring (str): the help text to provide the caller for this command.

        """
        return self.__doc__


class InterruptCommand(Exception):
    """Cleanly interrupt a command."""

