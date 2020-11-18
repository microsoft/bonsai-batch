import json
import subprocess
import pandas as pd


def get_running_unmanaged_sims(sim_name: str):

    list_sims = f"bonsai simulator unmanaged list --simulator-name {sim_name} -o json"
    print(list_sims)
    all_sims = subprocess.check_output(list_sims.split(" "))
    sims_json = json.loads(all_sims)

    return sims_json


def connect_sims(
    sim_name: str, brain_name: str, brain_version: str, concept: str,
):

    connect_cmd = f"bonsai simulator unmanaged connect -b {brain_name} --brain-version {brain_version} -a Train -c {concept} --simulator-name {sim_name} --debug"
    print(connect_cmd)
    run_it = subprocess.check_output(connect_cmd.split(" "))

    return run_it


def start_logging(sims_df: pd.DataFrame, brain_name: str, brain_version: str):

    debug_lst = []
    for sim_value in sims_df.value.tolist():
        session_id = sim_value["sessionId"]
        connect_cmd = f"bonsai brain version start-logging -n {brain_name} --version {brain_version} -d {session_id} --debug"
        debug_lst.append(subprocess.check_output(connect_cmd.split(" ")))

    return debug_lst


if __name__ == "__main__":

    connect_sims()
    all_sims = get_running_unmanaged_sims()
    sim_df = pd.DataFrame(all_sims)
    connect_logs = start_logging(sim_df)
    print(connect_logs)
