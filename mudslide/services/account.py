from django.db import transaction, IntegrityError
from honahlee.core import BaseService, BaseBackend
from mudslide.models import Account
from honahlee.utils.time import duration_from_string, utcnow
from mudslide.utils.text import partial_match, iter_to_string
from honahlee.utils.misc import make_iter

from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from channels.db import database_sync_to_async
from datetime import timedelta


class AccountService(BaseService):
    backend_key = 'account'

    async def create_account(self, connection, username, password):
        account = await self.backend.async_create_account(username, password)
        self.app.config.logs['application'].info(f"CONNECTION: {connection} - Account Created: {account}")
        return account

    async def rename_account(self, connection, account, new_name, exact=False, ignore_priv=False):
        if not (enactor := connection.get_account()) or (not ignore_priv and not enactor.check_lock("pperm(Admin)")):
            raise ValueError("Permission denied.")
        account = await self.find_account(account, exact=exact)
        old_name, new_name = self.backend.rename_account(account, new_name)
        entities = {'enactor': enactor, 'account': account}
        # amsg.RenameMessage(entities, old_name=old_name).send()

    async def email_account(self, connection, account, new_email, ignore_priv=False):
        if not (enactor := connection.get_account()) or (not ignore_priv and not enactor.check_lock("pperm(Admin)")):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        old_email, new_email = self.backend.change_email(account, new_email)
        entities = {'enactor': enactor, 'account': account}
        # amsg.EmailMessage(entities, old_email=old_email).send()

    async def find_account(self, search_text, exact=False):
        return await self.backend.find_account(search_text, exact=exact)

    async def disable_account(self, session, account, reason):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Admin)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        if account.db._disabled:
            raise ValueError("Account is already disabled!")
        if not reason:
            raise ValueError("Must include a reason!")
        account.db._disabled = reason
        entities = {'enactor': enactor, 'account': account}
        # amsg.DisableMessage(entities, reason=reason).send()
        account.force_disconnect(reason)

    async def enable_account(self, session, account):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Admin)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        if not account.db._disabled:
            raise ValueError("Account is not disabled!")
        del account.db._disabled
        entities = {'enactor': enactor, 'account': account}
        # amsg.EnableMessage(entities).send()

    async def ban_account(self, session, account, duration, reason):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Moderator)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        duration = duration_from_string(duration)
        ban_date = utcnow() + duration
        if not reason:
            raise ValueError("Must include a reason!")
        account.db._banned = ban_date
        account.db._ban_reason = reason
        entities = {'enactor': enactor, 'account': account}
        # amsg.BanMessage(entities, duration=time_format(duration.total_seconds(), style=2),
                        #ban_date=ban_date.strftime('%c'), reason=reason).send()
        account.force_disconnect(reason)

    async def unban_account(self, session, account):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Moderator)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        if not ((banned := account.db._banned) and banned > utcnow()):
            raise ValueError("Account is not banned!")
        del account.db._banned
        del account.db._ban_reason
        entities = {'enactor': enactor, 'account': account}
        # amsg.UnBanMessage(entities).send()

    async def password_account(self, session, account, new_password, ignore_priv=False, old_password=None):
        if not (enactor := session.get_account()) or (not ignore_priv and not enactor.check_lock("oper(account_password)")):
            raise ValueError("Permission denied.")
        if ignore_priv and not account.check_password(old_password):
            raise ValueError("Permission denied. Password was incorrect.")
        account = await self.find_account(account)
        if not new_password:
            raise ValueError("Passwords may not be empty!")
        account.set_password(new_password)
        account.db._date_password_changed = utcnow()
        entities = {'enactor': enactor, 'account': account}
        if old_password:
            pass
            # amsg.PasswordMessagePrivate(entities).send()
        else:
            pass
            # amsg.PasswordMessageAdmin(entities, password=new_password).send()

    async def disconnect_account(self, session, account, reason):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Moderator)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        if not account.sessions.all():
            raise ValueError("Account is not connected!")
        entities = {'enactor': enactor, 'account': account}
        # amsg.ForceDisconnect(entities, reason=reason).send()
        account.force_disconnect(reason=reason)

    def find_permission(self, perm):
        if not perm:
            raise ValueError("No permission entered!")
        if not (found := partial_match(perm, settings.PERMISSIONS.keys())):
            raise ValueError("Permission not found!")
        return found

    async def grant_permission(self, session, account, perm):
        if not (enactor := session.get_account()):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        perm = self.find_permission(perm)
        perm_data = settings.PERMISSIONS.get(perm, dict())
        perm_lock = perm_data.get("permission", None)
        if not perm_lock:
            if not enactor.is_superuser:
                raise ValueError("Permission denied. Only a Superuser can grant this.")
        if perm_lock:
            passed = False
            for lock in make_iter(perm_lock):
                if (passed := enactor.check_lock(f"pperm({lock})")):
                    break
            if not passed:
                raise ValueError(f"Permission denied. Requires {perm_lock} or better.")
        if perm.lower() in account.permissions.all():
            raise ValueError(f"{account} already has that Permission!")
        account.permissions.add(perm)
        self.permissions[perm.lower()].add(account)
        entities = {'enactor': enactor, 'account': account}
        # amsg.GrantMessage(entities, perm=perm).send()

    async def revoke_permission(self, session, account, perm):
        if not (enactor := session.get_account()):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        perm = self.find_permission(perm)
        perm_data = settings.PERMISSIONS.get(perm, dict())
        perm_lock = perm_data.get("permission", None)
        if not perm_lock:
            if not enactor.is_superuser:
                raise ValueError("Permission denied. Only a Superuser can grant this.")
        if perm_lock:
            passed = False
            for lock in make_iter(perm_lock):
                if (passed := enactor.check_lock(f"pperm({lock})")):
                    break
            if not passed:
                raise ValueError(f"Permission denied. Requires {perm_lock} or better.")
        if perm.lower() not in account.permissions.all():
            raise ValueError(f"{account} does not have that Permission!")
        account.permissions.remove(perm)
        self.permissions[perm.lower()].remove(account)
        entities = {'enactor': enactor, 'account': account}
        # amsg.RevokeMessage(entities, perm=perm).send()

    async def toggle_super(self, session, account):
        if not (enactor := session.get_account()) or not enactor.is_superuser:
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        acc_super = account.is_superuser
        reverse = not acc_super
        entities = {'enactor': enactor, 'account': account}
        if acc_super:
            pass
            # amsg.RevokeSuperMessage(entities).send()
        else:
            pass
            # amsg.GrantSuperMessage(entities).send()
        account.is_superuser = reverse
        account.save(update_fields=['is_superuser'])
        if reverse:
            self.permissions["_super"].add(account)
        else:
            self.permissions["_super"].remove(account)
        return reverse

    async def access_account(self, session, account):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Admin)"):
            raise ValueError("Permission denied.")
        account = await self.find_account(account)
        styling = enactor.styler
        message = list()
        message.append(styling.styled_header(f"Access Levels: {account}"))
        message.append(f"PERMISSION HIERARCHY: {iter_to_string(settings.PERMISSION_HIERARCHY)} <<<< SUPERUSER")
        message.append(f"HELD PERMISSIONS: {iter_to_string(account.permissions.all())} ; SUPERUSER: {account.is_superuser}")
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    async def permissions_directory(self, session):
        if not (enactor := session.get_account()) or not enactor.check_lock("pperm(Admin)"):
            raise ValueError("Permission denied.")
        # Create a COPY of the permissions since we're going to mutilate it a lot...

        perms = dict(self.permissions)
        message = list()
        styling = enactor.styler
        message.append(styling.styled_header("Permissions Hierarchy"))
        message.append(f"|rSUPERUSERS:|n {iter_to_string(perms.pop('_super', list()))}")
        for perm in reversed(settings.PERMISSION_HIERARCHY):
            if perm.lower() in perms:
                message.append(f"{perm:>10}: {iter_to_string(perms.pop(perm.lower(), list()))}")
        if perms:
            message.append(styling.styled_separator("Non-Hierarchial Permissions"))
            for perm, holders in perms.items():
                if not holders:
                    continue
                message.append(f"{perm}: {iter_to_string(holders)}")
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    async def list_permissions(self, session):
        if not (enactor := session.get_account()):
            raise ValueError("Permission denied.")
        styling = enactor.styler
        message = list()
        message.append(styling.styled_header("Grantable Permissions"))
        for perm, data in settings.PERMISSIONS.items():
            message.append(styling.styled_separator(perm))
            message.append(f"Grantable By: {data.get('permission', 'SUPERUSER')}")
            if (desc := data.get("description", None)):
                message.append(f"Description: {desc}")
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    async def list_accounts(self, connection):
        if not (conn_account := connection.get_account()):
            raise ValueError("Permission denied.")
        if not conn_account.is_staff():
            raise ValueError("Permission denied.")
        if not (accounts := await self.all()):
            raise ValueError("No accounts to list!")
        message = list()
        if connection.uses_screenreader():
            pass
        else:
            styling = connection.styler
            message.append(styling.styled_header(f"Account Listing"))
            for acc in accounts:
                message.extend(acc.render_list_section(connection, styling))
            message.append(styling.styled_footer())
        return '\n'.join(str(l) for l in message)

    async def examine_account(self, connection, account):
        if not (conn_account := connection.get_account()):
            raise ValueError("Permission denied.")
        if isinstance(account, str):
            if conn_account.is_staff():
                account = await self.find_account(account)
            else:
                raise ValueError("Permission denied.")
        else:
            account = conn_account
        if connection.uses_screenreader():
            pass
        else:
            return account.render_examine(connection)

    async def all(self):
        return await self.backend.all()

    async def count(self):
        return await self.backend.count()


class AccountBackend(BaseBackend):

    def __init__(self, service):
        super().__init__(service)

    @database_sync_to_async
    def async_create_account(self, username, password, email=None, entity=None):
        return self.create_account(username, password, email, entity)

    def create_account(self, username, password, email=None, entity=None):
        """
        This is called after all verification on username and password is done.
        """
        ent_srv = self.app.services['entity']
        cls = ent_srv.type_map['account']

        try:
            with transaction.atomic():
                if not entity:
                    entity = ent_srv.create_model('account', username)
                Account.objects.create(id=entity, username=username, password=make_password(password),
                                                     email=email, date_joined=entity.date_created,
                                                     total_playtime=timedelta())
                new_ent = cls(entity)
            ent_srv.register_entity(new_ent)
            return new_ent
        except IntegrityError as e:
            print(e)
            pass
