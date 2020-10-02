#!/usr/bin/python3

### tagHelper2 by Nico Darrow

### Description
import sys
import time
import copy

from mNetlib import bcolors

class tagHelper:
    db = None
    orgs = None #list of just org ids
    orgName = None #dict of org_id:name { <orgid> : "<name>" }
    nets = None # contains a dict of  { <net_id> : [ {<network> , <network>} ] , .. }
    tag_target   = "" #tags the Network as "active"
    tag_master   = "" #tag for the master network of the 
    orgs_whitelist = [] #usually configured via init()

    #Initialize with network_Id
    def __init__(self, db, target, master, orgs_WL):
        self.db = db
        self.orgs = []
        self.orgName = {}
        self.nets = {}
        self.tag_target = target
        self.orgs_whitelist = copy.deepcopy(orgs_WL)
        self.tag_master = master
        self.sync()
        return
    
    def show(self):
        print()
        print(f'\t{bcolors.OKBLUE}TagHelper: target[{bcolors.WARNING}{self.tag_target}{bcolors.OKBLUE}] master[{bcolors.WARNING}{self.tag_master}{bcolors.OKBLUE}]')
        print()
        print(f'\t\t{bcolors.HEADER}*************[{bcolors.OKGREEN}Orgs in scope{bcolors.HEADER}]*****************')
        print(bcolors.ENDC)
        print()
        #print(self.orgs)
        for o in self.orgName:
            o_name = self.orgName[o]
            print (f'{bcolors.OKGREEN}Organization [{bcolors.BOLD} {o_name} {bcolors.ENDC}{bcolors.OKGREEN}]\tOrg_ID [ {bcolors.BOLD}{o}{bcolors.ENDC}{bcolors.OKGREEN} ]')
            for n in self.nets:
                name = self.nets[n]['name']
                nid = self.nets[n]['id']
                tags = self.nets[n]['tags']
                if o == self.nets[n]['organizationId']: #if it's the correct org
                    if not self.tag_master in tags:
                        print (f'\t{bcolors.OKGREEN}{bcolors.Dim}Network [{bcolors.ResetDim} {name} {bcolors.Dim}]\tNetID [ {bcolors.ResetDim}{nid}{bcolors.Dim} ]\tTags {bcolors.ResetDim}{tags}{bcolors.ENDC}')
                    else:#GOLDEN NETWORK
                        print (f'\t{bcolors.OKGREEN}{bcolors.Dim}Network [{bcolors.ResetDim}{bcolors.WARNING} {name} {bcolors.OKGREEN}{bcolors.Dim}]\tNetID [ {bcolors.ResetDim}{bcolors.WARNING}{nid}{bcolors.OKGREEN}{bcolors.Dim} ]\tTags {bcolors.BOLD}{tags}{bcolors.ENDC}')


        #import copy
            print()
        #print(self.orgName)
        return

    #kicks off all the discovery
    def sync(self):
        self.loadOrgs()
        return

    #crawls all available orgs and collects orgs with tagged networks
    def loadOrgs(self):
        orgs = self.db.organizations.getOrganizations()
        for o in orgs:
            name = o['name']
            orgID = o['id']
            #print(name)
            if not orgID in self.orgs_whitelist:
                if not len(self.orgs_whitelist) == 0:
                    #print("Not an org in scope")
                    continue
            try:
                 ### Network Object
                 #{'id': 'N_577586652210342629',
                 # 'organizationId': '121177',
                 # 'name': 'AutoSync Test2',
                 # 'productTypes': ['wireless'],
                 # 'timeZone': 'America/Los_Angeles',
                 # 'tags': ['autoSYNC'],
                 # 'enrollmentString': None,
                 # 'url': 'https://n26.meraki.com/AutoSync-Test2/n/6kgJMbA/manage/usage/list'}]

                nets = self.db.organizations.getOrganizationNetworks(orgID)
                for n in nets:
                    tags = n['tags']

                    #print(f'looking for {self.tag_target}')
                    if self.tag_target in tags:
                        #print("found one!*****************************************")
                        #print(n)
                        if not orgID in self.orgs: self.orgs.append(orgID)
                        if not orgID in self.orgName:
                            self.orgName[orgID] = o['name']

                        nid = n['id']
                        self.nets[nid] = n
            except AttributeError as e:
                print(e)
            except:
                print(f'ERROR: No API support on Org[{name}] OrgID[{orgID}]')
                print("Unexpected error:", sys.exc_info()[0])
                #raise
        time.sleep(10)
        return

