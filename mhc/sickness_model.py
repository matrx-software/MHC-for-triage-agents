import numpy as np

class SicknessModel:
    """ Model of the sickness of a patient, used to calculate the health and symptoms over time """


    def __init__(self, config):
        self.config = config
        self.initialized = False

        # Fitness mapping: category name to the mean value
        self.fitness_mapping = {"Zeer laag": -2, "Laag": -1, "Gemiddeld": 0, "Hoog": 1, "Zeer hoog": 2}

        # Symptom mapping: category name to the mean value
        self.symptom_mapping = {"Zeer mild": 1, "Mild": 3, "Gemiddeld": 5, "Hoog": 7, "Zeer hoog": 9}
        self.symptom_health_ranges = {100 : "Zeer laag", 80: "Laag", 60: "Gemiddeld", 40: "Hoog", 20: "Zeer hoog"}

        # medical aid mapping: medical aid name to the mean of the normal distribution
        self.med_aid_mapping = {"eerste hulp": -1, "huis": -2, "ziekenboeg": 0, "IC": 3}


    def initial_health(self, health, symptoms, fitness, medical_care):
        """ Initialize how much health a patient has according to the passed variables """
        # 100 = full health, 0 = deceased
        # health = 100 - symptoms * 10
        # if you have symptoms at "zeer hoog" / level 9, this means you only have 100 - 9 * 10 = 10 health left
        health = 100 - self.symptom_mapping[symptoms] * 10
        return health


    def update_sickness(self, health, symptoms, symptoms_start, fitness, medical_care, patient_medical_offsets):
        # check if the start health has to be calculated
        if health is None:
            health = self.initial_health(health, symptoms, fitness, medical_care)

        if medical_care is None:
            return [health, symptoms]

        # TODO: implement sickness model V1 as described
        # here: https://ci.tno.nl/gitlab/jasper.vanderwaa-tno/mhc-triage/-/issues/2

        # calculate the new health based on the input variables
        health += (self.fitness_mapping[fitness] + patient_medical_offsets['fitness']) \
                  + (self.med_aid_mapping[medical_care] + patient_medical_offsets['med_aid'])
        health = round(health, 2)

        # the symptoms improve / worsen in accordance with health.
        best_symptom_category_match = 100
        for symptom_cat_threshold in self.symptom_health_ranges.keys():
            if health <= symptom_cat_threshold and (best_symptom_category_match is None or
                                                   symptom_cat_threshold < best_symptom_category_match):
                best_symptom_category_match = symptom_cat_threshold
        symptoms = self.symptom_health_ranges[best_symptom_category_match]

        return [health, symptoms]





def init_patient_specific_offsets():
    """ Every patient has slight variations inherent tot that person, and might for instance react differently
    to medical aid of a specific type. This function calculates the offset from the default (fitness or medical aid)
    values for a specific patient. So the patient-specific variation. """

    fitness_mean = 0
    fitness_std = 0.4
    fitness_offset = np.random.normal(fitness_mean, fitness_std, 1)[0]

    med_aid_mean = 0
    med_aid_std = 0.8
    med_aid_offset = np.random.normal(med_aid_mean, med_aid_std, 1)[0]

    return {"fitness": fitness_offset, "med_aid": med_aid_offset}
