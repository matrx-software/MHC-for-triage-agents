# Meaningful Human Control over agents in a code black pandemic triage task

This experiment is part of the paper **Assuring Trustworthiness of Autonomous Systems as Intelligent and Ethical Teammates**. 
It shows a task where the human test subject plays the role of a doctor assigned to a hospital section, during code black during a pandemic. The task is to triage every patient, and send them either to the Intensive care, the ward, or home. Test subjects have to follow a set of medical and ethical guidelines in determining the appropriate care for every patient, and also who gains priority in the case of insufficient hospital beds. 

The experiment consists of 4 conditions, in which the human collaborates with an agent in different forms:
- Team Design Pattern (TDP) 0: baseline. The human has to do everything themselves.
- TDP 1: a decision support agent gives advice on triage decisions. 
- TDP 2: an agent assigns patients to itself it is sure about, and assigns patients to the human in the case of a dilemma (multiple patients but insufficient beds) or otherwise difficult decision. The agent decisions are based on prior value elicited rules from the human. 
- TDP 3: the agent autonomously triages all patients, while the human supervises the process. The agent decisions are based on prior value elicited rules from the human. 

See the paper for a more in-depth overview of the experiment. 

For a more in depth description of the agent triage algorithm used for TDP 2 (dynamic allocation) and TDP 3 (supervised autonomy), see the (Dutch) document `Value elicitation agent algorithm NL.pdf`. 

## How to install 
- Install python3
- `pip install -r requirements.txt` 

## How to run
- For the tutorial: 
  - `python3 main_tutorial.py`
- For the experiment: 
  - `python3 main_exp3.py`
  - Choose the TDP / collaboration form you want to work in. 
- Go to `127.0.0.1:3000`
- ctrl + f5 to clear your cache
- From the dropdown, choose the human doctor
- Press the play button at the top, and the experiment will start. 

## Documentation
The experiment is build using [MATRX](https://github.com/matrx-software/matrx), an open-source framework for simulating human-agent teaming tasks, developed by the [Human-Agent-Robot Teaming (HART)](https://tno-hart.com/) Team at [TNO](https://tno.nl).  For more info, see the [MATRX website](https://github.com/matrx-software/matrx). 
