from . base import BaseEntity


class AccountEntity(BaseEntity):
    name_type = 'account'

    def __init__(self, model):
        super().__init__(model)
        self.account_model = model.account_component

    def rename(self, new_name):
        """
        Account Entities also have to rename the Account
        model.
        """
        pass

    def is_staff(self):
        return self.account_model.is_staff or self.is_superuser()

    def is_superuser(self):
        return self.account_model.is_superuser
