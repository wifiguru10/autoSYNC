#!/usr/bin/python3

### AutoSYNC by Nico Darrow

### Description: 
#


import meraki
from datetime import datetime
import time
import copy
import sys

from mNetlib import *
import tagHelper2
import changelogHelper
import configparser
import get_keys as g

config = configparser.ConfigParser()
config.sections()
config.read('autoSYNC.cfg')

if 'true' in config['autoSYNC']['WRITE'].lower(): WRITE = True
else: WRITE = False

if 'true' in config['autoSYNC']['ALL_ORGS'].lower(): orgs_whitelist = []
else:
    orgs_whitelist = config['autoSYNC']['Orgs'].replace(' ','').split(',')
#    print(orgs_whitelist)

radius_secret = config['autoSYNC']['RADIUS_SECRET']

tag_target = config['TAG']['TARGET']
tag_master = config['TAG']['MASTER']

#################### User-Configurable 


### TAG VARIABLES

#tag_target  = "autoSYNC" #Unique per golden network
#tag_master  = "as:master" #to assign source/Gold
#tag_compliance = "as:OOC" #out of compliance

#radius_secret = 'meraki123'  #THIS IS NEEDED FOR ALL EAP!!! This is the key for all 802.1x radius AAA

#the following orgs_whitelist will limit the script to only monitoring specific orgs, or leave blank to search all
#orgs_whitelist = [] #Uncomment this line to scan ALL ORGS 
#orgs_whitelist = [ '1234567890' , '2345678901' ,'3456789012' ] #this object is shared across tagHelper instances, to keep whitelist in sync
#orgs_whitelist = [ '121177' , '577586652210266696' ,'577586652210266697' ] #this object is shared across tagHelper instances, to keep whitelist in sync

#WRITE = True   #Set to False to test the script (read-only)

#################### User-Configurable 



def main():

    # client_query() # this queries current org and all client information and builds database
    # exit()

    # Fire up Meraki API and build DB's
    
    db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False) 
    th_array = []
    th_tmp = tagHelper2.tagHelper(db, tag_target, tag_master,orgs_whitelist)
    th_array.append(th_tmp)

    #th2 = tagHelper2.tagHelper(db, tag_target2, tag_master, tag_clone, tag_exclude) 
    
    orgs = [] #get a lit of orgs
    for th in th_array:
        orgs = orgs + th.orgs
    
    #Master ChangeLog Helper
    clh = changelogHelper.changelogHelper(db, orgs)
    clh.ignoreAPI = False #make sure it'll trigger on API changes too, default is TRUE
    clh.addEmail("ndarrow@cisco.com")
    #clh.addNetwork('L_577586652210275901')

    clh_clones = changelogHelper.changelogHelper(db, orgs)
    clh_clones.tag_target = tag_target #this sets the TAG so it'll detect additions of new networks during runtime
    for th in th_array: #go through all tagHelpers and buid a list of clones to watch
        th_nets = th.nets
        for thn in th_nets:
            if not tag_master in th.nets[thn]['tags']:
                clh_clones.addNetwork(thn)
    #print(clh_clones.watch_list)

    loop = True #Set this to false to break loop
    
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

       
        if loop_count > 0: #if it's not the first loop, check for changes
            master_change = clh.hasChange()
            clone_change = clh_clones.hasChange()
        else:#force a full sync on first run
            master_change = True
            clone_change = False

        for th in th_array:
            if loop_count > 0: th.sync() #taghelper, look for any new networks inscope
            th.show() #show inscope networks/orgs

            if clone_change: #if there's a change to clones, run a short loop syncing just those networks
                print(f'{bcolors.FAIL}Change in a target Network Detected:{bcolors.Blink} Initializing Sync{bcolors.ENDC}')
                inscope_clones = clh_clones.changed_nets #gets list of networks changed
                if not len(inscope_clones) == 0:
                    mr_obj = []
                    for ic in inscope_clones:
                       mr_obj.append(MR_network(db,ic,WRITE))
                mr_obj.append(MR_network(db,clh.watch_list[0],WRITE)) 
            elif master_change:
                mr_obj = []
                if loop_count == 0:
                    print(f'{bcolors.FAIL}First-Loop Detected:{bcolors.Blink} Syncing Networks{bcolors.ENDC}')
                else: 
                    print(f'{bcolors.FAIL}Master change Detected:{bcolors.Blink} Syncing Networks{bcolors.ENDC}')
                
                for net in th.nets:
                    mr = MR_network(db,net,WRITE)
                    mr_obj.append(mr)

                   
            else:
                print(f'{bcolors.OKBLUE}No changes detected in target networks{bcolors.ENDC}')

            print()
        
        master = None
        master_num = 0
        for mro in mr_obj:
            if tag_master in mro.tags:
                if master_num > 1:
                    print(f'{bcolors.FAIL} ERROR: Multiple Master networks detected... exiting....')
                    exit()
                master = mro
                master_num += 1
                print(f'Master count {master_num}')
                clh.clearNetworks()
                clh.addNetwork(mro.net_id)
                continue
            else:
                clh_clones.addNetwork(mro.net_id)
       
        if master == None:
            print(f'{bcolors.ENDC}Warning: No master Network detected.... going to sleep for 5s')
            time.sleep(5)
            continue
        else:
            print(f'{bcolors.OKBLUE}Master is [{bcolors.WARNING}{master.name}{bcolors.OKBLUE}]{bcolors.ENDC}')
       
        print()
        for mro in mr_obj:
            if not master == mro and not master == None:
                try:
                    startT = time.time()
                    mro.clone(master)
                    #mro.wipeALL()
                    endT = time.time()
                    split = round(endT-startT,2)
                    if split > 2: 
                        print(f'\t\t{bcolors.OKBLUE} Network Cloned in {bcolors.WARNING}{split}{bcolors.OKBLUE}seconds!')
                        print()
                        print()
                except AttributeError as error:
                    print(f'ERROR: Try/Except fail. Cant clone {mro.name}.')
                    print(error)
                except TypeError as error:
                    print(f'ERROR: TypeError')
                    print(error)
                    sys.exit(1)
        
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


        total_networks = len(mr_obj)
        print(f'\t{bcolors.OKBLUE}Total Networks in scope{bcolors.BLINK_FAIL} {total_networks}{bcolors.ENDC}')
        mins = round(longest_loop/60,2)
        print(f'\t{bcolors.OKBLUE}Longest Loop [{bcolors.WARNING} {mins} {bcolors.OKBLUE}] minutes{bcolors.ENDC}')



        print()
        print(f'\t{bcolors.HEADER}****************************{bcolors.FAIL}END LOOP{bcolors.HEADER}*****************************')
        print(bcolors.ENDC)
        print()
        
        count_sleep = 15
        while count_sleep > 0:
            time.sleep(1)
#            print(f'{bcolors.OKGREEN}z')
            count_sleep -= 1
        print(bcolors.ENDC)
        print()
        loop_count+=1
        #break #only used when wiping all
        # while loop


if __name__ == '__main__':
    start_time = datetime.now()

    print()
    main()
    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
