__version__ = '0.1'
__author__ = 'Oren Brigg'
__author_email__ = 'obrigg@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"

import os
import meraki
import asyncio
import time
import meraki.aio
from mapping import mapping
from getpass import getpass
from rich import print as pp


async def main():
    async with meraki.aio.AsyncDashboardAPI(
        meraki_api_key,
        output_log=False, 
        suppress_logging=True, 
        maximum_concurrent_requests=10,
        wait_on_rate_limit=True
            ) as aiomeraki:
       
        for org in organization_list:
            if org['name'] == org_name:
                org_id = org['id']
        try:
            org_admins = await aiomeraki.organizations.getOrganizationAdmins(org_id)
        except meraki.exceptions.AsyncAPIError as e:
            pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
        except Exception as e:
            pp(f'[red]Some other ERROR: {e}')
        
        # Delete the lab networks
        try:
            network_list = await aiomeraki.organizations.getOrganizationNetworks(org_id)
        except meraki.exceptions.AsyncAPIError as e:
            pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
        except Exception as e:
            pp(f'[red]Some other ERROR: {e}')

        network_reset_list = [network['name'] for network in mapping]
        for network in network_list:
            if network['name'] in network_reset_list:
                try:
                    response = await aiomeraki.networks.deleteNetwork(network['id'])
                except meraki.exceptions.AsyncAPIError as e:
                    pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
                except Exception as e:
                    pp(f'[red]Some other ERROR: {e}')

                pp(f"[red]Deleted network {network['name']}")

        # Let's give it a few seconds to process...
        time.sleep(2)
        
        # Create the lab networks
        network_create_tasks = [create_network(aiomeraki, org_id, org_admins, network) for network in mapping]
        for task in asyncio.as_completed(network_create_tasks):
            await task


async def create_network(aiomeraki: meraki.aio.AsyncDashboardAPI, org_id, org_admins, network):
    # Create networks
    try: 
        new_network = await aiomeraki.organizations.createOrganizationNetwork(
                org_id, 
                name=network['name'], 
                productTypes=['appliance', 'switch', 'camera'], 
                timeZone="Asia/Jerusalem"
                )
    except meraki.exceptions.AsyncAPIError as e:
        pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
    except Exception as e:
        pp(f'[red]Some other ERROR: {e}')

    pp(f"[dark_orange]\tCreated network {network['name']}")
    
    # Associate network admins
    for admin in org_admins:
        if admin['email'] == network['admin']:
            try:
                reponse = await aiomeraki.organizations.updateOrganizationAdmin(
                    org_id, 
                    admin['id'], 
                    orgAccess='none', 
                    networks=[{'id': new_network['id'], 'access': 'full'}]
                    )
            except meraki.exceptions.AsyncAPIError as e:
                pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
            except Exception as e:
                pp(f'[red]Some other ERROR: {e}')

            pp(f"[yellow]\t\tAdded admin {network['admin']} to network {network['name']}")

    # Associate devices with network
    try:
        response = await aiomeraki.networks.claimNetworkDevices(new_network['id'], network['devices'])
    except meraki.exceptions.AsyncAPIError as e:
        pp(f'[red]Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }')
    except Exception as e:
        pp(f'[red]Some other ERROR: {e}')

    pp(f"[green]\t\t\tAdded the following devices to network {network['name']}: {network['devices']}")


if __name__ == '__main__':
    meraki_api_key = os.environ.get('MERAKI_DASHBOARD_API_KEY')
    if not meraki_api_key:
        meraki_api_key = getpass('Enter your Meraki Dashboard API Key: ')
    # Initialize and test Meraki SDK
    dashboard = meraki.DashboardAPI(meraki_api_key, output_log=False, suppress_logging=True)
    try:
        organization_list = dashboard.organizations.getOrganizations()
    except Exception as e:
        pp(f'[red]ERROR: {e}')
        raise Exception('Meraki API Key is invalid')

    org_name = "Cisco Israel"
    pp(f"Start: {time.ctime()}")
    #network_prefix = "CMNA-lite-Lab"
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    pp(f"End: {time.ctime()}")