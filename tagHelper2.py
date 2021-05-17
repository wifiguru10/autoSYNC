#!/usr/bin/ipython3 -i

### tagHelper2 by Nico Darrow

### Description
import sys
import time
import copy
from bcolors import bcolors

class tagHelper:
    db = None
    orgs = None #list of just org ids
    orgName = None #dict of org_id:name { <orgid> : "<name>" }
    nets = None # contains a dict of  { <net_id> : [ {<network> , <network>} ] , .. }
    golden_net = None #contains network of first found "golden" network
    tag_target   = "" #tags the Network as "active"
    tag_golden   = "" #tag for the golden network of the 
    orgs_whitelist = [] #usually configured via init()
    last_count = 0
    sync_change = 0

    #Initialize with network_Id
    def __init__(self, db, target, golden, orgs_WL):
        self.db = db
        self.orgs = []
        self.orgName = {}
        self.nets = {}
        self.tag_target = target
        self.orgs_whitelist = copy.deepcopy(orgs_WL)
        self.tag_golden = golden
        self.sync()
        return
    
    def show(self):
        print()
        print(f'\t{bcolors.OKBLUE}TagHelper: target[{bcolors.WARNING}{self.tag_target}{bcolors.OKBLUE}] golden[{bcolors.WARNING}{self.tag_golden}{bcolors.OKBLUE}]')
        print()
        print(f'\t\t{bcolors.HEADER}*************[{bcolors.OKGREEN}Orgs in scope{bcolors.HEADER}]*****************')
        print(bcolors.ENDC)
        print()
        #print(self.orgs)
        for o in self.orgName:
            o_name = self.orgName[o]
            print (f'{bcolors.OKGREEN}Organization [{bcolors.BOLD}{o_name}{bcolors.ENDC}{bcolors.OKGREEN}]\tOrg_ID [{bcolors.BOLD}{o}{bcolors.ENDC}{bcolors.OKGREEN}]')
            for n in self.nets:
                name = self.nets[n]['name']
                nid = self.nets[n]['id']
                tags = self.nets[n]['tags']
                if o == self.nets[n]['organizationId']: #if it's the correct org
                    if not self.tag_golden in tags:
                        print (f'\t{bcolors.OKGREEN}{bcolors.Dim}Network [{bcolors.ResetDim}{name}{bcolors.Dim}]\tNetID [{bcolors.ResetDim}{nid}{bcolors.Dim}]{bcolors.ENDC}')#\tTags{bcolors.ResetDim}{tags}{bcolors.ENDC}')
                    else:#GOLDEN NETWORK
                        print (f'\t{bcolors.OKGREEN}{bcolors.Dim}Network [{bcolors.ResetDim}{bcolors.WARNING}{name}{bcolors.OKGREEN}{bcolors.Dim}]\tNetID [{bcolors.ResetDim}{bcolors.WARNING}{nid}{bcolors.OKGREEN}{bcolors.Dim}]{bcolors.ENDC}')#\tTags{bcolors.BOLD}{tags}{bcolors.ENDC}')


        #import copy
            print()
        #print(self.orgName)
        return

    #returns True if there is a network change count
    def hasChange(self):
        if self.sync_change != 0:
            return True
        else:
            return False

    #kicks off all the discovery
    def sync(self):
        self.last_count=len(self.nets)
        self.loadOrgs()
        self.sync_change=len(self.nets)-self.last_count
        print(f'Last Count difference= {self.sync_change}')
        return

    #crawls all available orgs and collects orgs with tagged networks
    def loadOrgs(self):
        orgs = self.db.organizations.getOrganizations()
        self.nets = {}
        for o in orgs:
            name = o['name']
            orgID = o['id']
            #print(f'Searching ORG[{name}]')
            if not orgID in self.orgs_whitelist:
                if not len(self.orgs_whitelist) == 0:
            #        print("Not an org in scope")
                    continue
            try:
                nets = self.db.organizations.getOrganizationNetworks(orgID)
                #print(nets)
                for n in nets:
                    tags = n['tags']

                    #print(f'looking for {self.tag_target}')
                    if self.tag_target in tags:
                        #print("found one!*****************************************")
                        #print(n)
                    
                        if not orgID in self.orgs: self.orgs.append(orgID)
                        if not orgID in self.orgName:
                            self.orgName[orgID] = o['name']

                        #Looks for golden master
                        if self.tag_golden in tags:
                            #print("FOUND GOLDEN")
                            self.golden_net = n #captures the master in a variable
                        
                        nid = n['id']
                        self.nets[nid] = n
            except AttributeError as e:
                print(e)
            except:
                print(f'ERROR: No API support on Org[{name}] OrgID[{orgID}]')
                print("Unexpected error:", sys.exc_info()[0])
                #raise
        #time.sleep(10)
        return


    


    

