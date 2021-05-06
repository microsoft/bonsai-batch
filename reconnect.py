""" 
Periodically reconnect simulators to a brain
example usage with a reconnection executed every minute: 
python reconnect.py --simulator-name HouseEnergy --brain-name 20201116_he --brain-version 1 --concept-name SmartHouse --interval 15
"""

__author__ = "Brice Chung"
__version__ = "0.0.5"

import subprocess, argparse, datetime, time
import os
import json
import logging
import logging.handlers
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)

logger = logging.getLogger("batch_containers")

def parse_sim_status(to_reverse=False):
    """ Function to parse bonsai simulator unmanaged list
    """
    unset_sims = []
    
    with open('sim_list.json') as f:
        sim_list = json.load(f)
    
    for instance in sim_list['value']:
        if instance['action'] == 'Unset':
            unset_sims.append(instance['sessionId'])
        else:
            pass
    
    # If lingering sims are clustered in beginning of query list, go to the back and start connecting sims
    if to_reverse:
        return reversed(unset_sims)
    else:
        return unset_sims

def connect_sim(simulator_name: str, brain_name: str, brain_version: str, concept_name: str, action: str = 'Train', to_reverse=False):
    """ Reconnect simulator to brain
    """
    timeout_value = 5*60 # in s
    retry_wait = 0.1 # in s
    max_retries = 15 # number of retries if timeout or errors
    retry_count = 0
    list_cmd = 'bonsai simulator unmanaged list --simulator-name {} -o json'.format(simulator_name)
    blocked_list = []
    
    while retry_count < max_retries:
        try:
            with open('sim_list.json', 'w') as outfile:
                subprocess.run(list_cmd.split(), timeout=timeout_value, check=True, stdout=outfile)
            time.sleep(1)
            try:
                unset_sims = parse_sim_status(to_reverse)
            except:
                logger.warning(
                    f'ERROR from reconnect.py: No sims are available with your criteria from bonsai simulator list. Retrying {}... Perhaps spin up new sims, check network issues, or increase command timeout in reconnect.py if issue persists.'.format(retry_count)
                )
                continue
            for sessid in unset_sims:
                if sessid not in blocked_list:
                    connect_cmd = 'bonsai simulator unmanaged connect \
                        --session-id {} \
                        --brain-name {} \
                        --brain-version {} \
                        --concept-name {} \
                        --action {}'.format(sessid, brain_name, brain_version, concept_name, action)
                    subprocess.run(connect_cmd.split(), timeout=timeout_value, check=True)
                else:
                    pass
        except subprocess.TimeoutExpired:
            print('{}: command timeout, will retry in {} min, retry attempt {} out of {}'.format(datetime.datetime.now(),retry_wait/60, retry_count, max_retries))
            time.sleep(retry_wait)
        except subprocess.SubprocessError:
            try: 
                print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                print("We may be going through a deployment and session id: {} has become invalidated, ignoring...".format(sessid))
                blocked_list.append(sessid)
                print('blocked list: {}'.format(blocked_list))
                print('{}: command error, will retry in {} min, retry attempt {} out of {}'.format(datetime.datetime.now(),retry_wait/60, retry_count, max_retries))
                print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                time.sleep(retry_wait)
            except:
                print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('ERROR from reconnect.py: No sims are available with your criteria from bonsai simulator list. Retrying {}... Perhaps spin up new sims, check network issues, or increase command timeout in reconnect.py if issue persists.'.format(retry_count))
                print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
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
            default='Train',
            help="action value can be Train or Assess",
        )
    
    parser.add_argument(
            "--interval",
            type=int,
            default=15,
            help="interval to periodically run reconnect in minutes",
        )

    args = parser.parse_args()
    if args.simulator_name is None or args.brain_name is None or args.brain_version is None or args.concept_name is None:
        parser.error("reconnect requires --simulator-name, --brain-name, --brain-version and --concept-name")
    elif args.interval is None:
        parser.error("needs --interval in minutes")

    to_reverse = False

    while True:
        # Toggle order of bonsai simulator unmanaged list if during deployment after retry attempts exceeded
        to_reverse ^= False

        # Run connect sim for X retry attempts, filtering for session ids and setting purpose
        connect_sim(
            simulator_name=args.simulator_name,
            brain_name=args.brain_name,
            brain_version=args.brain_version,
            concept_name=args.concept_name,
            action=args.action,
            to_reverse=to_reverse,
        )
        print('{}: reconnect will execute in {} min'.format(datetime.datetime.now(),args.interval))
        time.sleep(args.interval*60)
