from django.db import transaction, IntegrityError
from honahlee.core import BaseService
from mudslide.models import Account
from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from channels.db import database_sync_to_async
from datetime import timedelta

class AccountService(BaseService):

    async def create_account(self, connection, username, password):
        await self.do_create_account(username, password)

    async def find_account(self, connection, username):
        pass

    @database_sync_to_async
    def do_create_account(self, username, password, email=None, entity=None):
        """
        This is called after all verification on username and password is done.
        """
        ent_srv = self.app.services['entity']
        cls = ent_srv.type_map['account']

        try:
            with transaction.atomic():
                if not entity:
                    entity = ent_srv.create_model('account', username)
                new_account = Account.objects.create(id=entity, username=username, password=make_password(password),
                                                     email=email, date_joined=entity.date_created,
                                                     total_playtime=timedelta())
                new_ent = cls(entity)
            ent_srv.register_entity(new_ent)
            return new_ent
        except IntegrityError as e:
            print(e)
            pass
