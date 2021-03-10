
from matrx import WorldBuilder
from matrx.objects import Wall

def add_bed(builder: WorldBuilder, top_loc, room):
    """ Add one bed to the MATRX world

    Parameters
    ----------
    builder
        The MATRX world builder
    top_loc
        the coordinate of the top part of the bed
    room
        the hospital room in which the bed is located

    """
    # Add top half of bed with the room
    builder.add_object(location=top_loc, is_traversable=False,
                       is_movable=False, name="Bed_top", assigned_patient='free',
                       img_name="bed_top.png", room=room, customizable_properties=['assigned_patient'])
    # Add bottom half of bed
    bot_loc = [top_loc[0], top_loc[1] + 1]
    builder.add_object(location=bot_loc, is_traversable=False,
                       is_movable=False, name="Bed_bottom",
                       img_name="bed_bottom.png")

def add_chair(builder: WorldBuilder, top_loc, room):
    """ Add one chair to the MATRX world

    Parameters
    ----------
    builder
        The MATRX world builder
    top_loc
        the coordinate of the top part of the bed
    room
        the hospital room in which the bed is located
    """
    # Add top half of bed with the room
    builder.add_object(location=top_loc, is_traversable=False,
                       is_movable=False, name="Bed_top", assigned_patient='free',
                       img_name="chair_top.png", room=room, customizable_properties=['assigned_patient'])
    # Add bottom half of bed
    bot_loc = [top_loc[0], top_loc[1] + 1]
    builder.add_object(location=bot_loc, is_traversable=False,
                       is_movable=False, name="Bed_bottom",
                       img_name="chair_bottom.png")


def add_mhc_rooms(builder, config, world_size, wall_color):
    """ Adds the MHC hospital rooms and walls

    Parameters
    ----------
    builder
        The MATRX world builder
    config
        A dict containing the configuration for this condition, such as the entrance locations and such
    """
    #################################################################
    # Rooms
    ################################################################

    # Add the walls surrounding the hospital with the entrance and exit doors
    builder.add_room(top_left_location=[0, 0], width=world_size[0], height=world_size[1], name="Borders",
                     doors_open=True, door_locations=[tuple(config['hospital']['entrance']),
                                                      tuple(config['hospital']['entrance2']),
                                                      tuple(config['hospital']['exit']),
                                                      tuple(config['hospital']['exit2'])])

    # Add the walls of the different rooms

    builder.add_line(start=[5, 9], end=[22, 9], name="Room wall",
                     callable_class=Wall, visualize_colour=wall_color)
    builder.add_line(start=[5, 10], end=[5, 12], name="Room wall",
                     callable_class=Wall, visualize_colour=wall_color)
    builder.add_line(start=[5, 15], end=[22, 15], name="Room wall",
                     callable_class=Wall, visualize_colour=wall_color)
    builder.add_line(start=[5, 24], end=[22, 24], name="Room wall",
                     callable_class=Wall, visualize_colour=wall_color)
    builder.add_line(start=[5, 16], end=[5, 20], name="Room wall",
                     callable_class=Wall, visualize_colour=wall_color)


def add_mhc_chairs_beds(builder):
    """ Add the beds for the MHC triage cases

    Parameters
    ----------
    builder
        The MATRX builder
    """
    # Add beds in first aid
    add_chair(builder, top_loc=[6, 3], room="eerste hulp")
    # add_chair(builder, top_loc=[9, 3], room="eerste hulp")
    add_chair(builder, top_loc=[12, 3], room="eerste hulp")
    # add_chair(builder, top_loc=[15, 3], room="eerste hulp")
    add_chair(builder, top_loc=[18, 3], room="eerste hulp")
    # add_chair(builder, top_loc=[21, 3], room="eerste hulp")
    add_chair(builder, top_loc=[6, 6], room="eerste hulp")
    # add_chair(builder, top_loc=[9, 6], room="eerste hulp")
    add_chair(builder, top_loc=[12, 6], room="eerste hulp")
    # add_chair(builder, top_loc=[15, 6], room="eerste hulp")
    add_chair(builder, top_loc=[18, 6], room="eerste hulp")
    # add_chair(builder, top_loc=[21, 6], room="eerste hulp")

    # Add beds in IC
    add_bed(builder, top_loc=[8, 11], room="IC")
    builder.add_object(location=[9, 11], is_traversable=False,
                       is_movable=False, name="IV", assigned_patient='free',
                       img_name="iv_drip.png")
    builder.add_object(location=[8, 13], is_traversable=False,
                       is_movable=False, name="heart_monitor", assigned_patient='free',
                       img_name="heart_monitor.png")
    add_bed(builder, top_loc=[14, 11], room="IC")
    builder.add_object(location=[15, 11], is_traversable=False,
                       is_movable=False, name="IV", assigned_patient='free',
                       img_name="iv_drip.png")
    builder.add_object(location=[14, 13], is_traversable=False,
                       is_movable=False, name="heart_monitor", assigned_patient='free',
                       img_name="heart_monitor.png")
    add_bed(builder, top_loc=[20, 11], room="IC")
    builder.add_object(location=[21, 11], is_traversable=False,
                       is_movable=False, name="IV", assigned_patient='free',
                       img_name="iv_drip.png")
    builder.add_object(location=[20, 13], is_traversable=False,
                       is_movable=False, name="heart_monitor", assigned_patient='free',
                       img_name="heart_monitor.png")

    # Add beds in Ward
    add_bed(builder, top_loc=[16, 17], room="ziekenboeg")
    add_bed(builder, top_loc=[12, 17], room="ziekenboeg")
    add_bed(builder, top_loc=[20, 17], room="ziekenboeg")
    add_bed(builder, top_loc=[20, 20], room="ziekenboeg")
    add_bed(builder, top_loc=[16, 20], room="ziekenboeg")
    add_bed(builder, top_loc=[12, 20], room="ziekenboeg")
    # add_bed(builder, top_loc=[8, 20], room="ziekenboeg")


def add_mhc_extras(builder, config):
    """ Add the extras such as signs to the mhc world

    Parameters
    ----------
    builder
        The MATRX world builder

    config
        A dict containing the configuration for this condition, such as the location of texts and such
    """

    # add the entrance icon
    builder.add_object(location=tuple(config['hospital']['entrance']), is_traversable=True, name="entrance arrow1",
                       img_name="arrow.png", visualize_size=0.8)
    builder.add_object(location=tuple(config['hospital']['entrance2']), is_traversable=True, name="entrance arrow2",
                       img_name="arrow.png", visualize_size=0.8)

    # add the exit icons
    builder.add_object(location=tuple(config['hospital']['exit']), is_traversable=True, name="exit sign1",
                       img_name="exit_top.png")
    builder.add_object(location=tuple(config['hospital']['exit2']), is_traversable=True, name="exit sign2",
                       img_name="exit_bottom.png")

    # add room signs
    builder.add_object(location=[8, 2], is_traversable=True, name="waiting room sign",
                       img_name="first_help_sign.png", visualize_depth=110, visualize_size=3)
    builder.add_object(location=[8, 15], is_traversable=True, name="ward sign",
                       img_name="ward_sign_new.png", visualize_depth=110, visualize_size=3)
    builder.add_object(location=[8, 9], is_traversable=True, name="IC sign",
                       img_name="IC_sign_new.png", visualize_depth=110, visualize_size=3)
    builder.add_object(location=[8, 24], is_traversable=True, name="home sign",
                       img_name="home_sign.png", visualize_depth=110, visualize_size=3)

