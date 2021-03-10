from matrx.actions import RemoveObject
from matrx.agents import AgentBrain

from mhc.actions import RemovePatient


class HospitalManager(AgentBrain):
    """ Simple agent that removes patients that have passed away or have completely healed """

    def __init__(self):
        super().__init__()

        self.removal_queue = []

    def filter_observations(self, state):
        """ process all request messages """
        for message in self.received_messages.copy():

            if message.content == "agent_removal_request":
                self.removal_queue.append(message.from_id)
                self.received_messages.remove(message)

        return state

    def decide_on_action(self, state):
        action = None
        action_kwargs = {}

        # remove the first patient from the queue and the gridworld
        if len(self.removal_queue) > 0:
            action_kwargs['object_id'] = self.removal_queue.pop(0)
            action = RemovePatient.__name__
            print(f"Removing agent {action_kwargs['object_id']} with name {state[action_kwargs['object_id']]['patient_name']} from gridworld")

        return action, action_kwargs

    def _set_messages(self, messages=None):
        """
        Tweak to the standard MATRX function, such that the complete message is passed, instead of only the content
        """
        # Loop through all messages and create a Message object out of the dictionaries.
        for mssg in messages:

            # Add the message object to the received messages
            self.received_messages.append(mssg)