from datetime import datetime


def setTimestamp():
    """ Get a timestamp with the date and time at the moment the function is called """
    return str(datetime.today().strftime("%d-%m-%Y_%H-%M"))
