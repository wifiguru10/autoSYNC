#!/usr/bin/ipython3 -i

#Example script to use tagHelper to find in-scope networks. for changes or reporting

import meraki
import copy
import os
import pickle
from mNetClone import * #new library

import tagHelper2
import changelogHelper
import time
import get_keys as g

#compares JSON objects, directionarys and unordered lists will be equal 
def compare(A, B):
    result = True
    if A == None and B == None: 
        return True
    if not type(A) == type(B): 
        #print(f"Wrong type")
        return False
    try:
        if not type(A) == int and not type(A) == bool and not len(A) == len(B): 
            #print(f'Not the same length')
            return False
    except:
        print()
    
    if type(A) == dict:
        for a in A:
            if a in B and not compare(A[a],B[a]):
                return False
    elif type(A) == list:
        for a in A:
            if not a in B:
                return False
    else:
        if not A == B:
            return False
    return result
##END-OF COMPARE

print()
print("What tag would you like to target? Default is 'autoSYNC' if left blank")
tag_target = input("TAG:")
if len(tag_target) == 0:
    tag_target  = "autoSYNC"


db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False)

tag_golden  = "golden"
orgs_whitelist = [] 

orgs = db.organizations.getOrganizations()
for o in orgs:
    orgs_whitelist.append(o['id'])
print(orgs_whitelist)

th = tagHelper2.tagHelper(db, tag_target, tag_golden, orgs_whitelist)
orgs = th.orgs #get a lit of orgs

#Master ChangeLog Helper
clh = changelogHelper.changelogHelper(db, orgs)
clh.ignoreAPI = False #make sure it'll trigger on API changes too, default is TRUE

clh_clones = changelogHelper.changelogHelper(db, orgs)
clh_clones.tag_target = tag_target #this sets the TAG so it'll detect additions of new networks during runtime

# TagHelper sync networks
th.sync() #taghelper, look for any new networks inscope
th.show() #show inscope networks/orgs

th_nets = th.nets
for thn in th_nets:
    if not tag_golden in th.nets[thn]['tags']:
        clh_clones.addNetwork(thn) #this goes into the CLONES bucket
    else:
        clh.addNetwork(thn)
print(f'Master WL[{clh.watch_list}]')
print(f'Clones WL[{clh_clones.watch_list}]')



print()
print("Do you want to modify the following networks, left blank will exit")
runme = input("YES/NO:")
if not runme.lower() == 'yes':
    print("fine...goodbye!")
    sys.exit()
print()



try:
    networkMulticast_default = db.switch.getNetworkSwitchRoutingMulticast(th.golden_net['id'])
except:
    print("Golden Network doesn't have IGMP settings. Loading DEFAULTS IGMP")
    networkMulticast_default = {'defaultSettings': {'igmpSnoopingEnabled': False,'floodUnknownMulticastTrafficEnabled': False},'overrides': []}


try:
    NetworkSwitchStormControl_default = db.switch.getNetworkSwitchStormControl(th.golden_net['id'])
except:
    print("Golden Network doesn't have STORM settings. No switches in it. Loading STORM Defaults")
    #throws error when there's no switch in network. So set the default
    NetworkSwitchStormControl_default = {'broadcastThreshold': 20,'multicastThreshold': 50,'unknownUnicastThreshold': 10}

print()
print(f'Total networks in scope: {len(th_nets)}')

for n in th_nets:
    #n is netID a tthis point, object is th_nets[n]
    net = th_nets[n]
    print(f'Network[{net["name"]}]')
    try:
        target_netMulticast = db.switch.getNetworkSwitchRoutingMulticast(n)

        if not compare( target_netMulticast, networkMulticast_default ):
            print("\tNOT THE SAME! Changing multicast/IGMP")
            db.switch.updateNetworkSwitchRoutingMulticast(n, **networkMulticast_default)

        
        #this part crashes without switches in it
        target_netStormControl = db.switch.getNetworkSwitchStormControl(n)
        if not compare( target_netStormControl, NetworkSwitchStormControl_default):
            print("\tNOT THE SAME! Changing storm control")
            db.switch.updateNetworkSwitchStormControl(n, **NetworkSwitchStormControl_default)

        print(f'\tDone')
    except:
        #throws error when there's no switch in network. So set the default
        print(f'\tNope. No switches?')
    
    print()

#db.switch.updateNetworkSwitchStormControl(mynet, **
