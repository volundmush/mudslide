from honahlee.core import BaseService
from mudslide.models import GameEntry


class GameService(BaseService):

    def __init__(self):
        self.game_keys = dict()

    def setup(self):
        srv_ent = self.app.services['entity']

        for entry in GameEntry.objects.all():
            if (found := srv_ent.uuid_map.get(entry.entity.uuid, None)):
                self.register_entity(found)

    def register_entity(self, ent):
        self.game_keys[ent.game_key] = ent
