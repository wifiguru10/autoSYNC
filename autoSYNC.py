#!/usr/bin/python3

### AutoSYNC v2 by Nico Darrow

### Description: 
#


import meraki
from datetime import datetime
import time
import copy
import sys,os

from mNetClone import * #new library
from bcolors import bcolors
import tagHelper2
import changelogHelper
import configparser
import get_keys as g


#Defaults.... get overriden by autoSYNC.cfg
orgs_whitelist = [] 
WRITE = False
SWITCH = False
tag_target = ''
tag_master = ''
TAGS = []


def loadCFG(db):

    cfg = {}

    print("LOADING CONFIG")
    config = configparser.ConfigParser()
    config.sections()
    config.read('autoSYNC.cfg')

    if 'true' in config['autoSYNC']['WRITE'].lower(): 
        cfg['WRITE'] = True
    else: 
        cfg['WRITE'] = False

    if 'true' in config['autoSYNC']['ALL_ORGS'].lower(): 
        orgs_whitelist = []
        cfg['whitelist'] = []
    else:  
        orgs_whitelist = config['autoSYNC']['Orgs'].replace(' ','').split(',')
        cfg['whitelist'] = config['autoSYNC']['Orgs'].replace(' ','').split(',')


    if 'true' in config['autoSYNC']['SWITCH'].lower(): 
        SWITCH = True
        cfg['SWITCH'] = True
    else: 
        SWITCH = False
        cfg['SWITCH'] = False


    cfg['tag_target'] = config['TAG']['TARGET']
    cfg['tag_master'] = config['TAG']['MASTER']

#    cfg['adminEmails'] = config['ChangeLog']['emails'].replace(' ','').lower().split(',')
    

    return cfg

   

def main():
    import time
    # client_query() # this queries current org and all client information and builds database
    # exit()

    # Fire up Meraki API and build DB's
   
    log_dir = os.path.join(os.getcwd(), "Logs/")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False, output_log=True, log_file_prefix=os.path.basename(__file__)[:-3], log_path='Logs/',) 
    cfg = loadCFG(db)

    th_array = []
    tag_target = cfg['tag_target']
    tag_master = cfg['tag_master']
#    adminEmails = cfg['adminEmails']
    orgs_whitelist = cfg['whitelist']
    WRITE = cfg['WRITE']
    SWITCH = cfg['SWITCH']

    th = tagHelper2.tagHelper(db, tag_target, tag_master, orgs_whitelist)
    orgs = th.orgs #get a lit of orgs
    
    #Master ChangeLog Helper
    clh = changelogHelper.changelogHelper(db, orgs)
    clh.ignoreAPI = False #make sure it'll trigger on API changes too, default is TRUE

    clh_clones = changelogHelper.changelogHelper(db, orgs)
    clh_clones.tag_target = tag_target #this sets the TAG so it'll detect additions of new networks during runtime
   
    
    loop = True #Set this to false to break loop
    
    mNets = {} #Dictionary of {'net_id': <mnet_obj>}
    master_netid = None
    mr_obj = [] #collect the networks
    last_changes = []
    longest_loop = 0
    loop_count = 0
    while loop:
        print()
        print(f'\t{bcolors.HEADER}****************************{bcolors.FAIL}START LOOP{bcolors.HEADER}*****************************')
        print(bcolors.ENDC)
        startTime = time.time()

        if WRITE:
            print(f'{bcolors.OKGREEN}WRITE MODE[{bcolors.WARNING}ENABLED{bcolors.OKGREEN}]{bcolors.ENDC}')
        else:
            print(f'{bcolors.OKGREEN}WRITE MODE[{bcolors.WARNING}DISABLED{bcolors.OKGREEN}]{bcolors.ENDC}')


        # TagHelper sync networks
        th.sync() #taghelper, look for any new networks inscope
        

        print()
        #Master Loader section
        netCount = 0
        for thn in th.nets:
            netCount += 1
            if loop_count == 0:
                print(f'{bc.WARNING}Network #{netCount} of [{len(th.nets)}] networks {bc.ENDC}')

            if not tag_master in th.nets[thn]['tags']:
                clh_clones.addNetwork(thn) #this goes into the CLONES bucket
                if not thn in mNets:
                    mNets[thn] = mNET(db, thn, WRITE).loadCache()
            else:
                if not thn in mNets:
                    mNets[thn] = mNET(db, thn, WRITE).loadCache()
                if master_netid != thn:
                    master_netid = thn
                    clh.clearNetworks() #wipes out previous master
                    print(f'MASTER NETWORK change to netid[{thn}]')
                    clh.addNetwork(thn)
            
        print()
        print(f'Master WL[{clh.watch_list}]')
        print(f'Clones WL[{clh_clones.watch_list}]')
        
        th.show() #show inscope networks/orgs
        
        
        #Cleanup for old mNET objects which have been removed from scope
        delList = []
        for mid in mNets: #cleanup
            if not mid in th.nets:
                delList.append(mid)

        for mid in delList:
            mNets.pop(mid)
            print(f'Dropping network[{mid}] from mNets DB')
            clh_clones.delNetwork(mid)
            if master_netid == mid: #assuming the master is changed/removed
                clh.delNetwork(mid) #remove it from changeloghelper 
                master_netid = None

        if master_netid == None:
            print(f'Something went wrong, no master netid!!!')
            continue
            
        print()
        master_change = clh.hasChange()
        clone_change = clh_clones.hasChange()
        print(f'{bcolors.OKGREEN}Changes Master[{bcolors.WARNING}{master_change}{bcolors.OKGREEN}] Clone[{bcolors.WARNING}{clone_change}{bcolors.OKGREEN}]')
        print()

        print(f'{bcolors.OKGREEN}Loop Count[{bcolors.WARNING}{loop_count}{bcolors.OKGREEN}]')

        print()
        
        if clone_change: #if there's a change to clones, run a short loop syncing just those networks
            print(f'{bcolors.FAIL}Change in a target Network Detected:{bcolors.Blink} Initializing Sync{bcolors.ENDC}')
            inscope_clones = clh_clones.changed_nets #gets list of networks changed
            for ic in inscope_clones:
                print(f'New Network detected!!!')
                if not ic in mNets:
                    mNets[ic] = mNET(db, ic, WRITE).loadCache()
                    mNets[ic].cloneFrom(mNets[master_netid])
                else:
                    mNets[ic].sync()
                    mNets[ic].cloneFrom(mNets[master_netid])
          

        elif master_change:
            print(f'{bcolors.FAIL}Master change Detected:{bcolors.Blink} Syncing Networks{bcolors.ENDC}')
            mcCount = 0
            mNets[master_netid].sync()
            avgTime = 0
            for net in mNets:
                if net == master_netid: continue
                mcCount += 1
                secondsGuess = avgTime * (len(th.nets)-1 - mcCount)
                print(f'{bc.WARNING}Network #{mcCount} of [{len(th.nets)-1}] networks. AvgTime[{round(avgTime,1)}] seconds. Estimated [{round(secondsGuess/60,1)}] minutes left{bc.ENDC}')
                startT = time.time()

                #Niftly little workaround for finding "out of compliance" networks, if there's an exception or error, re-sync and try again
                tries = 1
                while tries > 0:
                    try:
                        mNets[net].cloneFrom(mNets[master_netid])
                        tries = 0
                    except:
                        #potentially something changed... 
                        print(f'\t{bc.FAIL}ERROR:{bc.OKBLUE} Something changed in network [{bc.WARNING}{mNets[net].name}{bc.OKBLUE}]. Re-Syncing network and trying again....{bc.ENDC}')
                        mNets[net].sync()
                    tries -= 1
                

                endT = time.time()
                dur = round(endT-startT,2)
                if avgTime == 0:
                    avgTime = dur
                else:
                    avgTime = ( avgTime + dur )/ 2
               
        else:
            print(f'{bc.OKBLUE}No changes detected in target networks{bc.ENDC}')

        print()
    
        loop_count+=1
        
        print()
        endTime = time.time()
        duration = round(endTime-startTime,2)
        if duration > longest_loop: longest_loop = duration
        #print()
        if duration < 60:
            print(f'\t{bcolors.OKBLUE}Loop completed in {bcolors.WARNING}{duration}{bcolors.OKBLUE} seconds')
        else:
            duration = round(duration / 60,2)
            print(f'\t{bcolors.OKBLUE}Loop completed in {bcolors.WARNING}{duration}{bcolors.OKBLUE} minutes')


        total_networks = len(mNets)
        print(f'\t{bcolors.OKBLUE}Total Networks in scope{bcolors.BLINK_FAIL} {total_networks}{bcolors.ENDC}')
        mins = round(longest_loop/60,2)
        print(f'\t{bcolors.OKBLUE}Longest Loop [{bcolors.WARNING} {mins} {bcolors.OKBLUE}] minutes{bcolors.ENDC}')



        print()
        print(f'\t{bcolors.HEADER}****************************{bcolors.FAIL}END LOOP{bcolors.HEADER}*****************************')
        print(bcolors.ENDC)
        print()
        
        time.sleep(5)
        #while count_sleep > 0:
        #    time.sleep(1)
#       #     print(f'{bcolors.OKGREEN}z')
        #    count_sleep -= 1
        #print(bcolors.ENDC)
        print()
        #break #only used when wiping all

        #if loop_count > 5:
        #    loop = False
        # while loop


if __name__ == '__main__':
    start_time = datetime.now()

    print()
    try:
        main()
    except:
        print("Unexpected error:", sys.exc_info())
        raise
     

    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
