#  Copyright (C) 2023 Hochschule RheinMain
#
#  This program is free software;
#  you can redistribute it and/or modify it under the terms of the
#  Creative Commons Attribution-NonCommercial-ShareAlike License;
#  either version 3.0 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See https://creativecommons.org/licenses/by-nc-sa/3.0/ for more License Details.

"""
This Module is used to reserve a Dummy Crazyflie instance, to simulate the behaviour if you would 121 paste and copy the code to an actual Carzyflie Script. Original Crazyflie class can be found at: https://github.com/bitcraze/crazyflie-lib-python
"""

import logging


class Crazyflie:
    def __init__(self, link=None, ro_cache=None, rw_cache=None):
        """
        Create a Dummy Crazyflie class to act as a placeholder to have as little modificatiuons in Scripts between Simulation and real Crazyflie
        """
        logging.debug("crazyflie class established")
