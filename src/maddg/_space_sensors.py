# Copyright (c) 2025 Massachusetts Institute of Technology
# SPDX-License-Identifier: MIT

import pickle
from typing import List, Dict
from madlib import SpaceOpticalSensor, Satellite
import tempfile
import json
import os

from hydra_zen import launch, make_config

deg2rad = 0.017453292519943295  # pi/180


def make_and_pickle_sensor(
    sensor_name: str,
    epoch_mjd: float,
    keplerian_elements: Dict,
    start_mjd: float,
    end_mjd: float,
    dra: float,
    ddec: float,
    obs_per_collect: int,
    collect_gap_mean: float,
    collect_gap_std: float,
    obs_limits: dict,
):
    sat = Satellite.from_keplerian(
        epoch=epoch_mjd,
        inclination_rad=keplerian_elements["inc_deg"] * deg2rad,
        raan_rad=keplerian_elements["raan_deg"] * deg2rad,
        argp_rad=keplerian_elements["arp_deg"] * deg2rad,
        ecc=keplerian_elements["ecc"],
        semi_major_axis_km=keplerian_elements["sma_m"] / 1000.0,
        mean_anomaly_rad=keplerian_elements["man_deg"] * deg2rad,
    )

    sensor = SpaceOpticalSensor(
        sensor_satellite=sat,
        dra=dra,
        ddec=ddec,
        collect_gap_mean=collect_gap_mean,
        obs_limits=obs_limits,
        collect_gap_std=collect_gap_std,
        obs_per_collect=obs_per_collect,
        id=sensor_name,
    )

    obs_times = sensor.generate_obs_timing(start=start_mjd, end=end_mjd)

    sensor.sensor_propagate(times=obs_times)

    with open(f"{sensor_name}_sensor.pkl", "wb") as f:
        pickle.dump(sensor, f)

    with open(f"{sensor_name}_times.pkl", "wb") as f:
        pickle.dump(obs_times, f)


def driver(
    elements_dir,
    job_id: int,
    epoch_mjd: float,
    start_mjd: float,
    end_mjd: float,
    dra: float,
    ddec: float,
    obs_per_collect: int,
    collect_gap_mean: float,
    collect_gap_std: float,
    obs_limits: dict,
):
    elements_path = os.path.join(elements_dir, f"sensor_{job_id}.json")

    with open(elements_path, "r") as f:
        keplerian_elements = json.load(f)

    sensor_name = f"sensor_{job_id}"

    make_and_pickle_sensor(
        sensor_name=sensor_name,
        epoch_mjd=epoch_mjd,
        keplerian_elements=keplerian_elements,
        start_mjd=start_mjd,
        end_mjd=end_mjd,
        dra=dra,
        ddec=ddec,
        obs_per_collect=obs_per_collect,
        collect_gap_mean=collect_gap_mean,
        collect_gap_std=collect_gap_std,
        obs_limits=obs_limits,
    )


def task_fn(cfg):
    driver(**cfg)


def launch_sensor_propagation(
    epoch_mjd: float,
    elements_list: List[Dict],
    start_mjd: float,
    end_mjd: float,
    dra: float,
    ddec: float,
    obs_per_collect: int,
    collect_gap_mean: float,
    collect_gap_std: float,
    obs_limits: dict,
):
    with tempfile.TemporaryDirectory(dir=".") as tmpdirname:
        print(f"Temporary directory: {tmpdirname}")
        for n, elements in enumerate(elements_list):
            temp_json_path = os.path.join(tmpdirname, f"sensor_{n}.json")
            with open(temp_json_path, "w") as f:
                json.dump(elements, f)

        Cfg = make_config(
            elements_dir=tmpdirname,
            job_id=0,
            epoch_mjd=epoch_mjd,
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            dra=dra,
            ddec=ddec,
            obs_per_collect=obs_per_collect,
            collect_gap_mean=collect_gap_mean,
            collect_gap_std=collect_gap_std,
            obs_limits=obs_limits,
        )

        N = len(elements_list)

        print("Launching jobs.")

        (jobs,) = launch(
            Cfg,
            task_function=task_fn,
            job_name="sensor_job",
            multirun=True,
            to_dictconfig=True,
            overrides=[
                f"job_id=range(0,{N})",
                "hydra/launcher=submitit_slurm",
                "hydra.launcher.partition=normal",
                "hydra.launcher.constraint=xeon-e5",
                "hydra.launcher.nodes=1",
                "hydra.launcher.cpus_per_task=2",
            ],
        )


if __name__ == "__main__":
    import pandas as pd
    import time

    t0 = time.time()
    epoch_mjd = 60197
    start_mjd = epoch_mjd
    end_mjd = start_mjd + 3

    starlink_file = "/home/gridsan/MI25223/MaDDG/ExternalData/starlink_elements.csv"

    dra = 10.0
    ddec = 10.0
    obs_per_collect = 1
    collect_gap_mean = 10.0
    collect_gap_std = 1.0

    obs_limits = {
        "sun_separation": [40.0, 180.0],
    }

    keplerian_data = pd.read_csv(starlink_file)
    elements_list = keplerian_data.to_dict("records")

    launch_sensor_propagation(
        epoch_mjd=epoch_mjd,
        elements_list=elements_list,
        start_mjd=start_mjd,
        end_mjd=end_mjd,
        dra=dra,
        ddec=ddec,
        obs_per_collect=obs_per_collect,
        collect_gap_mean=collect_gap_mean,
        collect_gap_std=collect_gap_std,
        obs_limits=obs_limits,
    )
    t1 = time.time()
    print(f"Time Elapsed: {(t1-t0)/60:.1f} minutes")
