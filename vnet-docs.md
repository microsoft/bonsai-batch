# Example: Provisioning a Pool within a Virtual Network

## Overview

1. Create Virtual Network
2. Create a service principal (service principal is the recommended approach, but see [other options](https://docs.microsoft.com/en-us/azure/batch/batch-aad-auth#request-a-secret-for-your-application) for authenticating with batch)
3. Add `Contributor` access for the Virtual Network and the Batch Account to the service principal
4. Update configuration files (`config.ini`)
5. Run tasks with `python batch_containers.py run_tasks --use_service_principal=True --use_vnet=True`

## Requirements

- Resource group, batch account, storage account, and virtual network
  - You can create the first three using the command: `python batch_creation.py create_resources`
- **Authentication**: the Batch Client API must use Azure Active Directory (AAD) authentication. For our purposes we will use a Service Principal to authenticate our batch requests to AAD:
  - Please [register your Azure batch application](https://docs.microsoft.com/en-us/azure/batch/batch-aad-auth#register-your-application-with-a-tenant) with AAD.
  - Retrieve a [tenand id](https://docs.microsoft.com/en-us/azure/batch/batch-aad-auth#get-the-tenant-id-for-your-active-directory) for your Azure Active Directory and paste it into the configuration file provided.
  - Create a [secret](af1904e2-a0a9-4553-9a74-577567df8762) for your application and retrieve the key
  - Use the Azure IAM portal to assign `Contributor` access to the batch pool and virtual network

## Adding an Application to AAD

1. Locate your Azure Active Directory (or create a new one) from the Azure portal. Locate your tenant-id and copy it to the configuration file `userconfig.ini` under `[SERVICE][TENANT_ID]`.
2. Navigate to the sidebar to App registrations:
    ![](imgs/aad-app.png)  
3. Click `New registration` and follow the wizard to create your application (the redirect URI can be safely left blank)
4. Click on `Certificates & secrets` and create a new secret. Copy the secret value (⚠️ important to copy the value, not the key) and paste it into the user configuration file `userconfig.ini` under `[SERVICE][SECRET]`.
5. Return to the homepage of your application, and locate the `Application (client) ID`. Copy the value and paste it into the user configuration file `userconfig.ini` under `[SERVICE][CLIENT_ID]`.

## VNet requirements

- **Region and subscription**: the VNet must be in the **same subscription and region** as the batch account you use to create the pool
- **Subnet size**: the subnet must have enough unassigned IP addresses to accommodate the number of VMs targeted for the pool. This should equal the number of total nodes you request, i.e., the sum of `LOW_PRI_NODES` and `DEDICATED_NODES` in your configuration file.

## Provisioning a Pool within a Virtual Network

1. [Create](https://docs.microsoft.com/en-us/azure/virtual-network/manage-virtual-network#create-a-virtual-network) a virtual network using the [Azure Portal](https://docs.microsoft.com/en-us/azure/virtual-network/quick-create-portal) or through the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/network/vnet?view=azure-cli-latest#az-network-vnet-create). Ensure it meets the requirements specified above.
2. Copy the resource identifier for the virtual network and paste it into the configuration file at `config["VNET"]["SUBNET_ID"]`. Should be of the form: `/subscriptions/subscription-id/resourceGroups/resource-group-id/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name`
3. Make sure you have populated the `client_id`, `secret` and `tenant_id` you created for your service principal and application into the values in `config["SERVICE"]`.
4. Grant `contributor` access to the application you created above to your Azure Batch resource, Azure virtual network, Azure Container Registry, and storage account. To grant access:
    - In the azure portal, locate your resource
    - Click on on the item `Access control (IAM)` in the blade
    - Click `+ Add` 
    - Select contributor access
    - Select `+ Select members` and locate your created application
    - Complete by pressing `Review and assign`
5. Run your tasks with your virtual network:

```bash
python batch_containers.py run_tasks --use_service_principal=True --use_vnet=True
```

## Containerizing AnyLogic Models and Running in Batch

To run an AnyLogic simulator on Azure Batch, you should ensure that you have the `exported.zip` archive containing your AnyLogic simulation model. Place that in a folder along with the Dockerfile provided in `samples/abca/Dockerfile`. You can then build and push the image to ACR in one-step using `python batch_creation.build_image` or in two separate steps using 1. (to build) using `docker build -t <your-image-name> .` and 2. (to tag and push it to ACR) with `docker tag <your-image-name> <your-registry-name>.azurecr.io/<your-image-name>` and `docker push <your-registry-name>.azurecr.io/<your-image-name>`.

Then to run the tasks on Azure Batch:

```bash
python batch_containers.py run_tasks --use_service_principal=True --use_vnet=True --task_to_run="find -name '*_linux.sh' -exec sh {} \;"
```

Please also ensure that you have a `.env` file saved locally with your (unexpired) Bonsai workspace id and access-key, or that you enter them manually using their arguments:

```bash
python batch_containers.py \
  run_tasks --use_service_principal=True --use_vnet=True \
  --task_to_run="find -name '*_linux.sh' -exec sh {} \;" \
  --workspace=<your-bonsai-workspace-id> \
  --access_key=<your-bonsai-access-key>
```

Warnings may appear in your `stdout.txt` of the form:

```
chmod: chromium/chromium-linux64/chrome: No such file or directory
```

This is not a breaking error and can be safely ignored. However, if you see the following

```bash
Exception in thread "Thread-1" Exception in thread "main" java.lang.RuntimeException: Protection error
        at java.lang.Thread.run(Thread.java:748)
java.lang.RuntimeException: Reinforcement Learning Experiment couldn't be created.        at activity_based_costing_analysis_bonsai.RLExperiment.main(RLExperiment.java:256)Caused by: java.lang.reflect.InvocationTargetException        ... 1 moreCaused by: java.lang.RuntimeException: Protection error        ... 1 more
```

this is a sign that you have not provided your Bonsai workspace-id and access-key correctly.
