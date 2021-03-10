from matrx.logger.logger import GridWorldLogger


class LogNewPatients(GridWorldLogger):
    """ Log all info of new patients """

    def __init__(self, save_path="", file_name_prefix="", file_extension=".csv", delimeter=";"):
        super().__init__(save_path=save_path, file_name=file_name_prefix, file_extension=file_extension,
                         delimiter=delimeter, log_strategy=1)

        self.patients = []

    def log(self, grid_world, agent_data):
        log_statement = {}


        new_patients = []
        # log new patients
        for agent_id, agent in grid_world.registered_agents.items():
            if 'PatientAgent' in agent.properties['class_inheritance'] and not agent_id in self.patients:
                self.patients.append(agent_id)

                # add info on patient
                log_statement["ticks"] = grid_world.current_nr_ticks
                log_statement["agent_id"] = agent_id
                log_statement["number"] = agent.properties['number']
                log_statement["patient_name"] = agent.properties['patient_name']
                log_statement["img_name"] = agent.properties['img_name']
                log_statement["gender"] = agent.properties['gender']
                log_statement["age"] = agent.properties['age']
                log_statement["profession"] = agent.properties['profession']
                log_statement["fitness"] = agent.properties['fitness']
                log_statement["home_situation"] = agent.properties['home_situation']
                log_statement["patient_photo"] = agent.properties['patient_photo']
                log_statement["patient_medical_offsets"] = agent.properties['patient_medical_offsets']
                log_statement["patient_introduction_text"] = agent.properties['patient_introduction_text']
                log_statement["symptoms_start"] = agent.properties['symptoms_start']
                log_statement["symptoms"] = agent.properties['symptoms']
                log_statement["health"] = agent.properties['health']
                log_statement["medical_care"] = agent.properties['medical_care']

        return log_statement



class LogPatientStatus(GridWorldLogger):
    """ Log the status of every patient.

     As it is not possible to add columns during the experiment (as extra patients are created), all info is put
     in a dict that is logged.
     """

    def __init__(self, save_path="", file_name_prefix="", file_extension=".csv", delimeter=";"):
        super().__init__(save_path=save_path, file_name=file_name_prefix, file_extension=file_extension,
                         delimiter=delimeter, log_strategy=10)

    def log(self, grid_world, agent_data):
        log_statement = {}

        patient_statusses = {}

        # log new patients
        for agent_id, agent in grid_world.registered_agents.items():
            if 'PatientAgent' in agent.properties['class_inheritance']:
                patient_info = {}

                # add info on patient
                patient_info["agent_id"] = agent_id
                patient_info["symptoms"] = agent.properties['symptoms']
                patient_info["health"] = agent.properties['health']
                patient_info["medical_care"] = agent.properties['medical_care']

                # add the patient info under the agent ID
                patient_statusses[agent_id] = patient_info

        if patient_statusses != {}:
            log_statement['status_per_patient'] = patient_statusses


        return log_statement


class LogTriageDecision(GridWorldLogger):
    """ Log triage decisions.

     """

    def __init__(self, save_path="", file_name_prefix="", file_extension=".csv", delimeter=";"):
        super().__init__(save_path=save_path, file_name=file_name_prefix, file_extension=file_extension,
                         delimiter=delimeter, log_strategy=1)

    def log(self, grid_world, agent_data):
        log_statement = {}

        # we check the messages of the previous tick, as the messages of this tick haven't been processed yet
        tick_to_check = grid_world.current_nr_ticks-1

        if tick_to_check in grid_world.message_manager.preprocessed_messages.keys():

            # loop through all messages of this tick
            for message in grid_world.message_manager.preprocessed_messages[tick_to_check]:

                # only check triage decision messages
                if isinstance(message.content, dict) and 'type' in message.content.keys() \
                        and message.content['type'] == "triage_decision":
                    #agent might have died when being triaged
                    if message.to_id in grid_world.registered_agents:
                        agent = grid_world.registered_agents[message.to_id]

                        # log triage message and some info on the patient
                        log_statement['agent_id'] = message.to_id
                        log_statement['triage_decision'] = message.content['decision']
                        log_statement['health'] = agent.properties['health']
                        log_statement["symptoms"] = agent.properties['symptoms']
                        log_statement['decided_by'] = "human-agent"
                        log_statement['correct_tick'] = tick_to_check

        return log_statement



class LogTriageAgent(GridWorldLogger):
    """
    For each tick, log the triage score, triage decision, triage reasoning, and user elicitation used or calculated
    by the triage agent
    """

    def __init__(self, save_path="", file_name_prefix="", file_extension=".csv", delimeter=";"):
        super().__init__(save_path=save_path, file_name=file_name_prefix, file_extension=file_extension,
                         delimiter=delimeter, log_strategy=1)

    def log(self, grid_world, agent_data):

        data = {}
        for agent_id, agent_data in agent_data.items():
            id_num = agent_id.split("_")[-1]
            agent_name = agent_id.replace("_" + id_num, "")
            # counts the received 'requests', 'accepts', 'rejects' an agent has received
            for col, val in agent_data.items():
                data[f"{agent_name} - {col}"] = val

        return data
