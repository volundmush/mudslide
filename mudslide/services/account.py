from django.db import transaction, IntegrityError
from honahlee.core import BaseService, BaseBackend
from mudslide.models import Account
from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from channels.db import database_sync_to_async
from datetime import timedelta


class AccountService(BaseService):
    backend_key = 'account'

    async def create_account(self, connection, username, password):
        return await self.backend.async_create_account(username, password)

    async def rename_account(self, session, account, new_name, ignore_priv=False):
        if not (enactor := session.get_account()) or (not ignore_priv and not enactor.check_lock("pperm(Admin)")):
            raise ValueError("Permission denied.")
        account = self.find_account(account)
        old_name, new_name = self.backend.rename_account(account, new_name)
        entities = {'enactor': enactor, 'account': account}
        amsg.RenameMessage(entities, old_name=old_name).send()

    async def email_account(self, session, account, new_email, ignore_priv=False):
        if not (enactor := session.get_account()) or (not ignore_priv and not enactor.check_lock("pperm(Admin)")):
            raise ValueError("Permission denied.")
        account = self.find_account(account)
        old_email, new_email = self.backend.change_email(account, new_email)
        entities = {'enactor': enactor, 'account': account}
        amsg.EmailMessage(entities, old_email=old_email).send()

    async def find_account(self, search_text, exact=False):
        return self.backend.find_account(search_text, exact=exact)


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
