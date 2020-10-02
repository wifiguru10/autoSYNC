#!/usr/bin/python3

### changeLog by Nico Darrow

from datetime import *
import copy
from mNetlib import bcolors

class changelogHelper:
    db = None
    orgs = ""
    watch_list = "" #networkID watch list
    tag_target = ""
    changed_nets = ""
    adminEmail = "ndarrow@cisco.com"
    last_Checkin = ""
    ignoreAPI = ""

    def __init__(self, db, orgs):
        self.db = db
        uniqueOrgs = list(dict.fromkeys(orgs))
        self.orgs = uniqueOrgs
        self.watch_list = []
        self.changed_nets = []
        self.ignoreAPI = True
        return

    #adds network to watch-list
    def addNetwork(self, netid):
        self.watch_list.append(netid)
        uniqueNets = list(dict.fromkeys(self.watch_list)) #dedups
        self.watch_list = uniqueNets
        return

    #clears watching networks
    def clearNetworks(self):
        self.watch_list = []
        return

    def hasChange(self):
        current_time = datetime.isoformat(datetime.utcnow()) + 'Z'
        self.changed_nets = []
        if self.last_Checkin == "":
            self.last_Checkin = current_time
            return True
        
        changes = self.getChanges(self.last_Checkin)
        hasChange = False
        for c in changes:
            #print(c)
            if 'adminEmail' in c and c['adminEmail'] == self.adminEmail:
                if 'networkId' in c and c['networkId'] in self.watch_list:
                    if 'page' in c and c['page'] == 'via API' and self.ignoreAPI:
                        continue
                    else:
                        print(f'{bcolors.FAIL}ChangLog Detected change!{bcolors.ENDC}')
                        #print(c)
                        if not c['networkId'] in self.changed_nets: #remove duplicates
                            self.changed_nets.append(c['networkId'])
                        self.last_Checkin = current_time
                        hasChange = True

            #the following is supposed to sync any new network that has a "TAG" added but isn't currently in the watch_list
            if 'networkId' in c and not c['networkId'] in self.watch_list and len(self.tag_target) > 0 and c['label'] == 'Network tags' and self.tag_target in c['newValue']:
                print(f'{bcolors.WARNING}NEW NETWORK DETECTED{bcolors.ENDC}')
                self.changed_nets.append(c['networkId'])
                self.watch_list.append(c['networkId'])
                hasChange = True

        self.last_Checkin = current_time
        return hasChange

    def getChanges(self, TS):
         #{ 'ts': '2020-09-17T16:31:54.857306Z',
         #  'adminName': 'Nico Darrow',
         #  'adminEmail': 'ndarrow@cisco.com',
         #  'adminId': '577586652210300701',
         #  'networkName': 'AutoSync Test 21',
         #  'networkId': 'N_577586652210342748',
         #  'page': 'Organization overview',
         #  'label': 'Network tags',
         #  'oldValue': '["autoSYNC"]',
         #  'newValue': '[]'},
         results = []
         print(f'{bcolors.OKBLUE}Looking for changes at time {bcolors.WARNING}{TS}{bcolors.ENDC}')
         #print(self.orgs)
         for o in self.orgs:
            res = self.db.organizations.getOrganizationConfigurationChanges(o,startingAfter=TS)
            results = results + res

         #print(results)
         return results




###
