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
"""Functions for logging in projects"""
import logging


def logging_setup(
    logging_to_file: bool = False, logging_level: int = logging.DEBUG
) -> None:
    """Setup logging and clear logfile"""

    if logging_to_file:
        log_file_name = "application.log"
        with open(log_file_name, mode="w", encoding="utf-8"):
            pass

    else:
        log_file_name = ""

    logging.basicConfig(
        format="%(asctime)s :: %(levelname)s :: [%(module)s] :: %(message)s",
        level=logging_level,
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=log_file_name,
        encoding="utf-8",
    )

    logging.info("Logger setup complete")


if __name__ == "__main__":
    logging_setup()
    logging.debug("debug")
    logging.info("info")
    logging.warning("warning")
    logging.error("error")
