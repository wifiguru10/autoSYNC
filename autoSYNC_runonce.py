#!/usr/bin/ipython3 -i

import meraki
import copy
import os
import pickle
#from mNetlib import *  
from mNetClone import * #new library

import tagHelper2
import time
import get_keys as g



db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False)

print()
print("What tag would you like to source from? Default is 'golden' if left blank")
tag_golden = input("TAG:")
if len(tag_golden) == 0:
    tag_golden  = "golden"

print()
print("What tag would you like to target? Default is 'autoSYNC' if left blank")
tag_target = input("TAG:")
if len(tag_target) == 0:
    tag_target  = "autoSYNC"


print(f'TAG Target[{tag_target}] Golden[{tag_golden}]')

orgs = db.organizations.getOrganizations()
orgs_whitelist = [] 

for o in orgs:
    orgs_whitelist.append(o['id'])
print(orgs_whitelist)



th = tagHelper2.tagHelper(db, tag_target, tag_golden, orgs_whitelist)
orgs = th.orgs #get a lit of orgs

if th.golden_net == None:
    print(f'Exiting because no golden network was found. Golden master needs both the TARGET and the GOLDEN tag applied')
    exit()

if not len(th.nets) >= 2:
    print(f'Needs at least two networks to clone/copy!')
    exit()

th.show()

golden_netid = th.golden_net['id']
golden_net = mNET(db, golden_netid, True).loadCache()

last_net = None

for n in th.nets:
    if th.nets[n]['id'] == th.golden_net['id']:
        continue
    mnet_test = mNET(db, n, True).loadCache()
    last_net = mnet_test
    mnet_test.cloneFrom(golden_net)
    

