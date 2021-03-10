import os
import requests

from mhc.cases import baseline_case, tdp_decision_support_exp3, tdp_supervised_autonomy, tdp_dynamic_task_allocation
from triage_gui import visualization_server


def run_tdp(test_subject_id, tdp="baseline", user_elicitation_results=None):

    if tdp == "baseline":
        print("#"*30)
        print("Running the Baseline")
        print("#" * 30)
        builder = baseline_case.create_builder(test_subject_id)

        # setup the media folder
        media_folder = os.path.join(os.path.abspath(os.path.realpath("mhc")), 'images')
        builder.startup(media_folder=media_folder)

        # start the custom visualizer
        print("Starting custom visualizer")
        vis_thread = visualization_server.run_matrx_visualizer(verbose=False, media_folder=media_folder)

        # run the world
        world = builder.get_world()
        world.run(builder.api_info)

        # stop the custom visualizer
        print("Shutting down custom visualizer")
        r = requests.get("http://localhost:" + str(visualization_server.port) + "/shutdown_visualizer")
        vis_thread.join()

        # stop MATRX scripts such as the api and visualizer (if used)
        builder.stop()

    elif tdp == "dss":
        print("#" * 50)
        print("Running TDP: decision support with explanations")
        print("#" * 50)
        builder = tdp_decision_support_exp3.create_builder(test_subject_id)

        # setup the media folder
        media_folder = os.path.join(os.path.abspath(os.path.realpath("mhc")), 'images')
        builder.startup(media_folder=media_folder)

        # start the custom visualizer
        vis_thread = visualization_server.run_matrx_visualizer(verbose=False, media_folder=media_folder)

        # run the world
        world = builder.get_world()
        world.run(builder.api_info)

        # stop the custom visualizer
        print("Shutting down custom visualizer")
        r = requests.get("http://localhost:" + str(visualization_server.port) + "/shutdown_visualizer")
        vis_thread.join()

        # stop MATRX scripts such as the api and visualizer (if used)
        builder.stop()

    elif tdp == "dynamic":
        print("#" * 50)
        print("Running TDP: Dynamic Task Allocation")
        print("#" * 50)
        builder = tdp_dynamic_task_allocation.create_builder(user_elicitation_results, test_subject_id)

        # setup the media folder
        media_folder = os.path.join(os.path.abspath(os.path.realpath("mhc")), 'images')
        builder.startup(media_folder=media_folder)

        # start the custom visualizer
        vis_thread = visualization_server.run_matrx_visualizer(verbose=False, media_folder=media_folder)

        # run the world
        world = builder.get_world()
        world.run(builder.api_info)

        # stop the custom visualizer
        print("Shutting down custom visualizer")
        r = requests.get("http://localhost:" + str(visualization_server.port) + "/shutdown_visualizer")
        vis_thread.join()

        # stop MATRX scripts such as the api and visualizer (if used)
        builder.stop()

    elif tdp == "autonomy":
        print("#" * 50)
        print("Running TDP: Supervised Autonomy")
        print("#" * 50)
        builder = tdp_supervised_autonomy.create_builder(user_elicitation_results, test_subject_id)

        # setup the media folder
        media_folder = os.path.join(os.path.abspath(os.path.realpath("mhc")), 'images')
        builder.startup(media_folder=media_folder)

        # start the custom visualizer
        vis_thread = visualization_server.run_matrx_visualizer(verbose=False, media_folder=media_folder)

        # run the world
        world = builder.get_world()
        world.run(builder.api_info)

        # stop the custom visualizer
        print("Shutting down custom visualizer")
        r = requests.get("http://localhost:" + str(visualization_server.port) + "/shutdown_visualizer")
        vis_thread.join()

        # stop MATRX scripts such as the api and visualizer (if used)
        builder.stop()


if __name__ == "__main__":

    # # See options from: https://365tno.sharepoint.com/:w:/r/teams/P060.43326/_layouts/15/Doc.aspx?sourcedoc=%7BA9FFEAC8-50DF-44DD-8104-7505422D1A18%7D&file=Value%20elicitation%20agent%20algorithm.docx&action=default&mobileredirect=true
    # user_elicitation_results = {
    #     "age": 2, # 1, 2 or 3
    #     "gender": 1, # 1, 2 or 3
    #     "profession": 1, # 1, 2 or 3
    #     "home_situation": 1, # 1, 2 or 3
    # }
    #
    # print("running supervised autonomy with test subject 15")
    # run_tdp(15, tdp="dynamic", user_elicitation_results=user_elicitation_results)
    # sys.exit(0)

    print("\n----Welcome to the MHC project experiment 3 ----")
    print("What is the ID of the human guinea pig?")
    test_subject_id = int(input())

    choice = 0
    while not choice == "exit":
        print("\n\nType one of the options shown between brackets: ")
        print("(baseline): Run baseline")
        print("(dss): Run TDP 1: Decision support with explanations")
        print("(dynamic): Run TDP 2: Dynamic allocation")
        print("(autonomy): Run TDP 3: Supervised autonomy")
        print("(exit): Exit")
        print("What do you want to do?")
        choice = input()

        if choice == "exit":
            print("Quitting experiment")
            break


        if choice in ['dynamic', 'autonomy']:
            # question the user elicitation results
            print("\n" + ("#" * 30))
            print("User elicitation results")
            print("#" * 30)

            print("\nWhich option was chosen for age?")
            age = None
            while age is None or int(age) not in [1, 2, 3]:
                age = input()

            print("\nWhich option was chosen for gender?")
            gender = None
            while gender is None or int(gender) not in [1, 2, 3]:
                gender = input()

            print("\nWhich option was chosen for profession?")
            profession = None
            while profession is None or int(profession) not in [1, 2, 3]:
                profession = input()

            print("\nWhich option was chosen for home situation?")
            home_situation = None
            while home_situation is None or int(home_situation) not in [1, 2, 3]:
                home_situation = input()

            # See options from: https://365tno.sharepoint.com/:w:/r/teams/P060.43326/_layouts/15/Doc.aspx?sourcedoc=%7BA9FFEAC8-50DF-44DD-8104-7505422D1A18%7D&file=Value%20elicitation%20agent%20algorithm.docx&action=default&mobileredirect=true
            user_elicitation_results = {
                "age": age,  # 1, 2 or 3
                "gender": gender,  # 1, 2 or 3
                "profession": profession,  # 1, 2 or 3
                "home_situation": home_situation,  # 1, 2 or 3
            }
            print("Running experiment TDP ", choice, " with user elicitation results ", user_elicitation_results)
            run_tdp(test_subject_id, tdp=choice, user_elicitation_results=user_elicitation_results)

        if choice in ["baseline", "dss", "dynamic", "autonomy"]:
            print("Running experiment TDP ", choice)
            run_tdp(test_subject_id, tdp=choice)

        else:
            print("Sorry, did not recognize that option")