class BaseEntity:
    app = None
    name_type = None
    access_modes = ()

    def __init__(self, model):
        self.model = model
        self.uuid = model.uuid
        self.name = model.name
        self.iname = model.iname
        self.pk = model.pk

    def setup(self):
        pass

    def rename(self, new_name):
        pass

    def owner(self):
        return self

    def access(self, accessor, perm):
        """
        Returns true if accessor entity has access in the given mode.
        """
        if self.owner() == accessor:
            return True
        if self.access_check(accessor, perm, True):
            return False
        return self.access_check(accessor, perm, False)

    def access_check(self, accessor, perm, deny):
        """
        Does the hard work of actually checking ACL's.
        """
        perms = set()
        srv_ent = self.app.services['entity']

        for entry in self.model.sacl_entries.filter(deny=deny):
            spec_ent = srv_ent.get_special(entry.grantee)
            if spec_ent.represents(accessor, entry.mode):
                perms += set([p.name for p in entry.permissions.all()])
                if perm in perms:
                    return True

        for entry in self.model.acl_entries.filter(deny=deny):
            ent = entry.grantee
            if ent.represents(accessor, entry.mode):
                perms += set([p.name for p in entry.permissions.all()])
                if perm in perms:
                    return True
        return False

    def represents(self, accessor, mode):
        """
        Returns true if this entity will answer for accessor in the given mode.
        """
        if not mode:
            return self.represents_NA(accessor)
        if not (meth := getattr(self, f"represents_{mode}", None)):
            return False
        return meth(accessor)

    def represents_NA(self, accessor):
        return accessor == self
