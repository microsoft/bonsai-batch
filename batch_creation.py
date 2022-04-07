#! /usr/bin/env python
"""Create Azure Resources to scale simulation experiments for the Bonsai platform.
"""

import configparser
import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
import re
from typing import Dict, Union

import fire
from azure.cli.core import get_default_cli
from error_handles import *

from rich import print
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)],
)

for name in logging.Logger.manager.loggerDict.keys():
    if "azure" in name:
        logging.getLogger(name).setLevel(logging.WARNING)
        logging.propagate = True

logger = logging.getLogger("batch_creation")

default_config = os.path.join("configs", "config.ini")
windows_config = os.path.join("configs", "winconfig.ini")
user_config = os.path.join("configs", "userconfig.ini")


def azure_cli_run(cmd: str) -> Union[Dict, bool]:
    """Run Azure CLI command

    Returns
    -------
    cli.result
        stout of Azure CLI command

    Raises
    ------
    cli.result.error
        If sterror occurs due to azure CLI command
    """

    args = cmd.split()
    cli = get_default_cli()
    cli.invoke(args)
    if cli.result.result:
        logger.info("az {0}...".format(cmd))
        return cli.result.result
    elif cli.result.error:
        if any(msg in cli.result.error.message for msg in all_messages):
            logger.info(
                f"[bold red]Creation failed due to known reason: {cli.result.error.message}[/bold red]"
            )
        else:
            raise cli.result.error
    return True


class AzCreateBatch:
    def __init__(self, rg: str = "azcsbatchrg", loc: str = "westus", *args, **kwargs):
        """Create Azure Batch Service, and correpsonding Azure Container Registry and storage account.

        Parameters
        ----------
        rg : str
            Azure resource group
        loc : str, optional
            Region to use for resources' location, by default "westus"
        """

        self.rg = rg
        self.loc = loc

        return super().__init__(*args, **kwargs)

    def create_rg(self, rg_loc: Union[str, None]):
        """Create resource group based on with self.rg.
        All subsequent resourecs will be under this resource group.
        """

        if not rg_loc:
            rg_loc = self.loc
        azure_cli_run("group create -l {0} -n {1}".format(rg_loc, self.rg))

    def create_acr(self, acr: str):
        """Create an Azure Container Registry. Skips if already exists under resource group.

        Parameters
        ----------
        acr : str
            Name of Azure Container Registry to create.
        """

        azure_cli_run(
            "acr create -n {0} -g {1} -l {2} --sku Standard".format(
                acr, self.rg, self.loc
            )
        )
        azure_cli_run("acr update -n {0} --admin-enabled true".format(acr))

    def create_batch(self, batch: str):
        """Create an Azure Batch account. Skips if already exists under resource group.

        Parameters
        ----------
        batch : str
            Name of Azure Batch account.
        """

        azure_cli_run(
            "batch account create -l {0} -n {1} -g {2}".format(self.loc, batch, self.rg)
        )  # batch account creation
        # az batch account login -g $azgroup -n $azbatch --shared-key-auth #batch account login
        azure_cli_run(
            "batch account login -n {0} --shared-key-auth -g {1}".format(batch, self.rg)
        )

    def create_store(self, storage_account: str):
        """Create an Azure Blob Storage account to attach to Batch service. Skip if already exists under resource group.

        Parameters
        ----------
        storage_account : str
            Name of the Azure blob storage account.
        """
        azure_cli_run(
            "storage account create -g {0} -l {1} -n {2} --sku Standard_LRS".format(
                self.rg, self.loc, storage_account
            )
        )

    def connect_store_batch(self, batch_account: str, storage_account: str):
        """Connect Azure Blob Storage account to Batch service.

        Parameters
        ----------
        batch_account : str
        storage_account : str
        """

        azure_cli_run(
            "batch account set -g {0} -n {1} --storage-account {2}".format(
                self.rg, batch_account, storage_account
            )
        )

    def create_app_insight(self, insight_acct: str) -> Dict:

        azure_cli_run("config set extension.use_dynamic_install=yes_without_prompt")
        app_insight_info = azure_cli_run(
            f"monitor app-insights component create --app {insight_acct} --loc {self.loc} --resource-group {self.rg}"
        )

        return app_insight_info

    def create_vnet(self, vnet_name: str) -> Dict:

        # https://docs.microsoft.com/en-us/cli/azure/network/vnet?view=azure-cli-latest#az-network-vnet-create

        vnet_info = azure_cli_run(
            f"--network vnet create --name {vnet_name} --resource-group {self.rg}"
        )

        return vnet_info


class AzExtract:
    def __init__(self, rg: str = "azcsbatchrg", *args, **kwargs):
        """Extract Azure resource credentials from resource group.

        Parameters
        ----------
        rg : str, optional
            Name of resource group, by default "azcsbatchrg"

        """

        self.rg = rg

        return super().__init__(*args, **kwargs)

    def get_batch_key(self, batch_account: str):

        batch_keys = azure_cli_run(
            "batch account keys list -n {0} -g {1}".format(batch_account, self.rg)
        )
        batch_key = batch_keys["primary"]

        return batch_key

    def get_storage_key(self, storage: str):

        storage_keys = azure_cli_run("storage account keys list -n {0}".format(storage))
        store_key = storage_keys[0]["value"]

        return store_key

    def get_acr_pw(self, acr: str):

        acr_passwords = azure_cli_run("acr credential show -n {0}".format(acr))
        acr_password1 = acr_passwords["passwords"][0]["value"]

        return acr_password1


class AcrBuild:
    def __init__(
        self,
        image_name: str,
        image_version: str,
        registry: str,
        platform: str = None,
        docker_path: str = ".",
        timeout: int = 7200,
        *args,
        **kwargs,
    ):
        """Build Docker image on Azure Container Registry.

        Parameters
        ----------
        image_name : str
            Name of image
        image_version : str
            Version of image
        registry : str
            Name of ACR Repository
        platform : str
            Platform for Image (Windows, Ubuntu)
        """

        self.image_name = image_name
        self.image_version = image_version
        self.registry = registry
        if platform:
            self.platform = platform
        else:
            docker_file = open(os.path.join(docker_path, "Dockerfile"))
            docker_lines = docker_file.readlines()
            if "windows" in docker_lines[0]:
                self.platform = "windows"
            else:
                self.platform = "linux"
        self.docker_path = docker_path
        self.timeout = timeout

        return super().__init__(*args, **kwargs)

    def build_image_acr(
        self,
        extra_build_args: Union[str, None],
        filename: str = "Dockerfile",
        timeout: int = 7200,
    ):

        if timeout:
            self.timeout = timeout
        logger.info(
            f"Building a [bold blue]{self.platform}[/bold blue] image [bold]{self.image_name}:{self.image_version}[/bold] in [bold green]{self.registry}.azurecr.io[/bold green]"
        )

        if extra_build_args:
            buildargs = " --build-arg {0}".format(extra_build_args)
        else:
            buildargs = ""

        build_cmd = "acr build --image {0}:{1} --registry {2} --file {3}/{4} {3} --platform {5} {6} --timeout {7}".format(
            self.image_name,
            self.image_version,
            self.registry,
            self.docker_path,
            filename,
            self.platform,
            buildargs,
            self.timeout,
        )
        logger.info(build_cmd)

        azure_cli_run(build_cmd)


def delete_resources(rg_name: str):
    """Delete resource group

    Parameters
    ----------
    rg_name : str
        Name of the resource group to delete
    """

    logger.info("Deleting resource group {0}".format(rg_name))
    azure_cli_run("group delete -n {0} -y --no-wait".format(rg_name))


def write_azure_config(
    rg: str,
    acr: str,
    store: Union[str, None],
    batch: str,
    loc: str,
    rg_loc: str,
    config_file: str = default_config,
    new_config_file: str = user_config,
):

    az_extractor = AzExtract(rg)
    batch_key = az_extractor.get_batch_key(batch_account=batch)
    if store:
        store_key = az_extractor.get_storage_key(storage=store)
    else:
        store = "no-storage"
        store_key = "no-storage-key"
    acr_pw = az_extractor.get_acr_pw(acr=acr)

    config = configparser.ConfigParser()
    # bonsai = configparser.ConfigParser()
    # bonsai.read(str(pathlib.Path.home() / ".bonsai"))

    if not pathlib.Path(config_file).exists():
        raise ValueError("No config file found at {0}".format(config_file))
    else:
        logger.info("Using config from {}".format(config_file))
        config.read(config_file)

        config["GROUP"]["NAME"] = rg
        config["GROUP"]["LOCATION"] = rg_loc

        config["BATCH"]["LOCATION"] = loc
        config["BATCH"]["ACCOUNT_KEY"] = batch_key
        config["BATCH"]["ACCOUNT_NAME"] = batch
        config["BATCH"]["ACCOUNT_URL"] = (
            "https://" + batch + "." + loc + ".batch.azure.com"
        )

        config["STORAGE"]["LOCATION"] = loc
        config["STORAGE"]["ACCOUNT_NAME"] = store
        config["STORAGE"]["ACCOUNT_KEY"] = store_key

        config["ACR"]["LOCATION"] = loc
        config["ACR"]["SERVER"] = acr + ".azurecr.io"
        config["ACR"]["USERNAME"] = acr
        config["ACR"]["PASSWORD"] = acr_pw
        # config["BONSAI"]["USERNAME"] = bonsai["DEFAULT"]["username"]
        # config["BONSAI"]["KEY"] = bonsai["DEFAULT"]["accesskey"]

        with open(new_config_file, "w") as configfile:
            config.write(configfile)


def str_check(input_str: str) -> bool:

    reject = False

    if not input_str.isalnum():
        reject = True
    if any(x.isupper() for x in input_str):
        reject = True
    if len(input_str) >= 25 or len(input_str) < 3:
        reject = True

    return reject


def create_resources(
    rg: str = None,
    acr: str = None,
    store: str = None,
    batch: str = None,
    app_insights: str = None,
    loc: str = "westus",
    rg_loc: Union[str, None] = None,
    conf_file: str = default_config,
    new_conf_file: str = user_config,
    create_fileshare: bool = True,
    create_app_insights: bool = False,
    always_ask: bool = False,
    auto_convert: bool = True,
):
    """Main function to create azure resources and write out credentials to config file

    Parameters
    ----------
    rg : str, required
        Resource group name to use or create.
    acr : str, optional
        Azure container registry, by default $rg + "acr"
    store : str, optional
        Azure blob storage account, by default $rg + "store"
    batch : str, optional
        Azure batch account service, by default $rg + "batch"
    loc : str, optional
        Location to create resources, by default "westus".
    conf_file: str, optional
        Where to read config for default params, by default 'config.ini'
    new_conf_file: str, optional
        Where to write config file, by default 'config.ini'
    create_fileshare: bool, optional
        Whether to create an attached fileshare with storage account, default True
    """

    if not rg:
        rg = input(
            "specify resource group (at least 3, no more than 25, and only lowercase alphanumeric characters): "
        )
        if str_check(rg) and not auto_convert:
            raise ValueError(
                "Resources may contain only lowercase alphanumeric characters"
            )
        elif str_check(rg) and auto_convert:
            pre_conversion_rg = rg
            rg = re.sub("[\W_]+", "", pre_conversion_rg.lower())
            logger.warn(
                f"Provided resource group {pre_conversion_rg} contains special characters; auto-converting to lowercase alphanumeric containers {rg}"
            )

    if not acr and not always_ask:
        acr = rg + "acr"
    elif always_ask:
        acr = input("What is your acr name?")
    if not store:
        store = rg + "store"
    if not batch:
        batch = rg + "batch"
    if not app_insights:
        app_insights = rg + "insights"

    az_create = AzCreateBatch(rg, loc=loc)
    az_create.create_rg(rg_loc=rg_loc)
    az_create.create_acr(acr)
    az_create.create_batch(batch)
    az_create.create_store(store)
    az_create.connect_store_batch(batch_account=batch, storage_account=store)

    # if rg_loc is not provided make it the same as loc since we need to write it
    if not rg_loc:
        rg_loc = loc

    write_azure_config(rg, acr, store, batch, loc, rg_loc, conf_file, new_conf_file)

    if create_app_insights:
        app_insights_info = az_create.create_app_insight(app_insights)
        config = configparser.ConfigParser()
        config.read(new_conf_file)
        config["APP_INSIGHTS"]["INSTRUMENTATION_KEY"] = app_insights_info[
            "instrumentationKey"
        ]
        config["APP_INSIGHTS"]["APP_ID"] = app_insights_info["appId"]
        if config["ACR"]["PLATFORM"] == "linux":
            config["APP_INSIGHTS"][
                "BATCH_INSIGHTS_DOWNLOAD_URL"
            ] = "https://github.com/Azure/batch-insights/releases/download/v1.3.0/batch-insights"
        elif config["ACR"]["PLATFORM"] == "windows":
            config["APP_INSIGHTS"][
                "BATCH_INSIGHTS_DOWNLOAD_URL"
            ] = "https://github.com/Azure/batch-insights/releases/download/v1.3.0/batch-insights.exe"
        else:
            raise ValueError(f"Unknown platform selected {config['ACR']['PLATFORM']}")
        with open(new_conf_file, "w") as configfile:
            config.write(configfile)

    if create_fileshare:
        config = configparser.ConfigParser()
        config.read(new_conf_file)
        config["STORAGE"]["FILESHARE"] = "azfileshare"
        logger.info(
            "Creating fileshare {0} for storage account {1}".format(
                config["STORAGE"]["FILESHARE"], config["STORAGE"]["ACCOUNT_NAME"]
            )
        )

        azure_cli_run(
            "storage share create --account-name {0} --account-key {1} --name {2} --quota 1024".format(
                config["STORAGE"]["ACCOUNT_NAME"],
                config["STORAGE"]["ACCOUNT_KEY"],
                config["STORAGE"]["FILESHARE"],
            )
        )
        config["STORAGE"]["URL"] = "https://{0}.file.core.windows.net/{1}".format(
            config["STORAGE"]["ACCOUNT_NAME"], config["STORAGE"]["FILESHARE"]
        )
        with open(new_conf_file, "w") as configfile:
            config.write(configfile)


def build_image(
    docker_folder: str = None,
    dockerfile_path: str = "Dockerfile",
    image_name: str = None,
    image_version: str = "latest",
    platform: str = None,
    extra_build_args: str = None,
    conf_file: str = user_config,
    timeout: int = 7200,
):
    """Build ACR image from a source directory containing a dockerfile and src files.

    Parameters
    ----------
    docker_folder: str
    dockerfile_path : str
    image_name : str, optional
    image_version : str, optional
    platform : str, optional
    extra_build_args : str, optional
    conf_file : str, optional
        [description], by default "newconf.ini"
    """

    if not os.path.exists(conf_file):
        logger.info(
            f"No default configuration found at {conf_file}, creating config..."
        )
        rg = input("What is your provisioned workspace resource group? ")
        acr = input("What is your provisioned workspace ACR path? ")
        acr = acr.replace(".azurecr.io", "")
        store = input(
            "What storage account should be mounted to your Batch pool? (default is None, for no storage) "
        )
        if store.lower() == "none":
            store = None
        batch = input(
            "What is your provisioned Batch account name? If you don't have one please write None. "
        )
        loc = (
            input("What is the region of your workspace? (default = westus2) ")
            or "westus2"
        )

        if batch.lower() == "none":
            az_create = AzCreateBatch(rg=rg, loc=loc)
            batch = input(
                "What is the name of the batch account you'd like to create? "
            )
            az_create.create_batch(batch)

        write_azure_config(
            rg=rg,
            acr=acr,
            batch=batch,
            store=store,
            loc=loc,
            config_file=default_config,
            new_config_file=conf_file,
        )

    config = configparser.ConfigParser()
    config.read(conf_file)
    acr = config["ACR"]["USERNAME"]

    if not docker_folder:
        docker_folder = input("Directory of Dockerfile and source files: ")

    if not image_name:
        image_name = input("Please provide a name for your image: ")
        # image_name = re.sub(r"[^\w\s]", "", docker_folder)
    if not image_version:
        image_version = "latest"

    acr_build_image = AcrBuild(
        image_name=image_name,
        image_version=image_version,
        registry=acr,
        platform=platform,
        docker_path=docker_folder,
    )
    acr_build_image.build_image_acr(
        filename=dockerfile_path, extra_build_args=extra_build_args, timeout=timeout
    )
    platform = acr_build_image.platform

    config["ACR"]["IMAGE_NAME"] = image_name
    config["ACR"]["IMAGE_VERSION"] = image_version
    config["ACR"]["PLATFORM"] = platform
    with open(conf_file, "w") as config_file:
        config.write(config_file)


if __name__ == "__main__":

    fire.Fire()
    # rg = "aztest"
    # acr = "aztestacr"
    # store = "azteststore"
    # loc = "westus"
    # batch = "aztestbatch"
    # create_resources(rg=rg, acr=acr, loc=loc, store=store, batch=batch)

    # rg = "azbatchinsightsrg"
    # loc = "westus"
    # acr = "azbatchinsightsrgacr"
    # store = "azbatchinsightsrgstore"
    # batch = "azbatchinsightsrgbatch"

    # create_resources(rg=rg, acr=acr, store=store, batch=batch, loc=loc)
