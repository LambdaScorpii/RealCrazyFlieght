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
This is the Main Function making Use of the adapted Crazyflie Modules to be used within Realflight. 
At Current Development, only the Motion Commander Library can be used.
"""

# Import SystemLibraries

import logging
import sys
from pathlib import Path
import time

# Import  pip installed Dependencies

from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Slot, QObject, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidgetItem,
    QGroupBox,
    QDoubleSpinBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plot

# from mpl_toolkits.mplot3d import Axes3D
import pandas
import numpy as np


from ui.wrapper_mainwindow import Ui_MainWindow
from rflib.aircraft.generic_controller import RealFlightGenericController
from rflib.utils import logger
from rflib.positioning.motion_commander import MotionCommander


VERSION = "v2023.12.21"
THIS_PATH = Path(__file__).parent.resolve()


class MainWindow(QMainWindow):
    """Main Window to class to Create and initialize all Widgets"""

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ---------Inital Values
        self.setWindowTitle("CrazyFlie Simulator")
        self.setWindowIcon(QIcon("py/ui/logo.png"))
        self.rc: RealFlightGenericController
        self.mc: MotionCommander
        self.timer = QTimer()
        with open("application.log", "w"):
            pass
        with open("telemetry.log", "w"):
            pass

        self.setpoints_distance = pandas.DataFrame(
            {
                "T": [0],
                "distance_forward": 0,
                "distance_left": 0,
                "distance_right": 0,
                "distance_back": 0,
                "distance_up": 0,
                "distance_down": 0,
                "distance_turn_left": 0,
                "distance_turn_right": 0,
            }
        )

        self.setpoints_velocity = pandas.DataFrame(
            {
                "T": [0],
                "velocity_forward": 0,
                "velocity_left": 0,
                "velocity_right": 0,
                "velocity_back": 0,
                "velocity_up": 0,
                "velocity_down": 0,
                "velocity_turn_left": 0,
                "velocity_turn_right": 0,
            }
        )

        self.telemetry_data = pandas.DataFrame(
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
            )
        )

        self.telemetry_units = pandas.DataFrame(
            {
                "T": ["s"],
                "Airspeed": "m/s",
                "Aircraft X": "m",
                "Aircraft Y": "m",
                "Altitude above Ground": "m",
                "Roll": "°",
                "Pitch": "°",
                "Yaw": "°",
                "Flying": "",
            }
        )

        self.fly_mode = "move_distance"

        # ------ Menu
        # self.menu = self.menuBar()
        # self.menu_file = self.menu.addMenu("File")
        # # quit = QAction("Quit", self, triggered=qApp.quit)
        # menu_quit = QAction(self)
        # self.menu_file.addAction(menu_quit)
        # menu_quit.setText("Quit")
        # menu_quit.triggered.connect(QApplication.qui

        # ----- Prelimineary Checks

        # ----------Styling
        # self.ui.toolButton.setIcon(QIcon("UI/logo.png"))
        logging.info("GUI Loaded.")
        self.load_style_sheet()

        # ----- setup Widgets
        self.setup_input_fields()
        self.setup_table_view()
        self.setup_plot()
        self.setup_buttons()
        self.timer.setInterval(900)
        self.timer.timeout.connect(self.update_canvas)
        self.timer.start()
        # ------------Signal and Slots connections

    def load_style_sheet(self) -> None:
        """Used to initialize Sylesheet"""
        qss_file = f"{THIS_PATH}/ui/stylesheet.css"
        # logging.info("opening qss file at %s", qss_file)
        with open(qss_file, mode="r", encoding="utf-8") as qss:
            self.setStyleSheet(qss.read())
        logging.info("StyleSheet applied.")

    def setup_input_fields(self) -> None:
        """Initialize Input Fields, setup DataFrame for Setpoints and connect Slots"""

        input_distance: list[QDoubleSpinBox] = self.ui.group_move_distance.findChildren(
            QDoubleSpinBox
        )
        input_velovity: list[
            QDoubleSpinBox
        ] = self.ui.group_continous_motion.findChildren(QDoubleSpinBox)

        # for spin_box in input_distance:
        #     spin_box.valueChanged.connect(self.update_distance_setpoint)

        # for spin_box in input_velovity:
        #     spin_box.valueChanged.connect(self.update_velocity_setpoint)

    def setup_table_view(self) -> None:
        # row_count = self.telemetry_data.count(axis="columns")
        self.ui.table_telemetry.setRowCount(self.telemetry_data.shape[1])
        self.ui.table_telemetry.setColumnCount(2)
        self.ui.table_telemetry.setHorizontalHeaderLabels(["Data Point", "Value"])

    def setup_plot(self) -> None:
        plot.style.use("seaborn-v0_8-darkgrid")
        self.plot = plot.figure(figsize=(7.5, 5))
        self.canvas = FigureCanvas(self.plot)
        self.ui.gridLayout_plot.addWidget(self.canvas)
        self.plot.set_canvas(self.canvas)
        self.plot_axes = self.canvas.figure.add_subplot()
        # self.plot_axes = self.canvas.figure.add_sublot(111,projection= '3d')
        self.plot.suptitle("Aircraft Position (m)")

    def setup_buttons(self) -> None:
        self.ui.button_connect.clicked.connect(self.slot_connect)
        self.ui.button_disconnect.clicked.connect(self.slot_disconnect)
        self.ui.button_takeoff.clicked.connect(self.slot_takeoff)
        self.ui.button_hover.clicked.connect(self.slot_hover)
        self.ui.button_fly.clicked.connect(self.slot_fly)
        self.ui.button_land.clicked.connect(self.slot_land)
        self.ui.button_reset.clicked.connect(self.slot_reset)
        self.ui.group_move_distance.clicked.connect(self.slot_set_fly_mode)
        self.ui.group_continous_motion.clicked.connect(self.slot_set_fly_mode)

        self.ui.button_disconnect.setDisabled(True)
        self.ui.button_takeoff.setDisabled(True)
        self.ui.button_hover.setDisabled(True)
        self.ui.button_fly.setDisabled(True)
        self.ui.button_land.setDisabled(True)
        self.ui.button_reset.setDisabled(True)

    #  ---------------- Update Functions
    def update_plot(self) -> None:
        # data_point_limit = 10
        # indices = np.linspace(
        #     0, len(self.telemetry_data) - 1, data_point_limit, dtype=int
        # )

        self.plot_axes.scatter(
            self.telemetry_data["Aircraft X"].iloc[-1],
            self.telemetry_data["Aircraft Y"].iloc[-1],
            # self.telemetry_data["Altitude above Ground"],
            s=60,
            color="blue",
            label="Telemetry Data",
        )

        self.plot_axes.plot(
            self.telemetry_data["Aircraft X"],
            self.telemetry_data["Aircraft Y"],
            # self.telemetry_data["Altitude above Ground"],
            color="gray",
            alpha=0.7,
            label="Trajectory",
        )

        self.plot_axes.set_xlabel("X Position")
        self.plot_axes.set_ylabel("Y Position")

        u = v = np.ones(1)
        self.plot_axes.quiver(
            self.telemetry_data["Aircraft X"].iloc[-1],
            self.telemetry_data["Aircraft Y"].iloc[-1],
            u,
            v,
            angles=self.telemetry_data["Yaw"].iloc[-1] + 90,
            width=0.004,
        )

        # arrow_length = 10
        # direction_x = arrow_length * np.cos(np.deg2rad(self.telemetry_data["Yaw"]))
        # direction_y = arrow_length * np.sin(np.deg2rad(self.telemetry_data["Yaw"]))
        # # direction_z = np.zeros_like(direction_x)
        # self.plot_axes.quiver(
        #     self.telemetry_data["Aircraft Y"],
        #     self.telemetry_data["Aircraft X"],
        #     self.telemetry_data["Altitude above Ground"],
        #     direction_x,
        #     direction_y,
        #     direction_z,
        #     length=0.05,
        #     normalize=True,
        #     color="black",
        #     label="Direction",
        #     arrow_length_ratio=0.2,
        # )

        # self.plot_axes.plot(
        #     self.telemetry_data["Aircraft X"],
        #     self.telemetry_data["Aircraft Y"],
        # )

        # self.plot_axes.plot(
        #     1, 0, ">k", transform=self.plot_axes.get_yaxis_transform(), clip_on=False
        # )
        # self.plot_axes.plot(
        #     0, 1, "^k", transform=self.plot_axes.get_xaxis_transform(), clip_on=False
        # )
        self.canvas.draw()

    def update_table_data(self):
        telemetry_data = pandas.concat(
            [self.telemetry_data, self.telemetry_units], ignore_index=True
        )

        max_row = telemetry_data.shape[0] - 1
        table_row = 0
        for column in telemetry_data:
            table_descriptor = QTableWidgetItem(f"{column}")
            table_descriptor.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            table_descriptor.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            self.ui.table_telemetry.setItem(table_row, 0, table_descriptor)
            table_item = QTableWidgetItem(
                f"{telemetry_data.at[max_row-1, column]} {telemetry_data.at[max_row, column]}"
            )
            table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            self.ui.table_telemetry.setItem(table_row, 1, table_item)
            table_row += 1

        self.ui.table_telemetry.resizeColumnsToContents()
        self.ui.table_telemetry.resizeRowsToContents()

    #  --------------- Slot Functions

    @Slot()
    def slot_set_fly_mode(self) -> None:
        """analyze which toggle Button is switched on to determine respective Fly mode"""

        self.ui.group_continous_motion.setChecked(False)
        self.ui.group_move_distance.setChecked(False)
        sender: QObject = self.sender()
        sender_name = sender.objectName()

        group_box: QGroupBox = sender  # type: ignore
        group_box.setChecked(True)

        self.fly_mode = sender_name.replace("group_", "")

    # @Slot()
    # def update_distance_setpoint(self, value) -> None:
    #     sender: QObject = self.sender()
    #     sender_name = sender.objectName()

    #     self.setpoints_distance.at[0, f"{sender_name.replace('input_', '')}"] = value

    # @Slot()
    # def update_velocity_setpoint(self, value) -> None:
    #     sender: QObject = self.sender()
    #     sender_name = sender.objectName()

    #     self.setpoints_velocity.at[0, f"{sender_name.replace('input_', '')}"] = value

    @Slot()
    def slot_connect(self) -> None:
        self.rc = RealFlightGenericController(link_uri="http://127.0.0.1:18083")
        self.mc = MotionCommander(rc=self.rc, default_height=2)
        self.rc.enable()
        self.rc.reset_aircraft()
        self.rc.update_rc_value()

        self.ui.button_disconnect.setDisabled(False)
        self.ui.button_takeoff.setDisabled(False)
        self.ui.button_hover.setDisabled(False)
        self.ui.button_fly.setDisabled(False)
        self.ui.button_land.setDisabled(False)
        self.ui.button_reset.setDisabled(False)

    @Slot()
    def slot_disconnect(self) -> None:
        if self.mc._is_flying is True:
            self.mc = None
        self.rc.disable()
        self.ui.button_disconnect.setDisabled(True)
        self.ui.button_takeoff.setDisabled(True)
        self.ui.button_hover.setDisabled(True)
        self.ui.button_fly.setDisabled(True)
        self.ui.button_land.setDisabled(True)
        self.ui.button_reset.setDisabled(True)

    @Slot()
    def slot_takeoff(self) -> None:
        self.rc.start = time.time()
        self.mc.take_off(height=2, velocity=1)

    @Slot()
    def slot_hover(self) -> None:
        self.mc.stop()

    @Slot()
    def slot_fly(self) -> None:
        if self.ui.group_move_distance.isChecked():
            distance_x = (
                self.ui.input_distance_forward.value()
                - self.ui.input_distance_back.value()
            )

            distance_y = (
                self.ui.input_distance_left.value()
                - self.ui.input_distance_right.value()
            )
            distance_z = (
                self.ui.input_distance_up.value() - self.ui.input_distance_down.value()
            )
            self.mc.move_distance(
                distance_x_m=distance_x,
                distance_y_m=distance_y,
                distance_z_m=distance_z,
                velocity=1,
            )

            self.mc.turn_left(self.ui.input_distance_turn_left.value(), 120)
            self.mc.turn_right(self.ui.input_distance_turn_right.value(), 120)
        elif self.ui.group_continous_motion.isChecked():
            velocity_x = (
                self.ui.input_velocity_forward.value()
                - self.ui.input_velocity_back.value()
            )

            velocity_y = (
                self.ui.input_velocity_left.value()
                - self.ui.input_velocity_right.value()
            )
            velocity_z = (
                self.ui.input_velocity_up.value() - self.ui.input_velocity_down.value()
            )

            yaw_rate = (
                self.ui.input_velocity_turn_left.value()
                - self.ui.input_velocity_turn_right.value()
            )

            self.mc.start_linear_motion(
                velocity_x_m=velocity_x,
                velocity_y_m=velocity_y,
                velocity_z_m=velocity_z,
                rate_yaw=yaw_rate,
            )

    @Slot()
    def slot_land(self) -> None:
        self.mc.land(velocity=1)
        # self.rc = RealFlightGenericController(link_uri="http://127.0.0.1:18083")
        self.mc = MotionCommander(rc=self.rc, default_height=1.5)

    @Slot()
    def slot_reset(self) -> None:
        self.mc._is_flying = False
        self.mc._thread.stop()
        self.mc._thread = None
        self.rc.reset_aircraft()
        with open("application.log", "w"):
            pass
        with open("telemetry.log", "w"):
            pass
        self.plot_axes.clear()
        self.canvas.draw()

    def update_log(self) -> None:
        with open("application.log", "r", encoding="utf-8") as log:
            entry = log.read()
        self.ui.text_log.setPlainText(entry)

    def update_canvas(self) -> None:
        self.update_telemetry()
        if not self.telemetry_data.empty:
            self.update_plot()
            self.update_table_data()
        self.update_log()

    def update_telemetry(self) -> None:
        self.telemetry_data = pandas.read_csv(
            "telemetry.log",
            header=None,
            names=(
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
            index_col=False,
        )


def main() -> None:
    logger.logging_setup(logging_to_file=True, logging_level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.setBaseSize(1920, 1080)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
