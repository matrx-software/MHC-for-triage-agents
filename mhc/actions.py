from matrx.actions import Action, ActionResult


class AssignBed(Action):
    """ Assign a patient to a hospital bed """

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):

        if 'object_id' not in kwargs:
            return AssignBedResult(AssignBedResult.NO_OBJECT_ID, False)

        if kwargs['object_id'] not in grid_world.environment_objects.keys():
            return AssignBedResult(AssignBedResult.OBJECT_NOT_FOUND.replace('object_id'.upper(),
                                                                            str(kwargs['object_id'])), False)

        # check if the bed is occupied
        bed = grid_world.environment_objects[kwargs['object_id']]
        if bed.properties['assigned_patient'] is not None:
            return AssignBedResult(AssignBedResult.BED_OCCUPIED, True)


        # success
        return AssignBedResult(AssignBedResult.ACTION_SUCCEEDED, True)


    def mutate(self, grid_world, agent_id, **kwargs):
        bed = grid_world.environment_objects[kwargs['object_id']]

        # unassign the old bed
        agent_bed = grid_world.registered_agents[agent_id].properties['current_bed_id']
        if agent_bed is not None:
            # grid_world.environment_objects[agent_bed].is_traversable = False
            grid_world.environment_objects[agent_bed].change_property('assigned_patient', 'free')
            grid_world.environment_objects[agent_bed].change_property('is_traversable', False)

        # assign patient to the new bed
        bed = grid_world.environment_objects[kwargs['object_id']]
        bed.change_property('assigned_patient', agent_id)
        bed.change_property('is_traversable', True)
        grid_world.registered_agents[agent_id].change_property('current_bed_id', kwargs['object_id'])

        return AssignBedResult(AssignBedResult.ACTION_SUCCEEDED, True)


class AssignBedResult(ActionResult):
    """ Result when assignment failed """
    # failed
    NO_OBJECT_ID = "No object ID of a bed was passed in the kwargs"
    OBJECT_NOT_FOUND = "Object with ID `OBJECT_ID` was not found"
    BED_OCCUPIED = "The hospital bed is already occupied by another patient."
    # success
    ACTION_SUCCEEDED = "Agent was successfully assigned to the hospital bed."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)




class RemovePatient(Action):
    """ An action that removes the agent itself from the grid """

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):
        if 'object_id' not in kwargs:
            return AssignBedResult(AssignBedResult.NO_OBJECT_ID, False)

        # check if the agent exists
        if kwargs['object_id'] not in grid_world.registered_agents.keys():
            return RemovePatientResult(AssignBedResult.AGENT_NOT_FOUND.replace('object_id'.upper(),
                                                                            str(kwargs['object_id'])), False)
        
        # success
        return RemovePatientResult(RemovePatientResult.ACTION_SUCCEEDED.replace('object_id'.upper(), str(agent_id)),
                                   True)


    def mutate(self, grid_world, agent_id, **kwargs):
        object_id = kwargs['object_id']

        # unassign the old bed
        agent_bed = grid_world.registered_agents[object_id].properties['current_bed_id']
        if agent_bed is not None:
            grid_world.environment_objects[agent_bed].change_property('assigned_patient', 'free')

        # remove the agent, success is whether GridWorld succeeded
        success = grid_world.remove_from_grid(object_id)

        # check if we succeeded in removing the agent
        if success:
            return RemovePatientResult(RemovePatientResult.ACTION_SUCCEEDED.replace('object_id'.upper(), str(object_id)), True)
        else:
            return RemovePatientResult(RemovePatientResult.REMOVAL_FAILED.replace('object_id'.upper(), str(object_id)), False)


class RemovePatientResult(ActionResult):
    """ Result when assignment failed """
    # failed
    NO_OBJECT_ID = "No object ID of a patient was passed in the kwargs"
    AGENT_NOT_FOUND = "Agent with ID `OBJECT_ID` was not found"
    REMOVAL_FAILED = "The agent with id `OBJECT_ID` failed to be removed by the environment for some reason."
    # success
    ACTION_SUCCEEDED = "Agent with ID `OBJECT_ID` was succesfully removed from the gridworld."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)

class UnassignBed(Action):
    """ Assign a patient to a hospital bed """

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):

        if grid_world.registered_agents[agent_id].properties['current_bed_id'] not in grid_world.environment_objects.keys():
            return UnassignBedResult(UnassignBedResult.OBJECT_NOT_FOUND.replace('object_id'.upper(),
                                                                            str(grid_world.registered_agents[agent_id].properties['current_bed_id'])), False)

        # success
        return UnassignBedResult(UnassignBedResult.ACTION_SUCCEEDED, True)


    def mutate(self, grid_world, agent_id, **kwargs):

        # unassign the old bed
        agent_bed = grid_world.registered_agents[agent_id].properties['current_bed_id']
        if agent_bed is not None:
            # grid_world.environment_objects[agent_bed].is_traversable = False
            grid_world.environment_objects[agent_bed].change_property('assigned_patient', 'free')
            grid_world.environment_objects[agent_bed].change_property('is_traversable', False)


        grid_world.registered_agents[agent_id].change_property('current_bed_id', None)
        grid_world.registered_agents[agent_id].change_property('medical_care' , None)

        return UnassignBedResult(UnassignBedResult.ACTION_SUCCEEDED, True)


class UnassignBedResult(ActionResult):
    """ Result when assignment failed """
    # failed
    OBJECT_NOT_FOUND = "Object with ID `OBJECT_ID` was not found"
    # success
    ACTION_SUCCEEDED = "Agent was successfully unassigned from the hospital bed."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)





class SetAgentPlannedTriageDecisions(Action):
    """ Set the (provisional) triage decisions of the agent for patients"""

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):

        if not 'triage_decisions' in kwargs:
            return SetAgentPlannedTriageDecisionsResult("Missing keyword argument 'triage_decisions'", False)
        elif not 'triage_decision_influences' in kwargs:
            return SetAgentPlannedTriageDecisionsResult("Missing keyword argument 'triage_decision_influences'", False)
        elif not 'patients_info' in kwargs:
            return AgentTriageTDP2Result("Missing keyword argument 'patients_info'", False)

        # success
        return SetAgentPlannedTriageDecisionsResult(SetAgentPlannedTriageDecisionsResult.ACTION_SUCCEEDED, True)


    def mutate(self, grid_world, agent_id, **kwargs):

        # set the provisional triage decisions
        for patient_ID, triage_decision in kwargs['triage_decisions'].items():
            if patient_ID in grid_world.registered_agents:
                grid_world.registered_agents[patient_ID].change_property("agent_planned_triage_decision", triage_decision)

        # set the triage_decision_influences that explain why the triage decision was made
        for patient_ID, triage_decision_influences in kwargs['triage_decision_influences'].items():
            if patient_ID in grid_world.registered_agents:
                grid_world.registered_agents[patient_ID].change_property("agent_triage_decision_influences", triage_decision_influences)

        # update the info of the patient as passed by the agent
        for patient_ID, patient_props in kwargs['patients_info'].items():
            for prop_key, prop_val in patient_props.items():
                if patient_ID in grid_world.registered_agents:
                    grid_world.registered_agents[patient_ID].change_property(prop_key, prop_val)

        return SetAgentPlannedTriageDecisionsResult(SetAgentPlannedTriageDecisionsResult.ACTION_SUCCEEDED, True)


class SetAgentPlannedTriageDecisionsResult(ActionResult):
    """ Result when assignment succeeded / failed """
    # failed

    # success
    ACTION_SUCCEEDED = "Agent was successfully assigned to the hospital bed."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)



class AgentTriageTDP2(Action):
    """ Set the (provisional) triage decisions of the agent for patients"""

    def __init__(self, duration_in_ticks=0):
        super().__init__(duration_in_ticks)

    def is_possible(self, grid_world, agent_id, **kwargs):

        if not 'triage_decisions' in kwargs:
            return AgentTriageTDP2Result("Missing keyword argument 'triage_decisions'", False)
        elif not 'triage_decision_influences' in kwargs:
            return AgentTriageTDP2Result("Missing keyword argument 'triage_decision_influences'", False)
        elif not 'patients_info' in kwargs:
            return AgentTriageTDP2Result("Missing keyword argument 'patients_info'", False)

        # success
        return AgentTriageTDP2Result(AgentTriageTDP2Result.ACTION_SUCCEEDED, True)


    def mutate(self, grid_world, agent_id, **kwargs):

        # set the provisional triage decisions
        for patient_ID, triage_decision in kwargs['triage_decisions'].items():
            if patient_ID in grid_world.registered_agents:
                grid_world.registered_agents[patient_ID].change_property("agent_planned_triage_decision", triage_decision)

        # set the triage_decision_influences that explain why the triage decision was made
        for patient_ID, triage_decision_influences in kwargs['triage_decision_influences'].items():
            if patient_ID in grid_world.registered_agents:
                grid_world.registered_agents[patient_ID].change_property("agent_triage_decision_influences", triage_decision_influences)

        # update the info of the patient as passed by the agent
        for patient_ID, patient_props in kwargs['patients_info'].items():
            for prop_key, prop_val in patient_props.items():
                if patient_ID in grid_world.registered_agents:
                    # the agent is not allowed to take patients from the human
                    if prop_key == "assigned_to" and grid_world.registered_agents[patient_ID].properties['assigned_to'] == 'person':
                        continue

                    grid_world.registered_agents[patient_ID].change_property(prop_key, prop_val)

        return AgentTriageTDP2Result(AgentTriageTDP2Result.ACTION_SUCCEEDED, True)


class AgentTriageTDP2Result(ActionResult):
    """ Result when assignment succeeded / failed """
    # failed

    # success
    ACTION_SUCCEEDED = "Agent was successfully assigned to the hospital bed."

    def __init__(self, result, succeeded):
        super().__init__(result, succeeded)
