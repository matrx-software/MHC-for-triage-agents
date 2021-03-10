import matrx
from matrx import goals
from matrx.goals import *

class AllPatientsTriaged(WorldGoal):
    """
    A world goal that checks whether all patients have been triaged
    """

    def __init__(self, max_patient):
        """ Initialize the LimitedNumberPatients by saving the `max_patient`.
        """
        super().__init__()
        self.max_patient = max_patient
        self.triaged_patients = []

        # wait for X ticks after all patients have been triaged/died/healed before quitting
        self.countdown_after_completion = 0
        self.countdown_after_completion_goal = 75

    def goal_reached(self, grid_world):
        """ Returns whether the maximum number of specified patients has been reached.

        """
        # get the triaged patients
        triaged_patients = [agent_ID for agent_ID, agent in grid_world.registered_agents.items()
                                if 'triaged' in agent.properties and agent.properties['triaged']]

        # loop through all patients and add deceased / healed / triaged patients
        for agent_ID, agent in grid_world.registered_agents.items():
            if ('triaged' in agent.properties and agent.properties['triaged']) \
                    or ('health' in agent.properties and agent.properties['health'] is not None and
                        (agent.properties['health'] >= 100 or agent.properties['health'] <= 0)):
                # add agents which we didn't have yet
                if agent_ID not in self.triaged_patients:
                    self.triaged_patients.append(agent_ID)
                    print("New patient triaged/died/healed, total:", len(self.triaged_patients))

        # check if we are done
        if self.max_patient == np.inf or self.max_patient <= 0:
            self.is_done = False
        else:
            if len(self.triaged_patients) >= self.max_patient:
                if self.countdown_after_completion < self.countdown_after_completion_goal:
                    if self.countdown_after_completion == 0:
                        print(f">>All patients triaged/died/healed, waiting for {self.countdown_after_completion_goal} "
                              f"ticks before quitting<<")

                    # activate the completion message when we are done
                    elif self.countdown_after_completion > int(self.countdown_after_completion_goal * 0.7):
                        settings_obj = [obj for objID, obj in grid_world.environment_objects.items() if obj.properties['name'] == 'Settings'][0]
                        settings_obj.change_property("trial_completed", True)

                    self.countdown_after_completion += 1
                else:
                    self.is_done = True
            else:
                self.is_done = False
        return self.is_done


    def get_progress(self, grid_world):
        """ Returns the progress of reaching the AllPatientsTriaged in the simulated grid world.
        """
        # get the triaged patients
        triaged_patients = len([agent_ID for agent_ID, agent in grid_world.registered_agents.items()
                                if 'triaged' in agent.properties and agent.properties['triaged']])

        if triaged_patients != self.triaged_patients:
            print("New patient triaged, total triaged:", triaged_patients)

        self.triaged_patients = triaged_patients

        # calc progress
        if self.max_patient == np.inf or self.max_patient <= 0:
            return 0.
        return min(1.0, triaged_patients / self.max_patient)