from . base import BaseEntity


class GameEntity(BaseEntity):
    name_type = 'game'
    access_modes = ('play', 'manage')

    def __init__(self, model):
        super().__init__(model)
        self.game_model = model.game_component
        self.game_key = self.game_model.game_key
