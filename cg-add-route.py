#!/usr/bin/env python
PROGRAM_NAME = "cg-add-route.py"
PROGRAM_DESCRIPTION = """
CloudGenix script
---------------------------------------
This script quickly adds a global route to a site for all elements at that site
"""
from cloudgenix import API, jd
import os
import sys
import argparse
from fuzzywuzzy import fuzz
import ipaddress

CLIARGS = {}
cgx_session = API()              #Instantiate a new CG API Session for AUTH
global_vars = {}

def parse_arguments():
    global CLIARGS
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=PROGRAM_DESCRIPTION
            )
    parser.add_argument('--token', '-t', metavar='"MYTOKEN"', type=str, 
                    help='specify an authtoken to use for CloudGenix authentication')
    parser.add_argument('--authtokenfile', '-f', metavar='"MYTOKENFILE.TXT"', type=str, 
                    help='a file containing the authtoken')
    parser.add_argument('--site-name', '-s', metavar='SiteName', type=str, 
                    help='The site to run the site health check for', required=True)
    parser.add_argument('--prefix', '-p', metavar='prefix', type=str, 
                    help='The IP Prefix for the destination route', default="")
    parser.add_argument('--next-hop', '-n', metavar='nexthop', type=str, 
                    help='The IP Next hop for the route', default="")
    parser.add_argument('--admin-distance', '-a', metavar='admindistance', type=str, 
                    help='The admin distance for the route (default: 1)', default="1")
    
    args = parser.parse_args()
    CLIARGS.update(vars(args)) ##ASSIGN ARGUMENTS to our DICT

def authenticate():
    print("AUTHENTICATING...")
    user_email = None
    user_password = None
    
    ##First attempt to use an AuthTOKEN if defined
    if CLIARGS['token']:                    #Check if AuthToken is in the CLI ARG
        CLOUDGENIX_AUTH_TOKEN = CLIARGS['token']
        print("    ","Authenticating using Auth-Token in from CLI ARGS")
    elif CLIARGS['authtokenfile']:          #Next: Check if an AuthToken file is used
        tokenfile = open(CLIARGS['authtokenfile'])
        CLOUDGENIX_AUTH_TOKEN = tokenfile.read().strip()
        print("    ","Authenticating using Auth-token from file",CLIARGS['authtokenfile'])
    elif "X_AUTH_TOKEN" in os.environ:              #Next: Check if an AuthToken is defined in the OS as X_AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
        print("    ","Authenticating using environment variable X_AUTH_TOKEN")
    elif "AUTH_TOKEN" in os.environ:                #Next: Check if an AuthToken is defined in the OS as AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
        print("    ","Authenticating using environment variable AUTH_TOKEN")
    else:                                           #Next: If we are not using an AUTH TOKEN, set it to NULL        
        CLOUDGENIX_AUTH_TOKEN = None
        print("    ","Authenticating using interactive login")
    ##ATTEMPT AUTHENTICATION
    if CLOUDGENIX_AUTH_TOKEN:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("    ","ERROR: AUTH_TOKEN login failure, please check token.")
            sys.exit()
    else:
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None            
    print("    ","SUCCESS: Authentication Complete")

def match_site():
    print_array = []
    global CLIARGS, global_vars
    
    search_site = CLIARGS['site_name']
    search_ratio = 0
    
    resp = cgx_session.get.sites()
    if resp.cgx_status:
        tenant_name = resp.cgx_content.get("name", None)
        print("TENANT NAME:",tenant_name)
        site_list = resp.cgx_content.get("items", None)    #EVENT_LIST contains an list of all returned events
        for site in site_list:                            #Loop through each EVENT in the EVENT_LIST
            check_ratio = fuzz.ratio(search_site.lower(),site['name'].lower())
            if (check_ratio > search_ratio ):
                site_id = site['id']
                site_name = site['name']
                
                search_ratio = check_ratio
                site_dict = site
    else:
        logout()
        print("ERROR: API Call failure when enumerating SITES in tenant! Exiting!")
        sys.exit((jd(resp)))
    print("Found SITE ")
    print("     Site Name: " , site_dict['name'])
    print("       Site ID: " , site_dict['id'])
    print("   Description: "  , site_dict["description"])
 
    global_vars['site_id'] = site_id
    global_vars['site_name'] = site_name
    global_vars['site_dict'] = site_dict


def go():
    global CLIARGS, global_vars
    site_id = global_vars['site_id']
    ####CODE GOES BELOW HERE#########
    resp = cgx_session.get.tenants()
    if resp.cgx_status:
        tenant_name = resp.cgx_content.get("name", None)
    else:
        logout()
        print("ERROR: API Call failure when enumerating TENANT Name! Exiting!")
        print(resp.cgx_status)
        sys.exit((vars(resp)))
    
    change_elem_array = []
    element_count = 0
    resp = cgx_session.get.elements()
    if resp.cgx_status:
        element_change_list = {}
        element_list = resp.cgx_content.get("items", None)    #EVENT_LIST contains an list of all returned events
        for element in element_list:                            #Loop through each EVENT in the EVENT_LIST
            if (element['site_id'] == site_id):
                element_count += 1
                print("Found ION to add static route to: ", element['name'])
                change_elem_array.append(element)
    else:
        logout()
        print("ERROR: API Call failure when enumerating SITES in tenant! Exiting!")
        sys.exit((jd(resp)))
    #get ip prefix
    ip_valid = False
    ip_prefix_str = CLIARGS['prefix']
    
    while (ip_valid == False):
        try:
            ip_prefix = ipaddress.ip_network(ip_prefix_str,strict=False)
            ip_valid = True
        except:
            if (ip_prefix_str != ""):
                print("")
                print("Invalid IP Prefix Detected...")
            ip_valid = False
            ip_prefix_str = str(input("Please enter the DEST PREFIX (x.x.x.x/z): "))

    #get ip address/next-hop
    ip_valid = False
    ip_next_hop_str = CLIARGS['next_hop']
    
    while (ip_valid == False):
        try:
            ip_next_hop = ipaddress.ip_address(ip_next_hop_str)
            ip_valid = True
        except:
            if (ip_next_hop_str != ""):
                print("")
                print("Invalid IP Next-HOP Detected...")
            ip_valid = False
            ip_next_hop_str = str(input("Please enter the NEXTHOP IP (x.x.x.x): "))
    
    #get METRIC
    ip_valid = False
    ip_metric_str = CLIARGS['admin_distance']
    
    while (ip_valid == False):
        try:
            ip_metric = str(int(ip_metric_str))
            ip_valid = True
        except:
            print("Invalid IP Admin Distance Detected...")
            ip_valid = False
            ip_metric_str = str(input("Please enter the ADMIN Distance (Default 1): "))
    
    #post to site_id and elements in site
    json_request = '{"description":null,"tags":null,"destination_prefix":"' + str(ip_prefix) + '","nexthops":[{"nexthop_ip":"' + str(ip_next_hop) + '","nexthop_interface_id":null,"admin_distance":"'+ str(ip_metric) + '","self":false}],"scope":"global","network_context_id":null}'
    for element in change_elem_array:
        user_input = ""
        while (user_input != "y" and user_input != "n"):
            user_input = str(input("Would you like to add the static route to " + str(element['name'] + " ?(y/n) ")))
        if (user_input == "y"):
            result = cgx_session.post.staticroutes(site_id, element['id'], json_request)
            if result.cgx_status:
                print("Route added Successfully")
            else:
                print("ERROR: API Call failure when enumerating TENANT Name! Exiting!")
                print(result.cgx_status)

    ####CODE GOES ABOVE HERE#########
  
def logout():
    print("Logging out")
    cgx_session.get.logout()

if __name__ == "__main__":
    parse_arguments()
    authenticate()
    match_site()
    go()
    logout()
