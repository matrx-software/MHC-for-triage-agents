import random

from matrx.agents import AgentBrain
from matrx.messages import Message

from mhc.actions import SetAgentPlannedTriageDecisions, AgentTriageTDP2
from mhc.triage_model import TriageScoringAlgorithm


class TriageAgent(AgentBrain):

    def __init__(self, config, tdp, user_elicitation_results):
        super().__init__()
        self.state_tracker = None

        self.config = config
        self.tdp = tdp

        self.all_patients = []
        self.human_assigned_patients = []
        self.agent_assigned_patients = []

        self.free_IC_beds = 0
        self.free_ziekenboeg_beds = 0
        # keep track of if the number of available beds changed in this tick
        self.num_free_beds_changed = False

        # scores of each patient that describe the medical care they need and how badly they need it
        self.triage_scores = {}
        # subsequent triage decision made based on triage scores
        self.triage_decisions_prev = {}
        self.triage_decisions = {}

        self.patients_triage_priority_influences = {}
        self.user_elicitation_results = user_elicitation_results

        self.triage_scoring_algorithm = TriageScoringAlgorithm(user_elicited_rules=user_elicitation_results)


    def initialize(self):
        pass

    def filter_observations(self, state):
        # init some params for this tick
        self.num_free_beds_changed = False
        self.triage_scores = {}
        self.triage_decisions_prev = self.triage_decisions.copy()
        self.triage_decisions = {}
        self.patients_triage_priority_influences = {}
        self.human_assigned_patients = []
        self.agent_assigned_patients = []

        # get all untriaged patients from the state
        patients = state[{"is_patient": True, 'triaged': False}]

        # make sure we are dealing with a list of patients
        if patients is not None:
            if not isinstance(patients, list):
                patients = [patients]
        else:
            patients = []

        # completely reassign all patients from scratch every tick
        self.all_patients = []
        for patient in patients:
            # add current patients
            self.all_patients.append(patient['obj_id'])

            if self.tdp == "tdp_supervised_autonomy":
                # by default assign every patient to the agent
                self.agent_assigned_patients.append(patient['obj_id'])

            elif self.tdp == "tdp_dynamic_task_allocation":
                # start with assigning everything to the agent, but don't steal patients from the human for TDP 2
                if patient['assigned_to'] != 'person':
                    self.agent_assigned_patients.append(patient['obj_id'])
                else:
                    self.human_assigned_patients.append(patient['obj_id'])

        # keep track of all free beds and if the number changed
        free_IC_beds = self.count_free_beds(state[{'name': "Bed_top", 'room': "IC", 'assigned_patient': 'free'}])
        free_ziekenboeg_beds = self.count_free_beds(state[{'name': "Bed_top", 'room': "ziekenboeg", 'assigned_patient': 'free'}])

        if free_IC_beds != self.free_IC_beds or free_ziekenboeg_beds != self.free_ziekenboeg_beds:
            self.num_free_beds_changed = True
        self.free_IC_beds = free_IC_beds
        self.free_ziekenboeg_beds = free_ziekenboeg_beds

        return state

    def count_free_beds(self, free_beds):
        """ Count how many free beds of a specific type are available right now"""
        if free_beds is None:
            return 0
        elif isinstance(free_beds, list):
            return len(free_beds)
        else:
            return 1

    def decide_on_action(self, state):
        action = None
        action_kwargs = {"action_duration": 0}

        # influence of each (priority) rule on the triage score and why
        self.patients_triage_priority_influences = {}

        # calc the triage decisions for the patients (and any patient assignment) according to the triage score and TDP
        if self.tdp == "tdp_supervised_autonomy":
            action, action_kwargs = self.triaging_supervised_autonomy(state, action, action_kwargs)
        elif self.tdp == "tdp_dynamic_task_allocation":
            action, action_kwargs = self.triaging_dynamic_task_allocation(state, action, action_kwargs)


        patients_reset_countdowns = []
        # extend the timer of any patients of who the triage decision changed
        for patient_ID, triage_decision in self.triage_decisions.items():
            if patient_ID in self.agent_assigned_patients and patient_ID in self.triage_decisions_prev and \
                    self.triage_decisions_prev[patient_ID] != triage_decision:
                print(f"Triage decision for {patient_ID} changed, resetting triage timer")
                mssg = Message(to_id=patient_ID, from_id=self.agent_id, content={
                    "type": "reset_counter",
                    "counter_value": self.config['triage_countdown']
                })
                self.send_message(mssg)
                patients_reset_countdowns.append(patient_ID)

        # make the triage decision final for any patients of who the counter is 0 by sending them the triage decision
        # in a message
        for patient_ID in self.agent_assigned_patients:
            if state[patient_ID]['countdown'] <= 0 and patient_ID not in patients_reset_countdowns:
                decision = self.triage_decisions[patient_ID] if patient_ID in self.triage_decisions else state[patient_ID]['agent_planned_triage_decision']
                print(f"Counter for {patient_ID} is zero, sending triage decision: {decision}")
                mssg = Message(to_id=patient_ID, from_id=self.agent_id, content={
                    "type": "triage_decision",
                    "decision": decision,
                    "triaged_by": "agent"
                })
                self.send_message(mssg)
                self.agent_assigned_patients.remove(patient_ID)

        return action, action_kwargs


    def triaging_supervised_autonomy(self, state,  action, action_kwargs):
        """ Triage each patiet based on the triage score, prioritising patients with a higher score """

        patients_info = {}

        # calc the triage score for every patient currently in the waiting room
        for patient_ID in self.all_patients:
            triage_score, triage_priority_influences = self.calc_patient_triage_score(state[patient_ID])
            self.triage_scores[patient_ID] = triage_score
            self.patients_triage_priority_influences[patient_ID] = triage_priority_influences

            # assign all to ourselves
            patients_info[patient_ID] = {'assigned_to': 'robot'}

        # sort the patients based on triage score, higher scores first
        priority_sorted_patients = [k for k, v in sorted(self.triage_scores.items(), key=lambda item: item[1])]
        priority_sorted_patients.reverse()

        # Triage every patient based on the triage score, with higher scores getting priority over lower scores.
        # If care is not available, assign medial care one step worse (until available care is found)
        for patient_ID in priority_sorted_patients:
            # round the triage score to the nearest triage decision 1 (huis), 2 (ziekenboeg) or 3 (IC)
            triage_score = round(self.triage_scores[patient_ID])

            # patient requires IC care
            if triage_score >= 3:
                # assign IC if possible, otherwise ziekenboeg, otherwise huis
                if self.free_IC_beds > 0:
                    self.triage_decisions[patient_ID] = "IC"
                    self.free_IC_beds -= 1
                elif self.free_ziekenboeg_beds > 0:
                    self.triage_decisions[patient_ID] = "ziekenboeg"
                    self.free_ziekenboeg_beds -= 1
                else:
                    self.triage_decisions[patient_ID] = "huis"

            # patient requires ziekenboeg care
            elif triage_score >= 2:
                if self.free_ziekenboeg_beds > 0:
                    self.triage_decisions[patient_ID] = "ziekenboeg"
                    self.free_ziekenboeg_beds -= 1
                else:
                    self.triage_decisions[patient_ID] = "huis"

            # patient requires home care
            elif triage_score <= 1:
                self.triage_decisions[patient_ID] = "huis"

        # perform an action that set the triage decision and reasoning for each patient
        action = SetAgentPlannedTriageDecisions.__name__
        action_kwargs["triage_decisions"] = self.triage_decisions
        action_kwargs["triage_decision_influences"] = self.patients_triage_priority_influences
        action_kwargs['patients_info'] = patients_info

        return action, action_kwargs


    def triaging_dynamic_task_allocation(self, state, action, action_kwargs):
        """
        De agent is onzeker van een besluit als er N patienten een soortgelijke zorg moeten krijgen,
        terwijl er <N bedden in die zorg beschikbaar zijn, met N>1. Bij onzekerheid worden al deze N patienten
        toegewezen aan de mens. Als er N+1 patienten zijn, worden de N eerdere patienten mee genomen in de berekening
        of de agent voor de nieuwe patient ook onzeker is. Een lage zekerheid is gedefiniëerd als de triage score van
        twee of meer patiënten van 0.5 of minder van elkaar ligt
        """
        # for each patient all info and explanations updated for this tick
        patients_info = {}

        # calc the triage score for every patient currently in the waiting room
        for patient_ID in self.all_patients:
            triage_score, triage_priority_influences = self.calc_patient_triage_score(state[patient_ID])
            self.triage_scores[patient_ID] = triage_score
            self.patients_triage_priority_influences[patient_ID] = triage_priority_influences

            # by default assume the agent can and will triage the patient
            patients_info[patient_ID] = {"can_be_triaged_by_agent": True}
            if patient_ID not in self.human_assigned_patients:
                patients_info[patient_ID]['assigned_to'] = 'robot'
                self.agent_assigned_patients.append(patient_ID);
        # sort the patients based on triage score, higher scores first
        priority_sorted_patients = [k for k, v in sorted(self.triage_scores.items(), key=lambda item: item[1])]
        priority_sorted_patients.reverse()

        ############################################################
        # Calc triage score and ideal medical care per patient
        ############################################################

        # keep track of which agents need a type of limited medical care
        bed_assignments = {"IC": [], "ziekenboeg": []}

        # Triage every patient based on the triage score and identify the bed they need.
        # patients can always be immediately assigned to home, but for limited care (IC, ziekenboeg), don't assign yet.
        # If care is not available, assign medial care one step worse (until available care is found)
        for patient_ID in priority_sorted_patients:
            # round the triage score to the nearest triage decision 1 (huis), 2 (ziekenboeg) or 3 (IC)
            triage_score = round(self.triage_scores[patient_ID])

            # patient requires IC care
            if triage_score >= 3:
                # assign IC if possible, otherwise ziekenboeg, otherwise huis
                if self.free_IC_beds > 0:
                    bed_assignments['IC'].append(
                        {"patient_ID": patient_ID, "triage_score": self.triage_scores[patient_ID]})
                elif self.free_ziekenboeg_beds > 0:
                    bed_assignments['ziekenboeg'].append(
                        {"patient_ID": patient_ID, "triage_score": self.triage_scores[patient_ID]})
                else:
                    self.triage_decisions[patient_ID] = "huis"

            # patient requires ziekenboeg care
            elif triage_score >= 2:
                if self.free_ziekenboeg_beds > 0:
                    bed_assignments['ziekenboeg'].append(
                        {"patient_ID": patient_ID, "triage_score": self.triage_scores[patient_ID]})
                else:
                    self.triage_decisions[patient_ID] = "huis"

            # patient requires home care
            elif triage_score <= 1:
                self.triage_decisions[patient_ID] = "huis"


        # For each type of care, check that enough care is available, if not:
        # (TDP 2) in the case of high uncertainty (scores of patients <= 0.5), assign the patients to the human

        ############################################
        # Assigning to the IC
        ############################################

        # assign all patients to the IC if the beds are available
        if len(bed_assignments['IC']) <= self.free_IC_beds:
            for patient in bed_assignments['IC']:
                self.triage_decisions[patient['patient_ID']] = 'IC'

        # not enough beds, so compare the patients
        else:
            # keep track of patients that have to be send from IC to ziekenboeg due to a lack of IC beds
            ic_patients_to_ziekenboeg = []
            # track patients that the agent is uncertain about (diff <= 0.5)
            uncertain_patients_cluster = []

            for i, patient in enumerate(bed_assignments['IC']):

                if self.free_IC_beds > 0:
                    # check if there are multiple patients that want this bed
                    if i + 1 < len(bed_assignments['IC']):

                        # if the score is X higher than the next patient, the agent is certain that the current
                        # patient deserves it more than the next one
                        if patient['triage_score'] - bed_assignments['IC'][i+1]['triage_score'] > self.config['triage_agent_uncertainty_threshold']:

                            # END OF UNCERTAIN PATIENTS CLUSTER
                            # The agent was uncertain of the current patient compared to the previous one, but IS
                            # certain about it compared to the next one.
                            if len(uncertain_patients_cluster) > 0:

                                # not enough beds for all patients in the uncertain cluster, so assign them to the human
                                if self.free_IC_beds < len(uncertain_patients_cluster):
                                    # assign all patients in the uncertain cluster to the human
                                    patients_info = self.assign_patients_dynamic_task_allocation(
                                        uncertain_patients_cluster.copy(), "IC", state, patients_info)

                                    # prevent any subsequent patients from being assigned to the IC
                                    self.free_IC_beds = 0

                                # enough beds for all patients in the uncertain cluster, so assign them all an IC bed
                                else:
                                    for patient in uncertain_patients_cluster:
                                        self.triage_decisions[patient['patient_ID']] = "IC"
                                        self.free_IC_beds -= 1

                            # current patient not part of a cluster, so assign it the available IC bed it needs
                            else:
                                self.triage_decisions[patient['patient_ID']] = "IC"
                                self.free_IC_beds -= 1

                        # START OF UNCERTAIN PATIENTS CLUSTER
                        # the agent is uncertain of this patient compared to the next one, so save them temporarily.
                        # These are candidates for assigning to the human
                        else:
                            uncertain_patients_cluster.append(patient)
                            uncertain_patients_cluster.append(bed_assignments['IC'][i+1])
                            # only keep unique items
                            uncertain_patients_cluster = [dict(t) for t in {tuple(d.items()) for d in uncertain_patients_cluster}]

                    else:
                        # END OF UNCERTAIN PATIENTS CLUSTER
                        # The agent was uncertain of the current patient compared to the previous one, but the cluster
                        # has ended (no more patients for this type of care) so time to assign
                        if len(uncertain_patients_cluster) > 0:

                            # not enough beds for all patients in the uncertain cluster, so assign them to the human
                            if self.free_IC_beds < len(uncertain_patients_cluster):
                                # assign all patients in the uncertain cluster to the human
                                patients_info = self.assign_patients_dynamic_task_allocation(
                                    uncertain_patients_cluster.copy(), "IC", state, patients_info)
                                uncertain_patients_cluster = []

                                # prevent any subsequent patients from being assigned to the IC
                                self.free_IC_beds = 0

                            # enough beds for all patients in the uncertain cluster, so assign them all an IC bed
                            else:
                                for patient in uncertain_patients_cluster:
                                    self.triage_decisions[patient['patient_ID']] = "IC"
                                    self.free_IC_beds -= 1

                        # only 1 patient left that needs IC with 1 bed free, assign it
                        else:
                            self.triage_decisions[patient['patient_ID']] = "IC"
                            self.free_IC_beds -= 1

                # if there are no more IC beds to assign, assign patient to ziekenboeg bed instead
                else:
                    ic_patients_to_ziekenboeg.append(bed_assignments['IC'][i])

            # IC patients who didn't get a IC bed have the highest priority for the ziekenboeg beds
            bed_assignments['ziekenboeg'] = ic_patients_to_ziekenboeg + bed_assignments['ziekenboeg']

        ############################################
        # Assigning to the ziekenboeg
        ############################################

        # assign all patients to the ziekenboeg if the beds are available
        if len(bed_assignments['ziekenboeg']) <= self.free_ziekenboeg_beds:
            for patient in bed_assignments['ziekenboeg']:
                self.triage_decisions[patient['patient_ID']] = 'ziekenboeg'

        # not enough beds, so compare the patients
        else:
            # track patients that the agent is uncertain about (diff <= 0.5)
            uncertain_patients_cluster = []

            for i, patient in enumerate(bed_assignments['ziekenboeg']):

                if self.free_ziekenboeg_beds > 0:
                    # check if there are multiple people that want this bed
                    if i + 1 < len(bed_assignments['ziekenboeg']):

                        # if the score is X higher than the next patient, the agent is certain that the current
                        # patient deserves it more than the next one
                        if patient['triage_score'] - bed_assignments['ziekenboeg'][i + 1]['triage_score'] > self.config['triage_agent_uncertainty_threshold']:

                            # END OF UNCERTAIN PATIENTS CLUSTER
                            # The agent was uncertain of the current patient compared to the previous one, but IS
                            # certain about it compared to the next one.
                            if len(uncertain_patients_cluster) > 0:

                                # not enough beds for all patients in the uncertain cluster, so assign them to the human
                                if self.free_ziekenboeg_beds < len(uncertain_patients_cluster):
                                    # assign all patients in the uncertain cluster to the human
                                    patients_info = self.assign_patients_dynamic_task_allocation(
                                        uncertain_patients_cluster.copy(), "ziekenboeg", state, patients_info)
                                    uncertain_patients_cluster = []

                                    # prevent any subsequent patients from being assigned to the ziekenboeg
                                    self.free_ziekenboeg_beds = 0

                                # enough beds for all patients in the uncertain cluster, so assign them all an ziekenboeg bed
                                else:
                                    for patient in uncertain_patients_cluster:
                                        self.triage_decisions[patient['patient_ID']] = "ziekenboeg"
                                        self.free_ziekenboeg_beds -= 1

                            # current patient not part of a cluster, so assign it the available ziekenboeg bed it needs
                            else:
                                self.triage_decisions[patient['patient_ID']] = "ziekenboeg"
                                self.free_ziekenboeg_beds -= 1

                        # START OF UNCERTAIN PATIENTS CLUSTER
                        # the agent is uncertain of this patient compared to the next one, so save them temporarily.
                        # These are candidates for assigning to the human
                        else:
                            uncertain_patients_cluster.append(patient)
                            uncertain_patients_cluster.append(bed_assignments['ziekenboeg'][i + 1])
                            # only keep unique items
                            uncertain_patients_cluster = [dict(t) for t in {tuple(d.items()) for d in uncertain_patients_cluster}]

                    else:
                        # END OF UNCERTAIN PATIENTS CLUSTER
                        # The agent was uncertain of the current patient compared to the previous one, but the cluster
                        # has ended (no more patients for this type of care) so time to assign
                        if len(uncertain_patients_cluster) > 0:
                            # not enough beds for all patients in the uncertain cluster, so assign them to the human
                            if self.free_ziekenboeg_beds < len(uncertain_patients_cluster):
                                # assign all patients in the uncertain cluster to the human
                                patients_info = self.assign_patients_dynamic_task_allocation(
                                    uncertain_patients_cluster.copy(), "ziekenboeg", state, patients_info)
                                uncertain_patients_cluster = []
                                # prevent any subsequent patients from being assigned to the ziekenboeg
                                self.free_ziekenboeg_beds = 0

                            # enough beds for all patients in the uncertain cluster, so assign them all an ziekenboeg bed
                            else:
                                for patient in uncertain_patients_cluster:
                                    self.triage_decisions[patient['patient_ID']] = "ziekenboeg"
                                    self.free_ziekenboeg_beds -= 1

                        # only 1 patient left that needs ziekenboeg with 1 bed free, assign it

                        else:
                            self.triage_decisions[patient['patient_ID']] = "ziekenboeg"
                            self.free_ziekenboeg_beds -= 1

                # if there are no more ziekenboeg bedden to assign, assign patient to home instead
                else:
                    self.triage_decisions[patient_ID] = "huis"

        # perform an action that set the triage decision and reasoning for each patient
        action = AgentTriageTDP2.__name__
        action_kwargs["triage_decisions"] = self.triage_decisions
        action_kwargs["triage_decision_influences"] = self.patients_triage_priority_influences
        action_kwargs["patients_info"] = patients_info

        return action, action_kwargs


    def assign_patients_dynamic_task_allocation(self, uncertain_patients_cluster, care_needed, state, patients_info):
        """ assign the difficult patients to the human, and update the info of the patients """
        for patient in uncertain_patients_cluster:
            patient_ID = patient['patient_ID']

            # assign the patient to the human if not already the case
            if state[patient_ID]['assigned_to'] != 'person':
                print(f"Assigned {state[patient_ID]['patient_name']} to person")
                mssg = Message(to_id=patient['patient_ID'], from_id=self.agent_id, content={
                    "type": "reassign",
                    "assigned_to": 'person'
                })
                self.send_message(mssg)

            # list the names of the other patients that want this type of care
            care_contending_patients = [state[pat['patient_ID']]['patient_name'] for pat in
                                        uncertain_patients_cluster if (pat['patient_ID'] != patient_ID and not state[pat['patient_ID']]['triaged'])]

            # assign the patient to the person and that it cannot be triaged by the agent
            patients_info[patient_ID]['assigned_to'] = 'person'
            patients_info[patient_ID]['can_be_triaged_by_agent'] = False

            # note the patients all wanting the same care
            patients_info[patient_ID]['agent_planned_triage_decision'] = care_needed
            patients_info[patient_ID]['care_contending_patients'] = care_contending_patients

            #patients_info[patient_ID]['triaged'] = False
            #patients_info[patient_ID]['triaged_by'] = False

        return patients_info

    def calc_patient_triage_score(self, patient):
        """" Calculate the triage score for a patient, which is a combination of the type of medical needed, and
        their need for that medical care compared to other patients. Ranges between 0 to 4, with 1 being 'huis',
        2 = 'ziekenboeg', 3 = 'IC'"""

        triage_score = self.triage_scoring_algorithm.calc_triage_score(symptoms=patient['symptoms'],
                                                                       fitness=patient['fitness'],
                                                                       age=patient['age'],
                                                                       profession=patient['profession'],
                                                                       gender=patient['gender'],
                                                                       home_situation=patient['home_situation'])

        # for now generate a random number - for testing purposes
        # triage_score = float(random.choice(range(0, 40)) / 10.0)
        return triage_score


    def get_log_data(self):
        """ Gather some data that can be logged every tick """
        log_data = {"user_elicitation_rules": self.user_elicitation_results, "triage_scores": self.triage_scores,
                    "triage_decisions": self.triage_decisions,
                    "triage_score_influences": self.patients_triage_priority_influences}
        return log_data
