""" 
Periodically reconnect simulators to a brain
example usage with a reconnection executed every minute: 
python reconnect.py --simulator-name HouseEnergy --brain-name 20201116_he --brain-version 1 --concept-name SmartHouse --interval 1
"""

__author__ = "Brice Chung"
__version__ = "0.0.2"

import subprocess, argparse, datetime, time
import json


def parse_sim_status():
    """ Function to parse bonsai simulator unmanaged list
    """
    unset_sims = []

    with open("sim_list.json") as f:
        sim_list = json.load(f)

    for instance in sim_list["value"]:
        if instance["action"] == "Unset":
            unset_sims.append(instance["sessionId"])
        else:
            pass
    return unset_sims


def connect_sim(
    simulator_name: str,
    brain_name: str,
    brain_version: str,
    concept_name: str,
    action: str = "Train",
):
    """ Reconnect simulator to brain
    """
    timeout_value = 15 * 60  # in s
    retry_wait = 1 * 60  # in s
    max_retries = 10  # number of retries if timeout or errors
    retry_count = 0
    list_cmd = "bonsai simulator unmanaged list --simulator-name {} -o json".format(
        simulator_name
    )

    while retry_count < max_retries:
        try:
            with open("sim_list.json", "w") as outfile:
                subprocess.run(
                    list_cmd.split(), timeout=timeout_value, check=True, stdout=outfile
                )
            time.sleep(1)
            try:
                unset_sims = parse_sim_status()
            except:
                print(
                    "ERROR from reconnect.py: No sims are available with your criteria from bonsai simulator list. Retrying {}... Perhaps spin up new sims or increase command timeout in reconnect.py if issue persists.".format(
                        retry_count
                    )
                )
                time.sleep(retry_wait)
                continue
            for sessid in unset_sims:
                connect_cmd = "bonsai simulator unmanaged connect \
                    --session-id {} \
                    --brain-name {} \
                    --brain-version {} \
                    --concept-name {} \
                    --action {}".format(
                    sessid, brain_name, brain_version, concept_name, action
                )
                subprocess.run(connect_cmd.split(), timeout=timeout_value, check=True)
        except subprocess.TimeoutExpired:
            print(
                "{}: command timeout, will retry in {} min, retry attempt {} out of {}".format(
                    datetime.datetime.now(), retry_wait / 60, retry_count, max_retries
                )
            )
            time.sleep(retry_wait)
        except subprocess.SubprocessError:
            print(
                "{}: command error, will retry in {} min, retry attempt {} out of {}".format(
                    datetime.datetime.now(), retry_wait / 60, retry_count, max_retries
                )
            )
            time.sleep(retry_wait)
        else:
            break
        finally:
            retry_count += 1


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="reconnect sim")
    parser.add_argument(
        "--simulator-name",
        type=str,
        default=None,
        help="simulator name of sims to connect to brain",
    )
    parser.add_argument(
        "-b",
        "--brain-name",
        type=str,
        default=None,
        help="brain name for sim to connect to",
    )

    parser.add_argument(
        "--brain-version",
        type=str,
        default=None,
        help="brain version for sim to connect to",
    )

    parser.add_argument(
        "-c",
        "--concept-name",
        type=str,
        default=None,
        help="concept name for sim to connect to",
    )

    parser.add_argument(
        "-a",
        "--action",
        type=str,
        default="Train",
        help="action value can be Train or Assess",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="interval to periodically run reconnect in minutes",
    )

    args = parser.parse_args()
    if (
        args.simulator_name is None
        or args.brain_name is None
        or args.brain_version is None
        or args.concept_name is None
    ):
        parser.error(
            "reconnect requires --simulator-name, --brain-name, --brain-version and --concept-name"
        )
    elif args.interval is None:
        parser.error("needs --interval in minutes")

    while True:
        connect_sim(
            simulator_name=args.simulator_name,
            brain_name=args.brain_name,
            brain_version=args.brain_version,
            concept_name=args.concept_name,
            action=args.action,
        )
        print(
            "{}: reconnect will execute in {} min".format(
                datetime.datetime.now(), args.interval
            )
        )
        time.sleep(args.interval * 60)
