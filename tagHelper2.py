#!/usr/bin/ipython3 -i

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
    last_count = 0
    sync_change = 0

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
            print (f'{bcolors.OKGREEN}Organization [{bcolors.BOLD}{o_name}{bcolors.ENDC}{bcolors.OKGREEN}]\tOrg_ID [{bcolors.BOLD}{o}{bcolors.ENDC}{bcolors.OKGREEN}]')
            for n in self.nets:
                name = self.nets[n]['name']
                nid = self.nets[n]['id']
                tags = self.nets[n]['tags']
                if o == self.nets[n]['organizationId']: #if it's the correct org
                    if not self.tag_master in tags:
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

if __name__ == '__main__':

    import meraki
    import copy
    import os
    import pickle
    from mNetClone import * #new library

    import tagHelper2
    import changelogHelper
    import time
    import get_keys as g

    tag_target  = "autoSYNC"
    tag_master  = "golden"
    orgs_whitelist = ['121177','577586652210266696','577586652210266697'] 

    db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False)
    org_id = '121177' #nixnet
    org_id2 = '577586652210266696' #nixlab
    org_id3 = '577586652210266697' # 'G6 Bravo' #

    source_netid = 'L_577586652210276021' #DN_Core Golden_v2
    target_netid = 'L_577586652210276079' #AutoSync Clone 1
    t2_netid = 'L_577586652210276080' #AutoSync Clone2


    th = tagHelper2.tagHelper(db, tag_target, tag_master, orgs_whitelist)
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
        if not tag_master in th.nets[thn]['tags']:
            clh_clones.addNetwork(thn) #this goes into the CLONES bucket
        else:
            clh.addNetwork(thn)
    print(f'Master WL[{clh.watch_list}]')
    print(f'Clones WL[{clh_clones.watch_list}]')

    


    

