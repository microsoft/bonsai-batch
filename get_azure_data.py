import json
from urllib.request import urlopen

import pandas as pd
from bs4 import BeautifulSoup

columns_to_show = [
    "name",
    "numberOfCores",
    # "osDiskSizeInMB",
    # "resourceDiskSizeInMB",
    # "maxDataDiskCount",
    "memoryInMB",
    "linuxPrice",
    "windowsPrice",
    "regionId",
    "pricePerMemoryLinux",
    "pricePerMemoryWindows",
    "pricePerCoreLinux",
    "pricePerCoreWindows",
    "bestPriceRegion",
]


def get_table(
    region: str = "eastus", low_pri: bool = True, host_os: str = "linux"
) -> pd.DataFrame:
    """Retrieves a table of VM prices from https://azureprice.net/ for provided
    region, OS and priority
    
    Parameters
    ----------
    region : str, optional
        [description], by default "eastus"
    low_pri : bool, optional
        [description], by default True
    host_os : str, optional
        [description], by default "linux"
    
    Returns
    -------
    pd.DataFrame
    """

    azure_price_url = "https://azureprice.net/" + "?region=" + region

    if low_pri:
        azure_price_url += "&priority=true"
    else:
        azure_price_url += "&priority=false"

    html = urlopen(azure_price_url)
    soup = BeautifulSoup(html, "html.parser")
    body_script = soup.find("body").script
    body_script_contents = body_script.contents

    table_str = str(body_script_contents)
    b = table_str[17:-11]

    if host_os == "linux":
        drop_os = "windows"
    else:
        drop_os = "linux"
    regex_os = "(?i)" + drop_os

    table_df = pd.DataFrame(json.loads(b))
    table_df = table_df[columns_to_show]
    table_df = table_df[table_df.columns.drop(list(table_df.filter(regex=regex_os)))]
    return table_df


def calculate_price(
    low_pri_df: pd.DataFrame,
    dedicated_df: pd.DataFrame,
    # num_simulators: int = 100,
    low_pri_num: int = 10,
    dedicated_num: int = 1
    # num_brains: int = 10,
) -> float:
    """Calculates the price per hour for given dedicated an low priority node combination
    
    Calculation is simply the sum of the lowest VM price for dedicated
    and low priority nodes, multiplied by the number of instances
    TODO: 
        * allow user to provide number of instances per machine
        * i.e., divide total_nodes / (num_sims_per_node)

    Parameters
    ----------
    low_pri_df : pd.DataFrame
        [description]
    dedicated_df : pd.DataFrame
        [description]
    low_pri_num : int, optional
        [description], by default 10
    dedicated_num : int, optional
        [description], by default 1#num_brains:int=10

    Returns
    -------
    float
        Total cost per hour
    """

    low_pri_cost = low_pri_df.price.min() * low_pri_num
    dedicated_cost = dedicated_df.price.min() * dedicated_num

    total_cost = low_pri_cost + dedicated_cost
    return total_cost


def show_hourly_price(
    region: str = "westus",
    machine_sku: str = "Standard_a2_v2",
    low_pri_nodes: int = 9,
    dedicated_nodes: int = 1,
    host_os: str = "linux",
):

    low_table = get_table(region=region, low_pri=True, host_os=host_os)
    low_table = low_table[low_table["name"].str.lower() == machine_sku.lower()]
    ded_table = get_table(region=region, low_pri=False, host_os=host_os)
    ded_table = ded_table[ded_table["name"].str.lower() == machine_sku.lower()]

    hourly_price = (float(low_table.iloc[:, 3]) * low_pri_nodes) + (
        float(ded_table.iloc[:, 3]) * dedicated_nodes
    )

    return round(hourly_price, 2)


if __name__ == "__main__":

    print(get_table("westus").head())
