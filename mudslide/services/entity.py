from asgiref.sync import async_to_sync

from honahlee.core import BaseService
from mudslide.models import Entity, EntityType
from honahlee.utils.misc import fresh_uuid4
from mudslide.utils.ansi import ANSIString
from mudslide.entities.base import BaseEntity

import datetime
import pytz


class EntityService(BaseService):

    def __init__(self):
        self.uuid_map = dict()
        self.id_map = dict()
        self.type_map = dict()

    def register_entity(self, ent):
        self.uuid_map[ent.uuid] = ent
        self.id_map[ent.pk] = ent

    def setup(self):
        self.type_map = self.app.classes['entities']

        for entmod in Entity.objects.all():
            cls = self.type_map.get(entmod.entity_type.name, BaseEntity)
            new_ent = cls(entmod)
            self.register_entity(new_ent)
        for ent in self.id_map.values():
            ent.setup()

    def generate_uuid(self):
        return fresh_uuid4(self.uuid_map.keys())

    def create_model(self, entity_type, name, uuid=None, date_created=None, save=True):
        if entity_type not in self.type_map:
            raise ValueError(f"Unknown type: {entity_type}")
        en_type, created = EntityType.objects.get_or_create(name=entity_type)
        if created:
            en_type.save()
        if date_created is None:
            date_created = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if uuid is None:
            uuid = self.generate_uuid()
        else:
            if uuid in self.uuid_map:
                raise ValueError("UUID conflicts with existing entity!")
        name = self.sanitize_name(name)
        new_entity = Entity(uuid=uuid, entity_type=en_type, date_created=date_created, name=name,
                            iname=name.lower())
        if save:
            new_entity.save()
        return new_entity

    def sanitize_name(self, name):
        name = ANSIString(name).clean()
        name = name.strip()
        return name
