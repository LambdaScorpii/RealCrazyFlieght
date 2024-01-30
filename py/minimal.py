from rflib.aircraft.generic_controller import RealFlightGenericController
from rflib.utils import logger
from rflib.positioning.motion_commander import MotionCommander


with RealFlightGenericController(link_uri="http://127.0.0.1:18083") as rc:
    with MotionCommander(rc=rc, default_height=2) as mc:
        mc.move_distance(1, 2, 0, 1)
