# Batch Orchestration for Bonsai Simulations

## Overview

You've found the `batch-orchestration` framework. Here you'll find a set of tools to assist you in scaling out simulators using Azure Batch.

⚠️ **Disclaimer**: This is not an official Microsoft product. This application is considered an experimental addition to Microsoft Project Bonsai's software toolchain. It's primary goal is to reduce barriers of entry to use Project Bonsai's core Machine Teaching, and no warranties are provided for its use.

### Prerequisites

1. An Azure account.
2. Bonsai workspace. You can find instructions on provisioning a [bonsai workspace here](https://docs.microsoft.com/en-us/bonsai/guides/account-setup).
3. Anaconda or [miniconda](https://docs.conda.io/en/latest/miniconda.html).
4. Create a virtual environment with libraries dependencies (described in environment.yml file)

```shell
conda env create -f environment.yml
conda activate bonsai-preview
```

## Quick Start

- Create your resources: `python batch_creation.py create_resources`
- Build your image: `python batch_creation.py build_image`
- Run your tasks: `python batch_containers.py run_tasks`
- Create your brain and start training: `bonsai brain version start-training --name <brain-name>`
- Attach your simulators: `bonsai simulator unmanaged connect -b <brain-name> -a Train -c <concept_name> --simulator-name <simulator-name>`

## Scaling Simulators Using Azure Batch and Azure Container Registry

There are two executable scripts in this repository:

1. `batch_creation.py` -> creates the necessary resources on Azure to scale your simulations: Azure Batch, Azure Container Registry, and Azure Blob Storage, all within a single resource group.
    - **NOTE**: Resources may contain only lowercase alphanumeric characters, and must be between 3 and 25 characters in length.
2. `batch_containers.py` -> executes a set of simulation jobs as a set of tasks on the Azure Batch account you created in step 1.

Both of these scripts rely on the [`fire`](https://google.github.io/python-fire/) package to execute the scripts. To view how to use these scripts you are recommended to view their associated arguments and documentation:

```bash
python batch_creation.py -h
NAME
    batch_creation.py

SYNOPSIS
    batch_creation.py GROUP | COMMAND

GROUPS
    GROUP is one of the following:

     configparser
       Configuration file parser.

     pathlib

     re
       Support for regular expressions (RE).

     Dict
       The central part of internal API.

     Union
       Internal indicator of special typing constructs. See _doc instance attribute for specific docs.

     fire
       The Python Fire module.

COMMANDS
    COMMAND is one of the following:

     get_default_cli

     azure_cli_run
       Run Azure CLI command

     AzCreateBatch

     AzExtract

     AcrBuild

     delete_resources
       Delete resource group

     write_azure_config

     create_resources
       Main function to create azure resources and write out credentials to config file

     build_image
       Build ACR image from a source directory containing a dockerfile and src files.


python batch_containers.py -h
NAME
    batch_containers.py

SYNOPSIS
    batch_containers.py GROUP | COMMAND

GROUPS
    GROUP is one of the following:

     configparser
       Configuration file parser.

     datetime
       Fast implementation of the datetime type.

     pathlib

     sys
       This module provides access to some objects used or maintained by the interpreter and to functions that interact strongly with the interpreter.

     time
       This module provides various functions to manipulate time values.

     List
       The central part of internal API.

     batch_auth

     batch

     batchmodels

     blobxfer

     fire
       The Python Fire module.

     xfer_utils
       Run and scale simulation experiments on Azure Batch.

COMMANDS
    COMMAND is one of the following:

     AzureBatchContainers

     run_tasks
       Run simulators in Azure Batch.

     stop_job

     upload_files
       Upload files into attached batch storage account.

```

While there are a lot of different functions exposed, the most common usage only relies on two of them from `batch_creation`, and one from `batch_containers`:

1. `python batch_creation.py create_resources`
    - create the resources
2. `python batch_creation.py build_image --image-name <image-name>`
    - build your Docker image on Azure Container Registry
3. `python batch_containers.py run_tasks`
    - run your batch pool

## Comments on Usage

The main advantage of this repository is it streamlines the process of scaling simulators using Azure Container Registry with Docker images. The only thing the user needs to do is write a Dockerfile containing their source code for running the simulator. In most cases, this is a very simple Docker image, and hence the Dockerfile is very concise. Building and running the image is done entirely using Azure Container Registry, which means you don't even need to install Docker locally!

## Scaling number of sims, number of tasks and number of instances in a pool

In order to specify the number of nodes in the pool, define the following arguments:
```
python batch_containers.py run_tasks --dedicated-nodes=<#_of_dedicated nodes> --low-pri-nodes=<#_of_lo_pri_nodes>
```
The command will ask in the user to enter the number of sims to run, and the brain name.

The number of tasks per node will be automatically be deduced as number_of_sims/(number_low_pri_nodes + number_dedicated_nodes)

### Note about modifying an existing pool

In the current incarnation of this package, if you want to modify a pool by adding more nodes or changing files on the container, you have to recreate the pool with a new name. Reusing the same pool name, i.e.,

```
python batch_containers.py run_tasks --pool_name="existing-pool"
```

will cause the tasks to re-use the old pool, even if you pass new values for low-pri-nodes or dedicated-nodes. Instead, rebuild the pool image by

```
python batch_creation.py create_resources
```

and then re-run your tasks with a new** pool name `python batch_containers.py run_tasks --pool_name="new-pool-name"`. Functionality will be added soon to modify an existing pool or changing some container files without rebuilding.

** Worth noting, deleting the previous pool manually directly on Azure, waiting patiently for it to dissapear on Pool list, and running command `python batch_containers.py run_tasks  --pool_name="existing-pool"` would also work (or `python batch_containers.py run_tasks` if using default naming convention). More about how to delete an existing pool right bellow:

### How to Delete an Existing Pool

(1) Search for the Resource Group you selected when running `python batch_creation.py create_resources`

(2) On Overview tab, click over the item name with type "Batch Account" (by default: "<your_group_name>batch")

(3) On left pane, on 'Features' section, click over 'Pools'

(4) You can now see a drop down with the list of previously created pools

Note, deleting pools is the best way to completely ensure you don't run into additional costs once the brain training has completed.

### Building Windows Containers

The `build_image` function contains a few arguments for specifying the platform, image name, as well as the docker path. Here is an example of specifying a windows platform version with a different Dockerfile location:

```bash
python batch_creation.py build_image \
  --docker_folder=examples/cs-house-energy \
  --dockerfile_path=Dockerfile-windows \
  --platform=windows --image_name=winhouse
```

After building, you can run your tasks with the specific image you've created:

```bash
python batch_containers.py run_tasks --image_name=winhouse
```

### Installation

There is currently no updated `batch_orchestration` package. The best way to use this package is to install the bonsai-batch conda environment (Follow this [link](https://docs.conda.io/en/latest/miniconda.html) if you need to install conda):

```bash
conda update -n base -c defaults conda
conda env update -f environment.yml 
conda activate bonsai-preview
```

This provides the exact versions of the packages and python environment we used to test this library and therefore will give you the highest chance of success.

The first time you use this package you'll also need to login to azure and set your subscription appropriately:

```bash
az login
az account list -o table
az account set -s <subscription-id>
```

## Testing Docker Images

The only caveat is if you need to debug your Docker image, you will need to install Docker locally (or write a batch script to run on ACR, which is a pretty inefficient method of debugging). For example, after running the `batch_creation` script above, you could test your image by:


```bash
docker login azhvacacr.azurecr.io
# your username and password are available in the newconf.ini file
docker pull azhvacacr.azurecr.io/hvac:1.0
docker run -it azhvacacr.azurecr.io/hvac:1.0 bash
```

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.