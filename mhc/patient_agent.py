import csv
import os

from matrx.agents import AgentBrain
from matrx.agents.agent_utils.navigator import Navigator
from matrx.agents.agent_utils.state_tracker import StateTracker
from matrx.messages import Message

from mhc.actions import AssignBed, UnassignBed
from mhc.sickness_model import SicknessModel
from json import JSONEncoder
import numpy as np


class PatientAgent(AgentBrain):

    def __init__(self,  move_speed=0, hospital_exit=None, deceased_fade_after_ticks=None, random_seed=0,
                 sickness_model_config=None, update_sickness_every_x_seconds=1, current_medical_care="eerste hulp"):
        super().__init__()
        self.bed_unassigning = False
        self.state_tracker = None

        # general for all patients
        self.move_speed = move_speed

        # keep track of to which bed we are assigned or intending to go to
        self.bed_requested = False
        self.target_bed_id = None
        self.target_location = None
        self.current_bed_id = None

        # the medical care the patient currently receives
        self.current_medical_care = current_medical_care

        # note where the exit is
        self.hospital_exit = hospital_exit
        assert isinstance(hospital_exit, list)

        # init the state tracker for navigation
        self.state_tracker = None

        # initiate our sickness model
        self.sickness_model = SicknessModel(config=sickness_model_config)
        self.update_sickness_every_x_seconds = update_sickness_every_x_seconds
        self.last_sickness_update = None

        # keep track of if we have passed away, and if so, at what tick
        self.tick_of_death = None
        self.deceased_fade_after_ticks = deceased_fade_after_ticks
        # an agent cannot remove itself, so send a message to the hospital_manager when deceased for removal
        self.removal_request_sent = False

        # set seed
        self.rnd_seed = random_seed

        # double check that patient assignment is correct with the last message
        self.assigned_to = None
        self.triaged = False

    def filter_observations(self, state):
        if self.state_tracker is None:
            # Initialize this agent's state tracker and navigator, has to be done here and not in the initialize
            # function, as that doesn'twork for agents created during the experiment.
            self.state_tracker = StateTracker(agent_id=self.agent_id)
            self.navigator = Navigator(self.agent_id, self.action_set, Navigator.A_STAR_ALGORITHM)

        # for navigator update state tracker
        self.state_tracker.update(state)

        # let the agent triage countdown go down with every tick (if we are in TDP 2 or 3)
        # and is not assigned to a person in TDP 2
        if 'countdown' in self.agent_properties:
            if self.agent_properties['assigned_to'] == 'robot':
                self.agent_properties['countdown'] = round(self.agent_properties['countdown'] - state['World']['tick_duration'], 1)

        # skip if we have passed away or fully recovered
        if self.agent_properties['health'] is not None and (self.agent_properties['health'] <= 0 or
                                                            self.agent_properties['health'] >= 100):
            return state

        # update our sickness and health every x seconds
        time = state['World']['nr_ticks'] * state['World']['tick_duration']
        settings = state[{'name': 'Settings'}]
        try:
            self.agent_properties['assigned_to'] = self.assigned_to;
        except:
            self.agent_properties['assigned_to'] = None;
        if self.last_sickness_update is None:
            self.update_sickness()
            # keep patient health static for 10s
            self.last_sickness_update = time + 10
        if self.last_sickness_update is None \
                or time >= (self.update_sickness_every_x_seconds + self.last_sickness_update):
            self.last_sickness_update = time
            self.update_sickness()

        # check if we have received any messages
        for message in self.received_messages.copy():

            # check if it is a user triage decision
            if isinstance(message.content, dict) \
                    and 'type' in message.content.keys() \
                    and message.content['type'] == "triage_decision":
                print(f"{self.agent_id} received user triage decision {message.content['decision']}")
                self.current_medical_care = message.content['decision']
                self.triaged = True

                self.agent_properties['triaged_by'] = message.content['triaged_by']
                self.received_messages.remove(message)

            # reset the triage counter if we receive a message to do so
            elif isinstance(message.content, dict) \
                    and 'type' in message.content.keys() \
                    and message.content['type'] == "reset_counter":
                self.agent_properties['countdown'] = message.content['counter_value']
                self.received_messages.remove(message)

            elif isinstance(message.content, dict) \
                    and 'type' in message.content.keys() \
                    and message.content['type'] == "reassign":
                self.assigned_to = message.content['assigned_to']
                self.agent_properties['assigned_to'] = message.content['assigned_to']
                self.assigned_to = message.content['assigned_to']

                # also reset counter
                self.agent_properties['countdown'] = self.agent_properties['original_countdown']
                self.received_messages.remove(message)

        return state


    def decide_on_action(self, state):
        action = None
        action_kwargs = {"action_duration": self.move_speed}

        # fetch info from state
        time = state['World']['nr_ticks'] * state['World']['tick_duration']
        settings = state[{"name": "Settings"}]
        timestamp = state[{"name"}]

        if self.agent_properties['patient_name'] == "Sybren":
            assign_to_real = self.agent_properties['assigned_to']
            assign_to_local = self.assigned_to
            pass

        # skip everything if we are waiting for removal of this agent
        if self.removal_request_sent:
            return action, action_kwargs

        if not self.current_medical_care == 'eerste hulp':
            self.agent_properties['triaged'] = True
        # request removal of the agent if we have arrived at the hospital exit
        if tuple(self.agent_properties['location']) == tuple(self.hospital_exit):
            # find the hospital_manager and request that it removes this agent
            hospital_manager = state[{"name": "hospital_manager"}]
            if self.agent_properties['health'] >= 100 or self.agent_properties['health'] <= 0:
                self.send_message(Message(content="agent_removal_request", from_id=self.agent_id,
                                          to_id=hospital_manager['obj_id']))
                self.removal_request_sent = True
            # set this agent to be traversable, so the pathplanning of other agents isn't blocked
            self.agent_properties['is_traversable'] = True
            self.agent_properties['triaged'] = True
            # print("Agent walked to exit, requesting disappearance")


        # check if this patient has passed away
        if self.agent_properties['health'] <= 0:
            # timestamp our tick of death
            if self.tick_of_death is None:
                self.tick_of_death = state['World']['nr_ticks']
                return None, {}

            # give the test subject to see that this patient has died, before removing the patient from the gridworld
            if (state['World']['nr_ticks'] - self.tick_of_death) > self.deceased_fade_after_ticks \
                    and not self.removal_request_sent:

                # find the hospital_manager and request that it removes this agent
                hospital_manager = state[{"name": "hospital_manager"}]
                self.send_message(Message(content="agent_removal_request", from_id=self.agent_id,
                                          to_id=hospital_manager['obj_id']))
                self.removal_request_sent = True

                return action, action_kwargs
            else:
                return action, action_kwargs


        # check if the patient has fully recovered
        elif self.agent_properties['health'] >= 100:

            if self.target_location is None or tuple(self.target_location) != tuple(self.hospital_exit):
                # reset the navigator
                self.navigator.reset_full()
                self.navigator.add_waypoint(tuple(self.hospital_exit))
                self.target_location = self.hospital_exit
                return self.unassign_self_bed(state, action_kwargs)


        # check if we need to find ourselves a new hospital bed that fits the assigned medical care
        # self.current_medical_care = currently assigned, self.agent_properties['medical_care'] is where our
        # agent is located at the moment
        elif self.agent_properties['medical_care'] != self.current_medical_care:
            # print("Self.medical care is not self.current medical care")

            # navigate to the door
            if self.current_medical_care == "huis":
                self.navigator.reset_full()
                self.navigator.add_waypoint(tuple(self.hospital_exit))
                self.target_location = self.hospital_exit
                self.agent_properties['medical_care'] = self.current_medical_care

                return self.unassign_self_bed(state, action_kwargs)
            else:
                return self.assign_self_free_bed(state, action_kwargs)

        # navigate to our bed / target location if we are not done yet
        if not self.navigator.is_done and len(self.navigator.get_all_waypoints()) > 0:
            action = self.navigator.get_move_action(self.state_tracker)
            # print("Doing navigation action:", action)


        return action, action_kwargs


    def _set_messages(self, messages=None):
        """
        Tweak to the standard MATRX function, such that the complete message is passed, instead of only the content
        """
        # Loop through all messages and create a Message object out of the dictionaries.
        for mssg in messages:

            # Add the message object to the received messages
            self.received_messages.append(mssg)

    def assign_self_free_bed(self, state, action_kwargs):
        """ Fix the assignment of a new hospital bed, fitting for our required medical care """
        action = None

        # Find a free bed to go to if the patient has none assigned yet
        if not self.bed_requested:
            # find a free bed
            self.target_bed_id, self.target_bed_loc = self.find_free_bed(state)
            # print(f"{self.agent_id} requesting bed {self.target_bed_id} for medical care "
            #       f"{self.current_medical_care}")

            # try to assign ourselves to that bed
            self.bed_requested = True
            action = AssignBed.__name__
            action_kwargs['object_id'] = self.target_bed_id


        # We requested a bed last tick, check if it succeeded
        elif self.bed_requested:

            # check if it our bed assignment has been approved, if so navigate to it
            if self.previous_action_result.succeeded:
                # assign our new bed and medical care
                self.bed_requested = False
                self.agent_properties['medical_care'] = self.current_medical_care
                self.current_bed_id = self.target_bed_id

                # navigate to it
                # print(f"{self.agent_id} assignment to bed {self.target_bed_id} was approved. Navigating to "
                #       f"{self.target_bed_loc}")
                self.navigator.reset_full()
                self.navigator.add_waypoint(tuple(self.target_bed_loc))

            # It might be that another agent tried to go to the same bed in the same tick.
            # If so, bed assignment failed. Retry another free bed
            else:
                # print(f"Agent {self.agent_id} requested bed {self.target_bed_id}, but assignment failed with reason "
                #       f"{self.previous_action_result.result}")
                # print(f"Trying new bed")
                self.target_bed_id, self.target_bed_loc = self.find_free_bed(state)

                # try to assign ourselves to that bed
                self.bed_requested = True
                action = AssignBed.__name__
                action_kwargs['object_id'] = self.target_bed_id

        return action, action_kwargs

    def unassign_self_bed(self, state, action_kwargs):

        action = None

        # Find a free bed to go to if the patient has none assigned yet
        if not self.bed_unassigning:
            # find a free bed
            self.bed_unassigning=True
            action = UnassignBed.__name__


        return action, action_kwargs

    def find_free_bed(self, state):
        """ Provided a type of medical care, find a free hospital bed intended for that care """

        # find free beds for the correct medical care
        beds = state[{'name': "Bed_top", 'room': self.current_medical_care, 'assigned_patient': 'free'}]

        bed = None
        # multiple beds found
        if isinstance(beds, list) and len(beds) > 0:
            # randomly choose one of the beds
            bed = np.random.choice(beds)
            # print("Chose bed :", bed['obj_id'])

        # only 1 bed found
        elif beds is not None:
            bed = beds

        # no beds found
        else:
            raise Exception(f"Couldn't find a free hospital bed for {self.agent_id} for ward "
                            f"{self.current_medical_care}")

        # return the ID and location

        return bed['obj_id'], bed['location']



    def update_sickness(self):
        """ Update the health of the current patient """

        result = self.sickness_model.update_sickness(health=self.agent_properties['health'],
                                                     symptoms=self.agent_properties['symptoms'],
                                                     symptoms_start=self.agent_properties['symptoms_start'],
                                                     fitness=self.agent_properties['fitness'],
                                                     medical_care=self.current_medical_care,
                                                     patient_medical_offsets=self.agent_properties['patient_medical_offsets'])

        # print(f"Updated sickness and health of {self.agent_id}. Health {self.agent_properties['health']}->{result[0]} and symptoms {self.agent_properties['symptoms']}->{result[1]}")

        # set the results
        [self.agent_properties['health'], self.agent_properties['symptoms']] = result

