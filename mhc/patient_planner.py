import csv
import json
import os
import pandas as pd
import numpy as np

from matrx.actions import Action, ActionResult
from matrx.agents import AgentBrain, SenseCapability, np
from matrx.objects import AgentBody
import matrx.defaults as defaults

from mhc.patient_agent import PatientAgent
from mhc import sickness_model as SicknessModel


class PatientPlanner(AgentBrain):
    """ Planning and spawning of patient agents """

    def __init__(self, config, tdp):
        super().__init__()
        self.config = config
        self.patients_planning = config['patients']['patient_planning']

        # load the patient data file
        patients_data_file = os.path.join(os.path.realpath(self.config['patients']['patients_file']))
        self.patient_data = pd.read_csv(patients_data_file, sep=';')

        self.current_keypoint = None
        self.timestamp_next_patient_spawn = None

        # there might be a queue if the test subject is not triaging the patients quickly enough
        self.generated_patients = 0
        self.patient_spawn_queue = []
        self.spawned_patients = 0

        # new patients need a couple ticks to assign themselves to a free bed, so we have a short cooldown when spawning
        # patients
        self.spawn_cooldown = 0

        self.tdp = tdp

        # there are two entrances, use them in alternating order (so patients are not put on top of eachother)
        self.last_entrance_used = None


    def initialize(self):
        pass

    def filter_observations(self, state):
        return state

    def decide_on_action(self, state):
        action = None
        action_kwargs = {}

        # current time since start of experiment in seconds
        second = state['World']['tick_duration'] * state['World']['nr_ticks']

        # check at what keypoint in the patient planning we are
        current_keypoint = None
        for keypoint in self.patients_planning:
            if second > keypoint['second']:
                current_keypoint = keypoint

        # check if we need to add a patient (to the queue) this tick
        if current_keypoint != None and (self.spawned_patients + len(self.patient_spawn_queue)) < \
                self.config['patients']['max_patients']:

            # replan when we need to spawn the next patient if we have a new patient_spawn_speed
            if current_keypoint != self.current_keypoint or second > self.timestamp_next_patient_spawn:
                self.current_keypoint = current_keypoint

                # add a patient to the queue
                brain_args, body_args = self.get_next_patient()
                action_kwargs = {"brain_args": brain_args, "body_args": body_args}
                # action = AddPatientAgent.__name__
                self.patient_spawn_queue.append(action_kwargs)
                # print("Patient planner adding a new patient to the spawn queue")

                # plan when we need to spawn the next patient
                seconds_per_patient = 10000 if 'seconds_per_patient' not in current_keypoint else current_keypoint[
                    'seconds_per_patient']
                self.timestamp_next_patient_spawn = second + seconds_per_patient
                # print(f"Planned new patient for t {self.timestamp_next_patient_spawn}")

        # spawn a patient from the queue if there are any and there is a free first aid bed, we are not on cool down
        # and the entrance is clear
        # queue: because a person might be slower than the rate at which patients are generated
        # free first aid bed: a patient first goes to a free first aid bed, so it needs to be available
        # cooldown: patients assign themselves to (first aid) beds, and need 2 ticks to do so. So we have a short
        #           cooldown in between patient spawning to give them and not book 2 patients to one bed
        # clear entrance: There are 2 entrances, one of them needs to be clear so we can spawn a patient there.
        if len(self.patient_spawn_queue) > 0 and self.get_free_firstaid_beds(state) > 0 and not self.spawn_cooldown > 0:

            # get patients in the first aid
            patients = state[{"is_patient": True, "medical_care": "eerste hulp"}]
            if patients is None:
                patients = []
            elif not isinstance(patients, list):
                patients = [patients]

            # check which entrance is free
            free_entrances = ['entrance', 'entrance2']
            for patient in patients:
                for entrance in free_entrances.copy():
                    if tuple(patient['location']) == tuple(self.config['hospital'][entrance]):
                        free_entrances.remove(entrance)

            # if there is a free entrance, spawn the patient at one of the free entrances
            if len(free_entrances) > 0:
                entrance = np.random.choice(free_entrances)
                # alternate between the two entrances if possible
                if len(free_entrances) > 1 and self.last_entrance_used is not None:
                    entrance = free_entrances[0] if free_entrances[0] is not self.last_entrance_used else free_entrances[1]
                self.last_entrance_used = entrance

                action_kwargs = self.patient_spawn_queue.pop(0)
                action_kwargs['body_args']['location'] = self.config['hospital'][entrance]

                action = AddPatientAgent.__name__
                time = state['World']['nr_ticks'] * state['World']['tick_duration']

                self.spawned_patients += 1

                print(f"Spawning patient at tick {state['World']['nr_ticks']}. Patient "
                      f"{self.spawned_patients} of max {self.config['patients']['max_patients']}")

                self.spawn_cooldown = 3
        else:
            self.spawn_cooldown -= 1

        return action, action_kwargs

    def get_next_patient(self):
        """ Generate a new patient """

        # get the data of this patient
        patient_number = self.spawned_patients + len(self.patient_spawn_queue)

        patient_data = self.patient_data.iloc[patient_number]

        # set a default patient image
        img = "patients/patient_unknown.png" if 'image' not in patient_data or patient_data['image'] == '' else \
            patient_data['image']

        # calculate the patient specific offset
        patient_medical_offsets = SicknessModel.init_patient_specific_offsets()

        # specify the agent brain props
        brain_args = {"move_speed": self.config['patients']['move_speed'],
                      "hospital_exit": self.config['hospital']['exit'],
                      "random_seed": self.config['random_seed'],
                      "sickness_model_config": self.config['sickness_model'],
                      "deceased_fade_after_ticks": self.config['patients']['deceased_fade_after_ticks'],
                      "update_sickness_every_x_seconds": self.config['patients']['update_sickness_every_x_seconds'],
                      "current_medical_care": "eerste hulp"}

        # create the agent body with default properties and some custom patient properties
        body_args = {"possible_actions": defaults.AGENTBODY_POSSIBLE_ACTIONS,
                     "callback_create_context_menu_for_self": None,
                     "visualize_size": defaults.AGENTBODY_VIS_SIZE,
                     "visualize_shape": defaults.AGENTBODY_VIS_SHAPE,
                     "visualize_colour": defaults.AGENTBODY_VIS_COLOUR,
                     "visualize_opacity": defaults.AGENTBODY_VIS_COLOUR,
                     "visualize_when_busy": defaults.AGENTBODY_VIS_COLOUR,
                     "visualize_depth": defaults.AGENTBODY_VIS_DEPTH,
                     "team": None,
                     "is_movable": False,
                     "is_human_agent": False,

                     # custom properties for patient agent
                     "location": self.config['hospital']['entrance'],
                     "current_bed_id": None,
                     "name": "patient",
                     "patient_name": patient_data['name'],
                     "number": self.generated_patients,
                     "is_traversable": False,
                     "img_name": img,
                     "customizable_properties": ['current_bed_id', 'symptoms', 'medical_care', "health",
                                                 "is_traversable", "triaged", "img_name", "patient_photo", "countdown",
                                                 "agent_planned_triage_decision", "triaged_by",
                                                 "agent_triage_decision_influences", "assigned_to"],

                     # patient data
                     "is_patient": True,
                     "gender": patient_data['gender'],
                     "age": int(patient_data['age']),
                     "profession": patient_data['profession'],
                     "symptoms": patient_data['symptoms'],
                     "symptoms_start": patient_data['symptoms'],
                     "fitness": patient_data['fitness'],
                     "home_situation": patient_data['home_situation'],
                     "medical_care": None,
                     "patient_photo": img,
                     "health": None,
                     "patient_medical_offsets": patient_medical_offsets,
                     "patient_introduction_text": patient_data['description'],
                     "triaged": False,
                     "triaged_by": None,
                     "assigned_to": None,

                     # triage agent actions on patient
                     # the care the patient is
                     "agent_planned_triage_decision": None,
                     "agent_triage_decision_influences": None
                     }

        # add decision support info for decision support trials
        if self.tdp == "tdp_decision_support":
            # add data for the decision support prediction to the agent (if present in the dataset)
            for dss_var_num in ["survival_eerste_hulp", "std_survival_eerste_hulp",
                                "survival_huis", "std_survival_huis", "survival_ziekenboeg",
                                "std_survival_ziekenboeg", "survival_IC", "std_survival_IC",
                                "opnameduur_eerste_hulp", "std_opnameduur_eerste_hulp",
                                "opnameduur_huis", "std_opnameduur_huis", "opnameduur_ziekenboeg",
                                "std_opnameduur_ziekenboeg", "opnameduur_IC", "std_opnameduur_IC",
                                "remaining_life_years"]:
                if dss_var_num in patient_data:
                    body_args[dss_var_num] = round(float(patient_data[dss_var_num]), 2)

            # add string dss var
            for dss_var_str in ["care_suggestion_unbiased", "care_suggestion_biased"]:
                if dss_var_str in patient_data:
                    body_args[dss_var_str] = patient_data[dss_var_str]

            body_args['remaining_life_years_std'] = 5


        # add decision support info for decision support with explanations for experiment 2 / 3 trials
        elif self.tdp == "tdp_decision_support_explained":

            # add data for the decision support prediction to the agent (if present in the dataset)
            for dss_var_num in ["survival_eerste_hulp", "std_survival_eerste_hulp",
                                "survival_huis", "std_survival_huis", "survival_ziekenboeg",
                                "std_survival_ziekenboeg", "survival_IC", "std_survival_IC",
                                "opnameduur_eerste_hulp", "std_opnameduur_eerste_hulp",
                                "opnameduur_huis", "std_opnameduur_huis", "opnameduur_ziekenboeg",
                                "std_opnameduur_ziekenboeg", "opnameduur_IC", "std_opnameduur_IC",
                                "remaining_life_years", "confidence"]:
                if dss_var_num in patient_data:
                    # some are provided in format '60%', should be in format 0.6.
                    if isinstance(patient_data[dss_var_num], str) and "%" in patient_data[dss_var_num]:
                        body_args[dss_var_num] = int(patient_data[dss_var_num].replace("%", "")) * 0.01

                    # round other values to 2 decimals
                    else:
                        body_args[dss_var_num] = round(float(patient_data[dss_var_num]), 2)

            # add string dss var
            for dss_var_str in ["care_suggestion", "confidence_explanation", "advice_explanation", "IC_foil",
                                "Ziekenboeg_foil", "Huis_foil"]:
                if dss_var_str in patient_data:
                    body_args[dss_var_str] = patient_data[dss_var_str]

            body_args['remaining_life_years_std'] = 5


        # for tdp 2, add a variable that makes it possible to compare patients to each other in the explanation,
        # in the case of uncertainty where patients are assigned to the human
        elif self.tdp == "tdp_dynamic_task_allocation":
            body_args['can_be_triaged_by_agent'] = True
            body_args['care_contending_patients'] = []
            body_args['customizable_properties'] += ['can_be_triaged_by_agent', 'care_contending_patients']


        if 'triage_countdown' in self.config:
            # the countdown that displays how long it wil take before the agent makes their triage decision final
            body_args["countdown"] = self.config['triage_countdown']
            # the original countdown, used by the frontend to display a progress bar of the correct size
            body_args["original_countdown"] = self.config['triage_countdown']

        print("Generating patient with medical offsets:", patient_medical_offsets)
        self.generated_patients += 1
        return brain_args, body_args

    def get_free_firstaid_beds(self, state):
        """ Counts how many first aid beds are free """
        n_beds = 0
        beds = state[{'name': "Bed_top", 'room': "eerste hulp", 'assigned_patient': 'free'}]

        if isinstance(beds, list):
            n_beds = len(beds)
        elif beds is not None:
            n_beds = 1

        # if n_beds > 0:
        #     print(f"Beds free ({n_beds}) at tick {state['World']['nr_ticks']}, spawning patients")
        #     print(beds)

        return n_beds


class AddPatientAgent(Action):
    """ An action that can add a patient agent to the gridworld """

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):

        # check that we have all variables
        if 'brain_args' not in kwargs:
            return AddObjectResult(AddObjectResult.NO_AGENTBRAIN, False)

        if 'body_args' not in kwargs:
            return AddObjectResult(AddObjectResult.NO_AGENTBODY, False)

        # success
        return AddObjectResult(AddObjectResult.ACTION_SUCCEEDED, True)

    def mutate(self, grid_world, agent_id, **kwargs):
        # create the agent brain
        agentbrain = PatientAgent(**kwargs['brain_args'])

        # these properties can't be sent via the kwargs because the API can't JSON serialize these objects and would
        # throw an error
        obj_body_args = {
            "sense_capability": SenseCapability({"*": np.inf}),
            "class_callable": PatientAgent,
            "callback_agent_get_action": agentbrain._get_action,
            "callback_agent_set_action_result": agentbrain._set_action_result,
            "callback_agent_observe": agentbrain._fetch_state,
            "callback_agent_log": agentbrain._get_log_data,
            "callback_agent_get_messages": agentbrain._get_messages,
            "callback_agent_set_messages": agentbrain._set_messages,
            "callback_agent_initialize": agentbrain.initialize,
            "callback_create_context_menu_for_other": agentbrain.create_context_menu_for_other
        }

        # merge the two sets of agent body properties
        body_args = dict(kwargs['body_args'])
        body_args.update(obj_body_args)

        # create the agent_body
        agent_body = AgentBody(**body_args)

        # register the new agent
        grid_world._register_agent(agentbrain, agent_body)

        # register any new teams
        grid_world._register_teams()

        return AddObjectResult(AddObjectResult.ACTION_SUCCEEDED, True)


class AddObjectResult(ActionResult):
    """ Result when assignment failed """
    # failed
    NO_AGENTBRAIN = "No object passed under the `agentbrain` key in kwargs"
    NO_AGENTBODY = "No object passed under the `agentbody` key in kwargs"
    # success
    ACTION_SUCCEEDED = "Agent was succesfully added to the gridworld."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)
