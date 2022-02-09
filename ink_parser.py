"""Utilities for parsing and adjusting inkling files

Supported operations:

1. Adjust goal objectives
2. Adjust training parameters (including new ones)
3. Adjust algorithm parameters (including new ones)

NOT yet implemented:
1. experimental tags
2. support for adjust algorithm network
3. changing algorithms for specific concepts
4. ~~changing training parameters for specific lessons~~
5. Remove/add goals
6. Adjust observablestate based on user input
7. Change the output of concept
8. Modify lesson scenarios
    - read config param and then adjust ranges for specific config values
    - adjust_scenario_params(ink_file, {"vehicles_count": [10,50]})
    - adjust_scenario_params(ink_file: {"vehicles_count": [10,20]})

"""

from typing import Any, Dict, List


def read_ink(ink_path: str = "machine_teacher.ink"):
    with open(ink_path, "r") as input_file:
        ink_file = input_file.read()
    ink_lines = ink_file.split("\n")

    return ink_lines


def write_ink(ink_to_write, ink_path: str = "new_teacher.ink"):
    with open(ink_path, "w") as input_file:
        n = input_file.write(ink_to_write)
        input_file.close()


def split_on_dhash(inpt):

    output_list = []
    chunk = []
    for l in inpt:
        if l.strip().startswith("##"):
            if len(chunk) > 0:
                output_list.append(chunk)
                chunk = []
            chunk.append(l)
        else:
            chunk.append(l)
    output_list.append(chunk)
    return output_list


def add_weight_objective(ink_chunk: List[str], goal_name: str, weight_value: int):

    new_chunk = []

    for l in ink_chunk:
        if goal_name in l:
            if "weight" in l:
                l = l[:-2] + f"{weight_value}:"
            else:
                weight_str = f" weight {weight_value}:"
                l = l[:-1] + weight_str
        new_chunk.append(l)
    return new_chunk


def adjust_weight_objectives(ink_lines: List[str], goal_weights: Dict[str, int]):

    ink_chunks: List[List[str]] = split_on_dhash(ink_lines)

    match_index = -1
    for e, ink_l in enumerate(ink_chunks):
        if any("goal (" in string for string in ink_l):
            match_index = e
            for gk, gv in goal_weights.items():
                ink_c = add_weight_objective(ink_l, gk, gv)

    if match_index != -1:
        ink_chunks[match_index] = ink_c
    else:
        print(f"no goals with names {goal_weights.keys()} found in ink file")

    return [l for sl in ink_chunks for l in sl]


def adjust_training_params(
    ink_lines: List[str], train_params: Dict[str, Any], training_section: str,
):

    ink_chunks: List[List[str]] = split_on_dhash(ink_lines)

    match_index = -1
    new_training_params = [training_section, "training {"]
    white_space = 4

    for e, ink_l in enumerate(ink_chunks):
        if any("training {" in string for string in ink_l) and any(
            training_section in string for string in ink_l
        ):
            match_index = e
            white_space = len(ink_l[0]) - len(ink_l[0].strip()) + 4
            for k, v in train_params.items():
                if k != list(train_params)[-1]:
                    l = " " * white_space + f"{k}: {v},"
                else:
                    l = " " * white_space + f"{k}: {v}"
                new_training_params.append(l)
    close_training_params = " " * (white_space - 4) + "}"
    new_training_params[0] = " " * (white_space - 4) + training_section
    new_training_params[1] = " " * (white_space - 4) + "training {"
    new_training_params.append(close_training_params)

    if match_index != -1:
        ink_chunks[match_index] = new_training_params
    return [l for sl in ink_chunks for l in sl]


def adjust_sim_package():

    pass


def adjust_observed_state():
    pass


def adjust_algorithm_params(
    ink_lines: List[str], algo_params: Dict[str, Any],
):

    ink_chunks: List[List[str]] = split_on_dhash(ink_lines)

    match_index = -1
    new_algorithm_params = ["algorithm {"]
    white_space = 4

    for e, ink_l in enumerate(ink_chunks):
        if any("algorithm {" in string for string in ink_l):
            match_index = e
            white_space = len(ink_l[0]) - len(ink_l[0].strip()) + 4
            for k, v in algo_params.items():
                if k != list(algo_params)[-1]:
                    l = " " * white_space + f"{k}: {v},"
                else:
                    l = " " * white_space + f"{k}: {v}"
                new_algorithm_params.append(l)
    close_algorithm_params = " " * (white_space - 4) + "}"
    new_algorithm_params[0] = " " * (white_space - 4) + "algorithm {"
    new_algorithm_params.append(close_algorithm_params)

    if match_index != -1:
        ink_chunks[match_index] = new_algorithm_params
    return [l for sl in ink_chunks for l in sl]


if __name__ == "__main__":
    ink_path = "/home/alizaidi/bonsai/microsoft-bonsai-api/Python/samples/cartpole/machine_teacher.ink"
    ink_lines = read_ink(ink_path)
    # ink_chunks = split_on_dhash(ink_lines)
    # new_goals = add_weight_objective(ink_chunks[8], "FallOver", 2)
    new_ink_goals = adjust_weight_objectives(ink_lines, {"FallOver": 2})
    new_train_params = {
        "EpisodeIterationLimit": 100,
        "TotalIterationLimit": 10 ** 10,
        "NoProgressIterationLimit": 10 ** 6,
        "LessonAssessmentWindow": 50,
        # "LessonRewardThreshold": 200,
        "LessonSuccessThreshold": 0.95,
    }
    new_ink = adjust_training_params(
        new_ink_goals, new_train_params, "## concept-level training params"
    )

    new_algorithm_params = {
        "MemoryMode": '"state and action"',
        "Algorithm": '"PPO"',
        "BatchSize": 6000,
        "PolicyLearningRate": "5e-5",
    }
    newer_ink = adjust_algorithm_params(new_ink, new_algorithm_params)
    write_ink("\n".join(newer_ink), "new_teacher.ink")
