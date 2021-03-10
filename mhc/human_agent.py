from matrx.agents import HumanAgentBrain


class HumanDoctor(HumanAgentBrain):
    """ Creates an Human Agent which is an agent that can be controlled by a human.
    """

    def __init__(self):
        """ Creates an Human Agent which is an agent that can be controlled by a human.
        """
        super().__init__()


    def initialize(self):
        pass

    def filter_observations(self, state):
        return state


    def decide_on_action(self, state, user_input):
        action = None
        action_kwargs = {}

        return action, action_kwargs


    # we don't the context menu, so have it return nothing
    def create_context_menu_for_self(self, clicked_object_id, click_location, self_selected):
        return {}

    def create_context_menu_for_other(self, agent_id_who_clicked, clicked_object_id, click_location):
        return {}