import os, requests

from triage_gui import visualization_server
from mhc.cases import tutorial_case

if __name__ == "__main__":
    builder = tutorial_case.create_builder()

    # setup the media folder
    media_folder = os.path.join(os.path.abspath(os.path.realpath("mhc")), 'images')
    builder.startup(media_folder=media_folder)

    # start the custom visualizer
    print("Starting custom visualizer")
    vis_thread = visualization_server.run_matrx_visualizer(verbose=False, media_folder=media_folder)

    print("Running the Tutorial")

    # run the world
    world = builder.get_world()
    world.run(builder.api_info)


    # stop the custom visualizer
    print("Shutting down custom visualizer")
    r = requests.get("http://localhost:" + str(visualization_server.port) + "/shutdown_visualizer")
    vis_thread.join()

    # stop MATRX scripts such as the api and visualizer (if used)
    builder.stop()

