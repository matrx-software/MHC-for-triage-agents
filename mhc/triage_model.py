import numpy as np
from mhc.sickness_model import SicknessModel

class TriageScoringAlgorithm:
    """ Algorithm used by an agent to calculate a triage score for a patient.
        The score indicates what medical care a patient needs, and also how badly they need to care.
        The score is within the range of 0 to 4, where a score of correspond to medical care "huis", 2 = ziekenboeg, and
        3 = IC. In addition, each patient can have an increase or decrease in score based on the medical guidelines,
        ethical guidelines, and ethical compass of the test subject (retrieved using user elicitation).

        For more info see the doc: https://365tno.sharepoint.com/:w:/r/teams/P060.43326/_layouts/15/Doc.aspx?sourcedoc=%7BA9FFEAC8-50DF-44DD-8104-7505422D1A18%7D&file=Value%20elicitation%20agent%20algorithm.docx&action=default&mobileredirect=true
     """


    def __init__(self, user_elicited_rules=[]):
        # init the sickness model so we have access to the symptom_mappings etc
        self.sickness_model = SicknessModel(config=None)

        # map symptoms to medical needed
        self.symptom_triage_mapping = {"Zeer mild": 1, "Mild": 1, "Zeer laag": 1, "Laag": 1, "Gemiddeld": 2, "Hoog": 3,
                                       "Zeer hoog": 3}

        # map fitness to triage score
        self.fitness_triage_mapping = {"Zeer laag": -1, "Laag": -0.5, "Gemiddeld": 0, "Hoog": 0.5, "Zeer hoog": 1}

        # medical professions
        self.healthcar_professions = ["Medisch specialist", "Apotheker", "Tandarts", "Arts"]

        self.user_elicited_rules = user_elicited_rules

    def calc_triage_score(self, symptoms, fitness, age, profession, gender, home_situation):
        triage_score = None

        # keep track for each (priority) rule how much the effect was on the total triage score and why
        score_influences = {}

        ###################################################################
        # Calc the medical care needed based on the severity of symptoms
        ###################################################################
        triage_score = self.symptom_triage_mapping[symptoms]
        # low and very low = negative influence, otherwise positive
        infl = -1 if triage_score <= 1 else (triage_score-1)/2
        score_influences['symptoms'] = {'influence': infl, 'reason': f"Patiënten met ernstige symptomen krijgen voorrang "
                                                                     f"op patiënten met minder ernstige symptomen. "
                                                                     f"Deze patiënt heeft ernst van symptomen: {symptoms}"}


        ###################################################################
        # Apply the priority rules
        ###################################################################
        max_priority_modifier_score = 0
        priority_rules_score = 0

        # the priority (medical) rule that is always applicable is that of patients with high fitness having priority
        priority_rules_score += self.fitness_triage_mapping[fitness]
        max_priority_modifier_score = max(self.fitness_triage_mapping.values())
        score_influences['fitness'] = {'influence': priority_rules_score, 'reason': f"Patiënten met hoge fitheid krijgen "
                                                                                    f"voorrang op patiënten met lage "
                                                                                    f"fitheid. Deze patiënt heeft fitheid: {fitness}"}

        ###############
        # priority rules as defined by the user retrieved with user eliciation
        ################
        #######
        # Priority based on age
        if "age" in self.user_elicited_rules:
            self.user_elicited_rules['age'] = int(self.user_elicited_rules['age'])
            # high / low age has priority
            if self.user_elicited_rules['age'] == 1 or self.user_elicited_rules['age'] == 2:
                age_priority_score = 0
                # calc by default for option 2: low age gets priority
                if age <= 20:
                    age_priority_score += 1
                    score_influences['age'] = {"influence": 1, "reason": "Deze patiënt heeft een age leeftijd"}
                elif 40 >= age > 20:
                    age_priority_score += 0.5
                    score_influences['age'] = {"influence": 0.5, "reason": "Deze patiënt heeft een lage leeftijd"}
                elif 60 >= age > 40:
                    age_priority_score += 0
                    score_influences['age'] = {"influence": 0, "reason": "Deze patiënt heeft een gemiddelde leeftijd"}
                elif 80 >= age > 60:
                    age_priority_score -= 0.5
                    score_influences['age'] = {"influence": -0.5, "reason": "Deze patiënt heeft een hoge leeftijd"}
                elif age > 80:
                    age_priority_score -= 1
                    score_influences['age'] = {"influence": -1, "reason": "Deze patiënt heeft een hoge leeftijd"}

                # if it is option 1: high age high priority, flip the score
                if self.user_elicited_rules['age'] == 1:
                    age_priority_score *= -1
                    score_influences['age']['influence'] *= -1
                    score_influences['age']['reason'] = "Patienten met een hoge leeftijd krijgen prioriteit over " \
                                                        "patienten met een lage leeftijd. " + \
                                                        score_influences['age']['reason']
                else:
                    score_influences['age']['reason'] = "Patienten met een lage leeftijd krijgen prioriteit over " \
                                                        "patienten met een hoge leeftijd. " + \
                                                        score_influences['age']['reason']

                priority_rules_score += age_priority_score
                max_priority_modifier_score += 1

            # age has no influence
            elif self.user_elicited_rules == 3:
                pass

        #######
        # priority based on gender
        if "gender" in self.user_elicited_rules:
            self.user_elicited_rules['gender'] = int(self.user_elicited_rules['gender'])
            # women have priority
            if self.user_elicited_rules['gender'] == 1:
                influence = 1 if gender.lower() == "vrouw" else -1
                priority_rules_score += influence
                score_influences['gender'] = {"influence": influence, "reason": f"Vrouwen krijgen prioriteit over "
                                                                                f"mannen. De patiënt is een "
                                                                                f"{gender.lower()}."}
                max_priority_modifier_score += 1

            # men have priority
            elif self.user_elicited_rules['gender'] == 2:
                influence = 1 if gender.lower() == "man" else -1
                priority_rules_score += influence
                score_influences['gender'] = {"influence": influence, "reason": f"Mannen krijgen prioriteit over "
                                                                                f"vrouwen. De patiënt is een "
                                                                                f"{gender.lower()}."}
                max_priority_modifier_score += 1

            # gender no influence
            elif self.user_elicited_rules['gender'] == 3:
                pass

        #######
        # priority based on home_situation
        if "home_situation" in self.user_elicited_rules:
            self.user_elicited_rules['home_situation'] = int(self.user_elicited_rules['home_situation'])
            # families with children priority
            if self.user_elicited_rules['home_situation'] == 1:
                influence = 1 if "kind" in home_situation else -1
                priority_rules_score += influence
                score_influences['home_situation'] = {"influence": influence, "reason": f"Gezinnen met kinderen krijgen "
                                                                                        f"voorrang op gezinnen zonder "
                                                                                        f"kinderen. De patiënt heeft "
                                                                                        f"een gezin met {'geen ' if 'kind' not in home_situation else ''} kinderen."}
                max_priority_modifier_score += 1

            # families without children priority
            elif self.user_elicited_rules['home_situation'] == 2:
                influence = 1 if "kind" not in home_situation else -1
                priority_rules_score += influence
                score_influences['home_situation'] = {"influence": influence, "reason": f"Gezinnen met kinderen krijgen "
                                                                                        f"geen voorrang op gezinnen "
                                                                                        f"zonder kinderen. De patiënt "
                                                                                        f"heeft een gezin met {'geen ' if 'kind' not in home_situation else ''} kinderen."}
                max_priority_modifier_score += 1

            # family no influence
            elif self.user_elicited_rules['home_situation'] == 3:
                pass

        #######
        # priority based on profession
        if "profession" in self.user_elicited_rules:
            self.user_elicited_rules['profession'] = int(self.user_elicited_rules['profession'])
            # healthcare related professions priority
            if self.user_elicited_rules['profession'] == 1:
                influence = 1 if profession in self.healthcar_professions else -1
                priority_rules_score += influence
                score_influences['home_situation'] = {"influence": influence, "reason": f"Zorgpersoneel krijgen "
                                                                                        f"prioriteit over patienten met "
                                                                                        f"andere beroepen. De patiënt "
                                                                                        f"heeft {'geen ' if profession not in self.healthcar_professions else ''} baan in de gezondheidszorg."}
                max_priority_modifier_score += 1

            # NON-healthcare related professions priority
            elif self.user_elicited_rules['home_situation'] == 2:
                influence = 1 if profession not in self.healthcar_professions else -1
                priority_rules_score += influence
                score_influences['home_situation'] = {"influence": influence, "reason": f"Zorgpersoneel krijgen "
                                                                                        f"prioriteit over patienten met "
                                                                                        f"andere beroepen. De patiënt "
                                                                                        f"heeft {'geen ' if profession not in self.healthcar_professions else ''} baan in de gezondheidszorg."}
                max_priority_modifier_score += 1

            # profession no influence
            elif self.user_elicited_rules['home_situation'] == 3:
                pass

        # priority rules can have an influence on the final triage score between -1 and 1, so normalize the score
        # we have so far by dividing it by the maximum
        priority_rules_score = round(priority_rules_score / max_priority_modifier_score, 2)
        for key, val in score_influences.items():
            val['influence'] = round(val['influence'] / max_priority_modifier_score, 2)

        # triage score is the basic triage decision + priority rules tweak
        triage_score += priority_rules_score

        return triage_score, score_influences



