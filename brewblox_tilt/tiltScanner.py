"""
Brewblox service for Tilt hydrometer
"""
import asyncio
import csv
import os.path

import bluetooth._bluetooth as bluez
import numpy as np
from aiohttp import web
from brewblox_service import brewblox_logger, features, mqtt, repeater, strex
from pint import UnitRegistry

from . import blescan

LOGGER = brewblox_logger("brewblox_tilt")
ureg = UnitRegistry()
Q_ = ureg.Quantity

IDS = {
    "a495bb10c5b14b44b5121370f02d74de": "Red",
    "a495bb20c5b14b44b5121370f02d74de": "Green",
    "a495bb30c5b14b44b5121370f02d74de": "Black",
    "a495bb40c5b14b44b5121370f02d74de": "Purple",
    "a495bb50c5b14b44b5121370f02d74de": "Orange",
    "a495bb60c5b14b44b5121370f02d74de": "Blue",
    "a495bb70c5b14b44b5121370f02d74de": "Yellow",
    "a495bb80c5b14b44b5121370f02d74de": "Pink"
}

SG_CAL_FILE_PATH = "/share/SGCal.csv"
TEMP_CAL_FILE_PATH = "/share/tempCal.csv"


def setup(app):
    features.add(app, TiltScanner(app))


class Calibrator():
    def __init__(self, file):
        self.calTables = {}
        self.calPolys = {}
        self.loadFile(file)

    def loadFile(self, file):
        if not os.path.exists(file):
            LOGGER.warning("Calibration file not found: {} . Calibrated "
                           "values won\'t be provided.".format(file))
            return

        # Load calibration CSV
        with open(file, "r", newline="") as f:
            reader = csv.reader(f, delimiter=",")
            for line in reader:
                colour = None
                uncal = None
                cal = None

                try:
                    uncal = float(line[1].strip())
                except ValueError:
                    LOGGER.warning(
                        (
                            "Uncal value not a float \'{}\'. Ignoring line."
                        ).format(line[1]))
                    continue

                try:
                    cal = float(line[2].strip())
                except ValueError:
                    LOGGER.warning(
                        "Cal value not a float \'{}\'. Ignoring line.".format(
                            line[2]))
                    continue

                colour = line[0].strip().capitalize()
                if colour not in IDS.values():
                    LOGGER.warning(
                        "Unknown tilt colour \'{}\'. Ignoring line.".format(
                            line[0]))
                    continue

                if colour not in self.calTables:
                    self.calTables[colour] = {
                        "uncal": [],
                        "cal": []
                    }

                self.calTables[colour]["uncal"].append(uncal)
                self.calTables[colour]["cal"].append(cal)

        # Use polyfit to fit a cubic polynomial curve to calibration values
        # Then create a polynomical from the values produced by polyfit
        for colour in self.calTables:
            x = np.array(self.calTables[colour]["uncal"])
            y = np.array(self.calTables[colour]["cal"])
            z = np.polyfit(x, y, 3)
            self.calPolys[colour] = np.poly1d(z)

        LOGGER.info("Calibration file {} loaded for colours: {}".format(
            file,
            ", ".join(self.calPolys.keys())))

    def calValue(self, colour, value, roundPlaces=0):
        # Use polynomials calculated above to calibrate values
        if colour in self.calPolys:
            return round(self.calPolys[colour](value), roundPlaces)
        else:
            return None


class MessageHandler():
    def __init__(self, app):
        self.tiltsFound = set()
        self.noDevicesFound = True
        self.message = {}
        self.lowerBound = app["config"]["lower_bound"]
        self.upperBound = app["config"]["upper_bound"]

        self.sgCal = Calibrator(SG_CAL_FILE_PATH)
        self.tempCal = Calibrator(TEMP_CAL_FILE_PATH)

    def getMessage(self):
        return self.message

    def clearMessage(self):
        self.message = {}

    def popMessage(self):
        message = self.getMessage()
        self.clearMessage()
        return message

    def decodeData(self, data):
        # Tilt uses a similar data layout to iBeacons accross manufacturer data
        # hex digits 8 - 50. Digits 8-40 contain the ID of the "colour" of the
        # device. Digits 40-44 contain the temperature in f as an integer.
        # Digits 44-48 contain the specific gravity * 1000 (i.e. the "points)
        # as an integer.
        colour = IDS.get(data["uuid"], None)

        if colour is None:
            # UUID is not for a Tilt
            return None

        temp_f = data["major"]

        raw_sg = data["minor"]
        sg = raw_sg/1000

        return {
            "colour": colour,
            "temp_f": temp_f,
            "sg": sg
        }

    def publishData(self,
                    colour,
                    temp_f,
                    cal_temp_f,
                    temp_c,
                    cal_temp_c,
                    sg,
                    cal_sg,
                    plato,
                    cal_plato,
                    rssi):
        self.message[colour] = {
            "Temperature[degF]": temp_f,
            "Temperature[degC]": temp_c,
            "Specific gravity": sg,
            "Signal strength[dBm]": rssi,
            "Plato[degP]": plato
        }

        if cal_temp_f is not None:
            self.message[colour]["Calibrated temperature[degF]"] = cal_temp_f
        if cal_temp_c is not None:
            self.message[colour]["Calibrated temperature[degC]"] = cal_temp_c
        if cal_sg is not None:
            self.message[colour]["Calibrated specific gravity"] = cal_sg
        if cal_plato is not None:
            self.message[colour]["Calibrated plato[degP]"] = cal_plato

        LOGGER.debug(self.message[colour])

    def sgToPlato(self, sg):
        if sg is None:
            return None
        # From https://www.brewersfriend.com/plato-to-sg-conversion-chart/
        plato = ((-1 * 616.868)
                 + (1111.14 * sg)
                 - (630.272 * sg**2)
                 + (135.997 * sg**3))
        return plato

    def degFToDegC(self, degF):
        if degF is None:
            return None
        return Q_(degF, ureg.degF).to("degC").magnitude

    def handleData(self, data):
        decodedData = self.decodeData(data)
        if decodedData is None:
            return

        colour = decodedData["colour"]

        if colour not in self.tiltsFound:
            self.tiltsFound.add(colour)
            LOGGER.info("Found Tilt: {}".format(colour))

        raw_temp_f = decodedData["temp_f"]
        raw_temp_c = self.degFToDegC(raw_temp_f)

        cal_temp_f = self.tempCal.calValue(colour, raw_temp_f)
        cal_temp_c = self.degFToDegC(cal_temp_f)

        raw_sg = decodedData["sg"]
        cal_sg = self.sgCal.calValue(colour, raw_sg, 3)

        if raw_sg < self.lowerBound or raw_sg > self.upperBound:
            LOGGER.warn(f"Discarding message. raw_sg={raw_sg} bounds=[{self.lowerBound}, {self.upperBound}]")
            return

        raw_plato = self.sgToPlato(raw_sg)
        cal_plato = self.sgToPlato(cal_sg)

        self.publishData(
            colour,
            raw_temp_f,
            cal_temp_f,
            raw_temp_c,
            cal_temp_c,
            raw_sg,
            cal_sg,
            raw_plato,
            cal_plato,
            data["rssi"])


class TiltScanner(repeater.RepeaterFeature):
    def __init__(self, app: web.Application):
        super().__init__(app)
        self.sock = None
        self.messageHandler = MessageHandler(app)

    # Implements RepeaterFeature.prepare()
    # The function is called once during startup
    async def prepare(self):
        self.name = self.app["config"]["name"]  # The unique service name
        self.historyTopic = self.app["config"]["history_topic"] + f"/{self.name}"
        LOGGER.info("Started TiltScanner")

        try:
            self.sock = bluez.hci_open_dev(0)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error(f"Error accessing bluetooth device: {strex(e)}")
            await asyncio.sleep(10)  # Avoid lockup caused by service reboots
            raise web.GracefulExit(1)

        blescan.hci_enable_le_scan(self.sock)

    # Implements RepeaterFeature.run()
    # The function is called in a loop until service stops,
    # or a RepeaterCancelled error is raised
    async def run(self):
        message = self._processSocket(self.sock)
        if message:
            await self._publishMessage(message)

    def _processSocket(self, sock):
        try:
            for data in blescan.parse_events(sock, 10):
                self.messageHandler.handleData(data)
            return self.messageHandler.popMessage()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error(
                f"Error accessing bluetooth device whilst scanning: {strex(e)}")
            raise web.GracefulExit(1)

    async def _publishMessage(self, message):
        LOGGER.debug(message)

        # Publish history data
        await mqtt.publish(self.app,
                           self.historyTopic,
                           {
                               "key": self.name,
                               "data": message,
                           },
                           err=False)
