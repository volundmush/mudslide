from mudslide.commands.base import Command


class AdministrationCommand(Command):
    command_category = '- Prefix Commands'
    help_category = "Account Management"
    service_key = 'account'


class CmdAccount(AdministrationCommand):
    """
    General command for controlling game accounts.
    Note that <account> accepts either username or email address.

    Usage:
        -account [<account>]
            Display a breakdown of information all about an Account.
            Your own, if not targeted.

        -account/list
            Show all accounts in the system.

        -account/create <username>=<password>
            Create a new account.

        -account/disable <account>=<reason>
            Indefinitely disable an Account. The stated reason will be shown
            to staff and the account. If the account is currently online,
            it will be booted.
            Use -account/enable <account> to re-enable the account.

        -account/ban <account>=<duration>,<reason>
            Temporarily disable an account until the timer's up. <duration>
            must be a time period such as 7d (7 days), 2w (2 weeks), etc.
            Reason will be shown to the account and staff and recorded.
            Use -account/unban <account> to lift it early.

        -account/rename <account>=<new name>
            Change an account's Username.

        -account/email <account>=<new email>
            Change an Account's email address.

        -account/password <account>=<new password>
            Re-set an Account's password.

        -account/boot <account>=<reason>
            Forcibly disconnect an Account.
    """
    name = '-account'

    func_options = {
        None: {'usage': "-account [<account>]"},
        'list': {'usage': '-account/list'},
        'create': {'usage': '-account/create <username>=<password>'},
        'disable': {'usage': '-account/disable <account>=<reason>'},
        'enable': {'usage': '-account/enable <account>'},
        'rename': {'usage': '-account/rename <account>=<new name>'},
        'ban': {'usage': '-account/ban <account>=<duration>,<reason>'},
        'unban': {'usage': '-account/unban <account>'},
        'password': {'usage': '-account/password <account>=<new password>'},
        'email': {'usage': '-account/email <account>=<new email>'},
        'boot': {'usage': '-account/boot <account>=<reason>'}
    }

    async def func(self):
        if not self.args:
            self.args = self.caller
        self.msg(self.service.examine_account(self.caller, self.args))

    async def func_list(self):
        self.msg(self.service.list_accounts(self.caller))

    async def func_create(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.create_account(self.caller, self.lhs, self.rhs)

    async def func_disable(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.disable_account(self.caller, self.lhs, self.rhs)

    async def func_enable(self):
        self.service.enable_account(self.caller, self.lhs)

    async def func_password(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.password_account(self.caller, self.lhs, self.rhs)

    async def func_email(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.email_account(self.caller, self.lhs, self.rhs)

    async def func_boot(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.disconnect_account(self.caller, self.lhs, self.rhs)


class CmdAccess(AdministrationCommand):
    """
    Displays and manages information about Account access permissions.

    Usage:
        @access [<account>]
            Show the target's access details. Your own, if none is provided.

        @access/grant <account>=<permission>
            Grant an Evennia Permission to an Account.
            Use @access/revoke <account>=<permission> to remove it.

        @access/all
            Displays all grantable normal Permissions and their descriptions.

        @access/directory
            Display all managed Permissions and which Accounts hold them.
            Could be very spammy.

        @access/super <account>=SUPER DUPER
            Promote an Account to Superuser status. Use again to demote.
            Silly verification string required for accident prevention.
            |rDANGEROUS.|n
    """
    key = "@access"
    locks = "cmd:pperm(Helper)"
    func_rules = {
        'directory': dict(),
        'super': {
            'syntax': "<account>=SUPER DUPER",
            'lhs_req': True,
            'rhs_req': True
        },
        'grant': {
            'syntax': "<account>=<permission>",
            'lhs_req': True,
            'rhs_req': True
        },
        'all': dict(),
        'revoke': {
            'syntax': '<account>=<permission>',
            'lhs_req': True,
            'rhs_req': True
        }
    }
    func_options = ['directory', 'super', 'grant', 'all', 'revoke']

    async def func(self):
        account = self.args if self.args else self.account
        self.msg(self.service.access_account(self.caller, account))

    async def func_grant(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.grant_permission(self.caller, self.lhs, self.rhs)

    async def func_revoke(self):
        if not self.rhs and self.lhs:
            self.syntax_error()
        self.service.revoke_permission(self.caller, self.lhs, self.rhs)

    async def func_super(self):
        if not (self.rhs and self.lhs) and self.rhs == "SUPER DUPER":
            self.syntax_error()
        self.service.toggle_super(self.caller, self.lhs)

    async def func_all(self):
        self.msg(self.service.list_permissions(self.caller))

    async def func_directory(self):
        self.msg(self.service.permissions_directory(self.caller))


class CmdCharacter(AdministrationCommand):
    """
    General character administration command.

    Usage:
        @character <character>
            Examines a character and displays details.

        @character/list
            Lists all characters.

        @character/create <account>=<character name>
            Creates a new character for <account>.

        @character/rename <character>=<new name>
            Renames a character.

        @character/puppet <character>
            Takes control of a character that you don't own.

        @character/transfer <character>=<new account>
            Transfers a character to a different account.

        @character/archive <character>=<verify name>
            Archives / soft-deletes a character. They still exist for
            database purposes, but can no longer be used. Archived characters
            still have names, but the names  are freed for use.

        @character/restore <character>[=<new name>]
            Archived characters CAN be brought back into play. If the namespace
            already has re-used the character name, a new alternate name can be
            provided. This command is special and can only search archived
            characters. You may need to target them by #DBREF instead of their
            name if there are multiple matches.

        @character/old
            List all archived characters.
    """
    key = '@character'
    locks = "cmd:pperm(Helper)"
    func_options = ('create', 'archive', 'restore', 'rename', 'list',  'puppet', 'transfer', 'old')
    controller_key = 'character'
    func_rules = {
        'create': "<account>=<character name>",
        'archive': '<character>',
        'restore': '<character>[=<new name>]',
        'rename': '<character>=<new name>',
        'puppet': '<character>',
        'transfer': '<character>=<new account>'
    }

    async def func(self):
        self.msg(self.service.examine_character(self.caller, self.args))

    async def func_create(self):
        self.service.create_character(self.caller, self.lhs, self.rhs)

    async def func_restore(self):
        self.service.restore_character(self.caller, self.lhs, self.rhs)

    async def func_archive(self):
        self.service.archive_character(self.caller, self.lhs, self.rhs)

    async def func_puppet(self):
        self.service.puppet_character(self.caller, self.args)

    async def func_rename(self):
        self.service.rename_character(self.caller, self.lhs, self.rhs)

    async def func_transfer(self):
        self.service.transfer_character(self.caller, self.lhs, self.rhs)

    async def func_old(self):
        self.msg(self.service.list_characters(self.caller, archived=True))

    async def func_list(self):
        self.msg(self.service.list_characters(self.caller))


class _CmdAcl(UnixCommand):
    locks = "cmd:all()"

    @property
    def controller(self):
        return athanor.api().get('controller_manager').get('access')

    def init_parser(self):
        self.parser.add_argument("resource", action='store', nargs=1,
                                 help="The resource being operated on. Addressed as TYPE:THINGNAME.")


class _ModAcl(_CmdAcl):

    def init_parser(self):
        super().init_parser()
        self.parser.add_argument("-s", "--subjects", action='store', nargs='+', required=True,
                                 help="The entity(ies) having permissions added/removed to/from. Addressed as TYPE:THINGNAME")
        self.parser.add_argument("-p", "--permissions", action='store', nargs='+', required=True,
                                 help="The permissions being added/removed to the Subjects. These are words like 'read' or 'write'.")
        self.parser.add_argument("-d", "--deny", action="store_true", required=False,
                                 help="Modify Deny entries. Deny entries override Allows.")


class CmdAddAcl(_ModAcl):
    key = 'addacl'

    async def func(self):
        pass


class CmdRemAcl(_ModAcl):
    key = 'remacl'

    async def func(self):
        pass


class CmdGetAcl(_CmdAcl):
    key = 'getacl'

    async def func(self):
        obj = self.service.find_resource(self.caller, self.opts.resource[0])
        self.msg(f"I FOUND: {obj}")
