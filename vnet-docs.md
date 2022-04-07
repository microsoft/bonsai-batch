# Example: Provisioning a Pool within a Virtual Network

1. Create Virtual network and subnet
2. Provision Pool
3. Run tasks

## Requirements

- **Authentication**: the Batch Client API must use Azure Active Directory (AAD) authentication. For our purposes we will use a Service Principal to authenticate our batch requests to AAD:
  - Please [register your Azure batch application](https://docs.microsoft.com/en-us/azure/batch/batch-aad-auth#register-your-application-with-a-tenant) with AAD.
  - Retrieve a [tenand id](https://docs.microsoft.com/en-us/azure/batch/batch-aad-auth#get-the-tenant-id-for-your-active-directory) for your Azure Active Directory and paste it into the configuration file provided.
  - Create a [secret](af1904e2-a0a9-4553-9a74-577567df8762) for your application and retrieve the key.
	- Use the Azure IAM portal to assign `Contributor` access to the batch pool and virtual network

## VNet requirements

- **Region and subscription**: the VNet must be in the same subscription and region as the batch account you use to create the pool
- **Subnet size**: the subnet must have enough unassigned IP addresses to accommodate the number of VMs targeted for the pool. This should equal the number of total nodes you request, i.e., the sum of `LOW_PRI_NODES` and `DEDICATED_NODES` in your configuration file.

## Provisioning a Pool within a Virtual Network

1. [Create](https://docs.microsoft.com/en-us/azure/virtual-network/manage-virtual-network#create-a-virtual-network) a virtual network using the [Azure Portal](https://docs.microsoft.com/en-us/azure/virtual-network/quick-create-portal) or through the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/network/vnet?view=azure-cli-latest#az-network-vnet-create). Ensure it meets the requirements specified above.
2. Copy the resource identifier for the virtual network and paste it into the configuration file at `config["VNET"]["SUBNET_ID"]`.
3. Paste the `client_id`, `secret` and `tenant_id` you created for your service principal and application into the values in `config["SERVICE"]`.
4. Run your tasks with your virtual network:

```bash
python batch_containers.py run_tasks --use_service_principal=True --use_vnet=True
```