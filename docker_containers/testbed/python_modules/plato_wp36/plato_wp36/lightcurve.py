# -*- coding: utf-8 -*-
# lightcurve.py

"""
Classes for representing light curves, either on arbitrary time rasters, or on rasters with fixed step.
"""

import logging
import math
import numpy as np


class LightcurveArbitraryRaster:
    """
    A class representing a lightcurve which is sampled on an arbitrary raster of times.
    """

    def __init__(self, times, fluxes, uncertainties=None, flags=None, metadata=None):
        """
        Create a lightcurve which is sampled on an arbitrary raster of times.

        :param times:
            The times of the data points.
        :type times:
            np.ndarray
        :param fluxes:
            The light fluxes at each data point.
        :type fluxes:
            np.ndarray
        :param uncertainties:
            The uncertainty in each data point.
        :type uncertainties:
            np.ndarray
        :param flags:
            The flag associated with each data point.
        :type flags:
            np.ndarray
        :param metadata:
            The metadata associated with this lightcurve.
        :type metadata:
            dict
        """

        # Check inputs
        assert isinstance(times, np.ndarray)
        assert isinstance(fluxes, np.ndarray)

        # Unset all flags if none were specified
        if flags is not None:
            assert isinstance(flags, np.ndarray)
        else:
            flags = np.zeros_like(times)

        # Make an empty metadata dictionary if none was specified
        if metadata is not None:
            assert isinstance(metadata, dict)
        else:
            metadata = {}

        # Make uncertainty zero if not specified
        if uncertainties is not None:
            assert isinstance(uncertainties, np.ndarray)
        else:
            uncertainties = np.zeros_like(fluxes)

        # Store the data
        self.times = times
        self.fluxes = fluxes
        self.uncertainties = uncertainties
        self.flags = flags
        self.flags_set = True
        self.metadata = metadata

    def estimate_sampling_interval(self):
        """
        Estimate the time step on which this light curve is sampled, with robustness against missing points.

        :return:
            Time step
        """

        differences = np.diff(self.times)
        differences_sorted = np.sort(differences)

        interquartile_range_start = int(len(differences) * 0.25)
        interquartile_range_end = int(len(differences) * 0.75)
        interquartile_data = differences_sorted[interquartile_range_start:interquartile_range_end]

        interquartile_mean = np.mean(interquartile_data)

        # Round time interval to nearest number of integer seconds
        interquartile_mean = round(interquartile_mean * 86400) / 86400

        return float(interquartile_mean)

    def check_fixed_step(self, verbose=True, max_errors=None):
        """
        Check that this light curve is sampled at a fixed time interval. Return the number of errors.

        :param verbose:
            Should we output a logging message about every missing time point?
        :type verbose:
            bool
        :param max_errors:
            The maximum number of errors we should show
        :type max_errors:
            int
        :return:
            int
        """

        abs_tol = 1e-4
        rel_tol = 0

        error_count = 0
        spacing = self.estimate_sampling_interval()

        if verbose:
            logging.info("Time step is {:.15f}".format(spacing))

        differences = np.diff(self.times)

        for index, step in enumerate(differences):
            # If this time point has the correct spacing, it is OK
            if math.isclose(step, spacing, abs_tol=abs_tol, rel_tol=rel_tol):
                continue

            # We have found a problem
            error_count += 1

            # See if we have skipped some time points
            points_missed = step / spacing - 1
            if math.isclose(points_missed, round(points_missed), abs_tol=abs_tol, rel_tol=rel_tol):
                if verbose and (max_errors is None or error_count <= max_errors):
                    logging.info("index {:5d} - {:d} points missing at time {:.5f}".format(index,
                                                                                           int(points_missed),
                                                                                           self.times[index]))
                continue

            # Or is this an entirely unexpected time interval?
            if verbose and (max_errors is None or error_count <= max_errors):
                logging.info("index {:5d} - Unexpected time step {:.15f} at time {:.5f}".format(index,
                                                                                               step,
                                                                                               self.times[index]))

        # Return the verdict on this lightcurve
        return error_count

    def check_fixed_step_v2(self, verbose=True, max_errors=None):
        """
        Check that this light curve is sampled at a fixed time interval. Return the number of errors.

        :param verbose:
            Should we output a logging message about every missing time point?
        :type verbose:
            bool
        :param max_errors:
            The maximum number of errors we should show
        :type max_errors:
            int
        :return:
            int
        """

        abs_tol = 1e-4
        rel_tol = 0

        spacing = self.estimate_sampling_interval()

        if verbose:
            logging.info("Time step is {:.15f}".format(spacing))

        start_time = self.times[0]
        end_time = self.times[-1]
        times = np.arange(start=start_time, stop=end_time, step=spacing)
        error_count = 0

        input_position = 0
        for index, time in enumerate(times):
            while ((not math.isclose(time, self.times[input_position], abs_tol=abs_tol, rel_tol=rel_tol)) and
                   (self.times[input_position] < time)):
                input_position += 1

            # If this time point has the correct spacing, it is OK
            if not math.isclose(time, self.times[input_position], abs_tol=abs_tol, rel_tol=rel_tol):
                if verbose and (max_errors is None or error_count <= max_errors):
                    logging.info("index {:5d} - Point missing at time {:.15f}".format(index,
                                                                                     self.times[index]))
                error_count += 1

        # Return the verdict on this lightcurve
        return error_count

    def to_fixed_step(self):
        """
        Convert this lightcurve to a fixed time stride

        :return:
            [LightcurveFixedStep]
        """

        spacing = self.estimate_sampling_interval()
        start_time = self.times[0]
        end_time = self.times[-1]
        times = np.arange(start=start_time, stop=end_time, step=spacing)
        output = np.zeros_like(times)

        input_position = 0
        for index, time in times:
            while (not math.isclose(time, self.times[input_position])) and (time < self.times[input_position]):
                input_position += 1

            # If this time point has the correct spacing, it is OK
            if math.isclose(time, self.times[input_position]):
                output[index] = self.fluxes[input_position]
                continue

            logging.info("No data available at time point {:.5f}", time)
            output[index] = 1

        # Return lightcurve
        return LightcurveFixedStep(
            time_start=start_time,
            time_step=spacing,
            fluxes=output
        )


class LightcurveFixedStep:
    """
    A class representing a lightcurve which is sampled on a fixed time step.
    """

    def __init__(self, time_start, time_step, fluxes, uncertainties=None, flags=None, metadata=None):
        """
        Create a lightcurve which is sampled on an arbitrary raster of times.

        :param time_start:
            The time at the start of the lightcurve.
        :type time_start:
            float
        :param time_step:
            The interval between the points in the lightcurve.
        :type time_step:
            float
        :param fluxes:
            The light fluxes at each data point.
        :type fluxes:
            np.ndarray
        :param uncertainties:
            The uncertainty in each data point.
        :type uncertainties:
            np.ndarray
        :param flags:
            The flag associated with each data point.
        :type flags:
            np.ndarray
        :param metadata:
            The metadata associated with this lightcurve.
        :type metadata:
            dict
        """

        # Check inputs
        assert isinstance(fluxes, np.ndarray)

        # Unset all flags if none were specified
        if flags is not None:
            assert isinstance(flags, np.ndarray)
        else:
            flags = np.zeros_like(fluxes)

        # Make an empty metadata dictionary if none was specified
        if metadata is not None:
            assert isinstance(metadata, dict)
        else:
            metadata = {}

        # Make uncertainty zero if not specified
        if uncertainties is not None:
            assert isinstance(uncertainties, np.ndarray)
        else:
            uncertainties = np.zeros_like(fluxes)

        # Store the data
        self.time_start = float(time_start)
        self.time_step = float(time_step)
        self.fluxes = fluxes
        self.uncertainties = uncertainties
        self.flags = flags
        self.flags_set = True
        self.metadata = metadata
