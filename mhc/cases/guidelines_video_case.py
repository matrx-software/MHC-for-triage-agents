from matrx import WorldBuilder
from matrx.objects import Wall

from mhc.goals import AllPatientsTriaged
from mhc.hospital_manager import HospitalManager
from mhc.human_agent import HumanDoctor
from mhc.loggers import LogPatientStatus, LogNewPatients, LogTriageDecision
from mhc.patient_agent import PatientAgent

import json
import os
import numpy as np

from mhc.patient_planner import PatientPlanner
from mhc.cases.generic import *
from mhc.helper_functions import setTimestamp


def create_builder():
    world_size = [24, 28]
    bg_color = "#ebebeb"
    wall_color = "#adadad"
    tdp = "baseline"
    timestamp = setTimestamp()

    config_path = os.path.join(os.path.realpath("mhc"), 'cases', 'guidelines_video_config.json')
    config = json.load(open(config_path))
    print("Loaded config file:", config_path)

    np.random.seed(config['random_seed'])
    print("Set random seed:", config['random_seed'])


    # Create our builder instance
    builder = WorldBuilder(shape=world_size, run_matrx_api=True,
                           run_matrx_visualizer=False,
                           visualization_bg_clr=bg_color,
                           visualization_bg_img="", tick_duration=config['world']['tick_duration'],
                           # simulation_goal=150)
                           simulation_goal=AllPatientsTriaged(config['patients']['max_patients']))

    #################################################################
    # Rooms
    ################################################################
    add_mhc_rooms(builder, config, world_size, wall_color)

    #################################################################
    # Beds
    ################################################################
    add_mhc_chairs_beds(builder)

    #################################################################
    # Other objects
    ################################################################
    add_mhc_extras(builder, config)

    # add settings object
    builder.add_object(location=[0, 0], is_traversable=True, is_movable=False, name="Settings", visualize_size=0,
                       tdp=tdp, visualize_your_vs_robot_patients=False,
                       start_timestamp=timestamp, show_agent_predictions=False, trial_completed=False, config=config,
                       end_message=config['world']['trial_end_message'], customizable_properties=['trial_completed'])

    #################################################################
    # Loggers
    ################################################################

    builder.add_logger(LogPatientStatus, save_path=os.path.join('Results', tdp + "_" + timestamp),
                       file_name_prefix="guidelines_video_patient_status",)

    builder.add_logger(LogNewPatients, save_path=os.path.join('Results', tdp + "_" + timestamp),
                       file_name_prefix="guidelines_video_new_patients")

    builder.add_logger(LogTriageDecision, save_path=os.path.join('Results', tdp + "_" + timestamp),
                       file_name_prefix="guidelines_video_triage_decisions")

    #################################################################
    # Actors
    ################################################################

    # create the patient planner (god agent) that spawns patients over time, as described in the config
    builder.add_agent(location=[0, 0], is_traversable=True, is_movable=False,
                      agent_brain=PatientPlanner(config=config, tdp=tdp),
                      name="Patient planner", visualize_size=0)

    # add the test subject: the human doctor
    builder.add_human_agent(location=config['human_doctor']['location'], is_traversable=True, is_movable=False,
                            agent=HumanDoctor(), name="human_doctor", visualize_size=0)

    # add the hospital manager (god agent) that takes care of removing deceased patients
    builder.add_agent(location=[0, 0], is_traversable=True, is_movable=False, agent_brain=HospitalManager(),
                      name="hospital_manager", visualize_size=0)



    # Return the builder
    return builder
