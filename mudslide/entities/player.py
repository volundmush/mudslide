from . base import BaseEntity


class PlayerEntity(BaseEntity):
    name_type = 'player'

    def __init__(self, model):
        super().__init__(model)
        self.player_model = model.player_component
        self.player_key = self.player_model.player_key
