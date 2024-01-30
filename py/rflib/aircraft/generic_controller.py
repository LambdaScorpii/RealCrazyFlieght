#  Copyright (C) 2024 LambdaScorpii
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
The Real Flight Connector class takes care of controlling the aircraft in RealFlight via the Script. The Class comunicates with Realflight via Flight Axis and SOAP Requests. The class is based on the works in: https://github.com/camdeno/F16Capstone.

The Connector also enables to use the same syntax in the simulation as with the real crazyflie, achieveing, that the "with SyncCrazyflie...." can be copied without too much modifications. Actual class can be found at https://github.com/bitcraze/crazyflie-lib-python

Example: 
*Python*

with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    with MotionCommander(scf, default_height=0.5, default_velocity=0.2) as mc:
    mc.forward(1.0)
    mc.land()

"""
import io
import logging
from queue import Empty
import time
from numpy import append


import pandas
import requests
from bs4 import BeautifulSoup


class RealFlightGenericController:
    """
    Main Class for handling connection and communication between the script and FlightAxis.

    """

    def __init__(
        self, link_uri: str = "http://127.0.0.1:18083", max_velocity: float = 1
    ):
        self.realflight_url = link_uri
        self.channels = 12
        self.channel_default = [
            0.5,
            0.5,
            0.5,
            0.5,
            0.0,
            0.0,
            0.0,
            1,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
        self.channel_values = self.channel_default
        # input 0 = Channel 1, Roll:  0.0 - 1.0 ; In Loiter 0.5 for Roll, Pitch, Yaw to Hover
        # input 1 = Channel 2, Pitch: 0.0 - 1.0
        # input 2 = Channel 3, Throttle: 0.0 - 1.0
        # input 3 = Channel 4, Yaw: 0.0 - 1.0
        # input 7 = Channel 8, Mode: 0.0; 0.5; 1.0
        # input 6 = Channel 7, Headless Mode: 0.0. 1.0
        self.max_velocity = max_velocity
        self.telemetry = pandas.DataFrame(
            columns=(
                "T",
                "Airspeed",
                "Aircraft X",
                "Aircraft Y",
                "Altitude above Ground",
                "Roll",
                "Pitch",
                "Yaw",
                "Flying",
            ),
            index=[0],
        )
        self.start = time.time()

    def __enter__(self):
        try:
            logging.info("Attempting connection")
            self.enable()
            self.reset_aircraft()
            self.update_rc_value()
            return self
        except Empty as excep:
            logging.error(
                "Could not connect to RealFlight. Please Check if RealFlight is running. Error: %s",
                excep,
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            logging.debug("attempting to close connection")
            self.reset_aircraft()
            self.disable()
        except Empty as excep:
            logging.error(
                "Could not reset Simulation. Please restart RealFlight manually. Erros: %s",
                excep,
            )

    def post_soap_request(self, header: dict[str, str], body: str) -> bytes:
        """
        Method Used to structurally send messages via SOAP.
        """
        response = requests.post(
            self.realflight_url, data=body, headers=header, timeout=10
        )
        return response.content

    def disable(self) -> bytes:
        """
        Used to specifically disable the RC and puts back the original Controller.
        """

        header = {
            "content-type": "text/xml;charset='UTF-8'",
            "soapaction": "RestoreOriginalControllerDevice",
            "Connection": "Keep-Alive",
        }

        body = "<?xml version='1.0' encoding='UTF-8'?>\
        <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>\
        <soap:Body>\
        <RestoreOriginalControllerDevice><a>1</a><b>2</b></RestoreOriginalControllerDevice>\
        </soap:Body>\
        </soap:Envelope>"

        message = self.post_soap_request(header=header, body=body)
        return message

    def reset_aircraft(self) -> bytes:
        """
        Attempts to reset the RealFlight instance
        NOTE: If reset fails, RealFlight needs to be restarted manually to use normal controller
        """
        header = {
            "content-type": "text/xml;charset='UTF-8'",
            "soapaction": "ResetAircraft",
        }
        body = "<?xml version='1.0' encoding='UTF-8'?>\
        <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>\
        <soap:Body>\
        <ResetAircraft><a>1</a><b>2</b></ResetAircraft>\
        </soap:Body>\
        </soap:Envelope>"

        message = self.post_soap_request(header=header, body=body)
        self.telemetry = pandas.DataFrame(columns=self.telemetry.columns)
        self.start = time.time()
        self.channel_values = [0.5, 0.5, 0, 0.5, 0.0, 0.0, 0.0, 1, 0.0, 0.0, 0.0, 0.0]
        self.update_rc_value()
        return message

    def enable(self) -> bytes:
        """
        Enables the Airccraft and disables the original Controller.

        NOTE: If reset fails, RealFlight needs to be restarted manually to use normal controller
        """

        header = {
            "content-type": "text/xml;charset='UTF-8'",
            "soapaction": "InjectUAVControllerInterface",
        }

        body = "<?xml version='1.0' encoding='UTF-8'?>\
        <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>\
        <soap:Body>\
        <InjectUAVControllerInterface><a>1</a><b>2</b></InjectUAVControllerInterface>\
        </soap:Body>\
        </soap:Envelope>"

        message = self.post_soap_request(header=header, body=body)
        return message

    def update_rc_value(self) -> None:
        """
        Set the control inputs, and get the states
        Return True if the response was OK
        """
        header = {
            "content-type": "text/xml;charset='UTF-8'",
            "soapaction": "ExchangeData",
        }

        body = f"<?xml version='1.0' encoding='UTF-8'?><soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>\
        <soap:Body>\
        <ExchangeData>\
        <pControlInputs>\
        <m-selectedChannels>4095</m-selectedChannels>\
        <m-channelValues-0to1>\
        <item>{self.channel_values[0]}</item>\
        <item>{self.channel_values[1]}</item>\
        <item>{self.channel_values[2]}</item>\
        <item>{self.channel_values[3]}</item>\
        <item>{self.channel_values[4]}</item>\
        <item>{self.channel_values[5]}</item>\
        <item>{self.channel_values[6]}</item>\
        <item>{self.channel_values[7]}</item>\
        <item>{self.channel_values[8]}</item>\
        <item>{self.channel_values[9]}</item>\
        <item>{self.channel_values[10]}</item>\
        <item>{self.channel_values[11]}</item>\
        </m-channelValues-0to1>\
        </pControlInputs>\
        </ExchangeData>\
        </soap:Body>\
        </soap:Envelope>"

        try:
            response = self.post_soap_request(header=header, body=body)
            self.update_telemetry(response)
            # print("%s", response)
        except Empty as excep:
            logging.error(
                "Could not update Channel Values. Please Correct Input. Error: %s",
                excep,
            )

    def update_telemetry(self, soap_response: bytes) -> None:
        response_soup = BeautifulSoup(soap_response, features="xml")
        response_formatted = response_soup.find("m-aircraftState").prettify()  # type: ignore

        response_df = pandas.read_xml(
            io.StringIO(response_formatted), xpath="//m-aircraftState"
        )

        T = time.time() - self.start

        row = pandas.DataFrame(
            {
                "T": round(T, 3),
                "Airspeed": round(response_df.at[0, "m-airspeed-MPS"], 2),
                "Aircraft X": round(response_df.at[0, "m-aircraftPositionX-MTR"], 2),
                "Aircraft Y": round(response_df.at[0, "m-aircraftPositionY-MTR"], 2),
                "Altitude above Ground": round(
                    response_df.at[0, "m-altitudeAGL-MTR"], 2
                ),
                "Roll": round(response_df.at[0, "m-roll-DEG"], 2),
                "Pitch": round(response_df.at[0, "m-inclination-DEG"], 2),
                "Yaw": round(response_df.at[0, "m-azimuth-DEG"], 2),
                "Flying": response_df.at[0, "m-currentAircraftStatus"],
            },
            index=[0],
        )

        self.telemetry = row
        if not self.channel_values == self.channel_default:
            row.to_csv("telemetry.log", mode="a", header=False, index=False)

    def convert_motion_in_channel_values(
        self,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
        velocity_z: float = 0.0,
        rate_yaw: float = 0.0,
    ) -> None:
        """
        positive X is forward
        positive Y is left
        positive Z is up
        positive yaw is turn left"""

        roll = 0.5 - (velocity_y * 3.6 / 9.5) / 2
        pitch = 0.5 + (velocity_x * 3.6 / 9.5) / 2
        throttle = 0.5 + (velocity_z * 3.6 / 13.5) / 2
        if velocity_z < 0:
            throttle = 0.5 + (velocity_z * 3.6 / 7) / 2

        yaw = 0.5 + (rate_yaw) / 2

        self.channel_values = [
            roll,
            pitch,
            throttle,
            yaw,
            0.0,
            0.0,
            0.0,
            1,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
        logging.debug("Channel Values: %s", self.channel_values)
        self.update_rc_value()
        # input 0 = Channel 1, Roll:  0.0 - 1.0 ; In Loiter 0.5 for Roll, Pitch, Yaw to Hover
        # input 1 = Channel 2, Pitch: 0.0 - 1.0
        # input 2 = Channel 3, Throttle: 0.0 - 1.0
        # input 3 = Channel 4, Yaw: 0.0 - 1.0
        # input 7 = Channel 8, Mode: 0.0; 0.5; 1.0
        # input 6 = Channel 7, Headless Mode: 0.0. 1.0
