#!/usr/bin/python3 -i

### mNetClone by Nico Darrow

### Description
    # Second version, this version uses local cache and optimizations to speed up processing


import copy
import configparser
import os
import sys
import pickle
from time import *
from datetime import datetime,timedelta
from bcolors import bcolors as bc
import get_keys as g #need for request


import sys, getopt, requests, json


class mNET:

    db = None #this holds the dashboard API object
    org_id = ""
    name = ""
    url = ""
    productTypes = ""
    timeZone = ""
    tags = ""
    net_id = ""
    last_sync = None
    last_sync_duration = -1
    sync_interval = timedelta(minutes=1)

    CLEAN= False # This flag is set to True after a full sync, and Changlog can flip this to DIRTY to request a re-sync
    USE_CACHE = True # This is default set to true, set to False to disable

    SYNC_MR = True
    SYNC_MS = True
    SYNC_MG = True
    SYNC_MX = True


    ####CACHED RESULTS####
    #NETWORK
    getNetwork = None
    getNetworkAlertsSettings = None
    getNetworkGroupPolicies = None

    getNetworkTrafficAnalysis = None
    getNetworkSyslogServers = None
    getNetworkSnmp = None
    getNetworkWebhooksHttpServers = None
    
    #WIRELESS
    ssids_range = [] # should hold array of SSID_IDs, ex. [0,1,2,4,6,7]
    ssids = []
    ssids_l3 = []
    ssids_l7 = []
    ssids_ts = []
    ssids_ipsk = []
    getNetworkWirelessSsidIdentityPsks = None
    getNetworkWirelessSettings = None
    getNetworkWirelessBluetoothSettings = None
    getNetworkWirelessRfProfiles = None
    hasAironetIE = None #Leave this as true, first check will disable if it returns 404
    aironetie = []

    #SWITCH
    getNetworkSwitchMtu = None
    getNetworkSwitchSettings = None
    getNetworkSwitchDscpToCosMappings = None
    getNetworkSwitchRoutingMulticast = None
    getNetworkSwitchAccessControlLists = None
    getNetworkSwitchStormControl = None
    getNetworkSwitchQosRules = None
    getNetworkSwitchQosRulesOrder = None

    #MG
    getNetworkCellularGatewayDhcp = None
    getNetworkCellularGatewaySubnetPool = None
    getNetworkCellularGatewayUplink = None
    getNetworkCellularGatewayConnectivityMonitoringDestinations = None
    #getDeviceCellularGatewayPortForwardingRules = None

    #Cache Stuff
    cache_dir = os.path.join(os.getcwd(), "mNetCache/")
    f = ''
    stale_cache = timedelta(hours=48)
    mnet_cached = None
    hasCache = False #Leave False, marks existing disk cache



    def __init__(self, db, net_id, write_flag):
        startTime = time()
        self.db = db
        self.last_sync = datetime.utcnow()
        self.WRITE = write_flag
        self.net_id = net_id
        self.u_getNetwork()
        self.name = self.getNetwork['name']
        self.productTypes = self.getNetwork['productTypes']
        self.url = self.getNetwork['url']
        self.tags = self.getNetwork['tags']
        self.f = self.cache_dir + self.net_id + ".mnet"

        no_cache = True
        if os.path.exists(self.f) and self.USE_CACHE:
            mnet_cached = pickle.load(open(self.f,"rb"))
            cache_age = datetime.utcnow() - mnet_cached.last_sync
            print(f'Cache found! Its {cache_age} old')
            if cache_age < self.stale_cache:
                no_cache = False
                self.hasCache = True
                mnet_cached.db = db
                self.mnet_cached = mnet_cached
            else:
                print(f'Has Cache! But it is stale, re-syncing')
                self.clearCache()
        
        if 'appliance' in self.productTypes:
            self.SYNC_MX = True
        else: self.SYNC_MX = False
        if 'switch' in self.productTypes:
            self.SYNC_MS = True
        else: self.SYNC_MS = False
        if 'wireless' in self.productTypes:
            self.SYNC_MR = True
        else: self.SYNC_MR = False
        if 'cellularGateway' in self.productTypes:
            self.SYNC_MG = True
        else: self.SYNC_MG = False

        if no_cache:
            self.sync()
            #self.db = None
            #pickle.dump(self, open(self.f,"wb"))
            #self.db = db
        

        endTime = time()
        self.last_sync_duration = round(endTime - startTime,2)
        print(f'Loaded in {self.last_sync_duration} seconds')
        print()
        return 
    ### end-of __init__

    # returns timeDelta since the last sync
    def cacheAge(self):
        return datetime.utcnow() - self.last_sync

    # returns the cached object if exists otherwise returns the locally synced
    def loadCache(self):
        if not self.USE_CACHE: return
        if self.hasCache == True:
            if self.mnet_cached.db == None:
                self.mnet_cached.db = self.db
            return self.mnet_cached
        else:
            return self

    # writes it to disk for faster load times
    def storeCache(self):
        if not self.USE_CACHE: return
        db_tmp = self.db
        self.db = None
        pickle.dump(self, open(self.f, "wb"))
        self.db = db_tmp
        return

    # clears cache and kills disk backup
    def clearCache(self):
        self.hasCache = False
        self.mnet_cached = None
        if os.path.exists(self.f):
            os.remove(self.f)
        return

    # master SYNC function
    def sync(self):
        startTime = time()
        #print(f'NetID[{self.net_id}]')

        self.last_sync = datetime.utcnow()
        self.u_getNetwork()
        self.u_getNetworkAlertsSettings()
        self.u_getNetworkGroupPolicies()
        self.u_getNetworkSnmp()
        self.u_getNetworkTrafficAnalysis()
        try: self.u_getNetworkSyslogServers()
        except:
            print(f'{bc.FAIL}ERROR: Syslog configuration error on network{bc.White}[{self.net_id}{bc.White}]{bc.ENDC}')
        self.u_getNetworkWebhooksHttpServers()
        
        if self.SYNC_MR:
            self.u_getSSIDS()
            self.u_getSSIDS_l3()
            self.u_getSSIDS_l7()
            self.u_getSSIDS_ts()
            self.u_getSSIDS_ipsk()
            self.u_getSSIDS_aie()
            self.u_getNetworkWirelessSettings()
            self.u_getNetworkWirelessBluetoothSettings()
            self.u_getNetworkWirelessRfProfiles()

        if self.SYNC_MS:
            self.u_getNetworkSwitchMtu()
            self.u_getNetworkSwitchSettings()
            self.u_getNetworkSwitchDscpToCosMappings()
            self.u_getNetworkSwitchRoutingMulticast()
            self.u_getNetworkSwitchAccessControlLists()
            self.u_getNetworkSwitchStormControl()
            self.u_getNetworkSwitchQosRules()
            self.u_getNetworkSwitchQosRulesOrder()

        if self.SYNC_MG:
            self.u_getNetworkCellularGatewayDhcp()
            self.u_getNetworkCellularGatewaySubnetPool()
            self.u_getNetworkCellularGatewayUplink()
            self.u_getNetworkCellularGatewayConnectivityMonitoringDestinations()
            #self.u_getDeviceCellularGatewayPortForwardingRules() 
            


        endTime = time()
        self.last_sync_duration = round(endTime - startTime,2)
        print(f'{bc.White}Synced [{bc.WARNING}{self.name}{bc.White}] in {bc.WARNING}{self.last_sync_duration}{bc.White} seconds')
        print()
        self.CLEAN=True
        self.storeCache()

        return

    def u_getNetwork(self):
        self.getNetwork = self.db.networks.getNetwork(self.net_id)
        return self.getNetwork
    
    def u_getNetworkAlertsSettings(self):
        self.getNetworkAlertsSettings = self.db.networks.getNetworkAlertsSettings(self.net_id)
        return self.getNetworkAlertsSettings

    def u_getNetworkGroupPolicies(self):
        self.getNetworkGroupPolicies = self.db.networks.getNetworkGroupPolicies(self.net_id)
        return self.getNetworkGroupPolicies
    
    def u_getNetworkSnmp(self):
        self.getNetworkSnmp = self.db.networks.getNetworkSnmp(self.net_id)
        return self.getNetworkSnmp

    def u_getNetworkTrafficAnalysis(self):
        self.getNetworkTrafficAnalysis = self.db.networks.getNetworkTrafficAnalysis(self.net_id)
        return self.getNetworkTrafficAnalysis

    def u_getNetworkSyslogServers(self):
        self.getNetworkSyslogServers = self.db.networks.getNetworkSyslogServers(self.net_id)
        return self.getNetworkSyslogServers
        
    def u_getNetworkWebhooksHttpServers(self):
        self.getNetworkWebhooksHttpServers = self.db.networks.getNetworkWebhooksHttpServers(self.net_id)
        return self.getNetworkWebhooksHttpServers
        
       
    def u_getNetworkWirelessSettings(self):
        self.getNetworkWirelessSettings = self.db.wireless.getNetworkWirelessSettings(self.net_id)
        return self.getNetworkWirelessSettings
        
    def u_getNetworkWirelessBluetoothSettings(self):
        self.getNetworkWirelessBluetoothSettings = self.db.wireless.getNetworkWirelessBluetoothSettings(self.net_id)
        return self.getNetworkWirelessBluetoothSettings
        
    def u_getNetworkWirelessRfProfiles(self):
        self.getNetworkWirelessRfProfiles = self.db.wireless.getNetworkWirelessRfProfiles(self.net_id)
        return self.getNetworkWirelessRfProfiles

   
    def u_getSSIDS(self):
        self.ssids = []
        
        for ssid_num in range(0,15):
            ssid_tmp = self.db.wireless.getNetworkWirelessSsid(self.net_id, ssid_num)
            self.ssids.append(ssid_tmp)
            if not "Unconfigured SSID" in ssid_tmp['name'] and not ssid_num in self.ssids_range:
                self.ssids_range.append(ssid_num)
        return self.ssids
    
    #slowest function in the bunch
    def u_getSSIDS_aie(self):
        if self.hasAironetIE == None:
            #print(f'Network {self.name} has aironetIE extensions!!!')
            has_aie = self.getaironetie(self.net_id, 0)
            if has_aie == 'null': 
                self.hasAironetIE = False
                #print(f'Network {self.name} needs aironetIE NFO')
            else: 
                self.hasAironetIE = True
            
            #only do the full refresh if it's been cloned, cloneFrom_MR will set the aironetie = None
            if self.hasAironetIE:
                self.aironetie =[]
                for i in range(0,15):   
                    if i in self.ssids_range: #only query/refresh the active SSIDS
                        aie_code = self.getaironetie(self.net_id, i)
                        print(f'\t\t\t{bc.OKBLUE}Detecting AIE for SSID[{bc.WARNING}{i}{bc.OKBLUE}] Status[{bc.WARNING}{aie_code}{bc.OKBLUE}]{bc.ENDC}')
                        self.aironetie.append(aie_code) #-1 for unkown, 0 for off, 1 for on
        return self.aironetie

    def u_getSSIDS_l3(self):
        self.ssids_l3 = []
        for ssid_num in range(0,15):
            if ssid_num in self.ssids_range:
                self.ssids_l3.append(self.db.wireless.getNetworkWirelessSsidFirewallL3FirewallRules(self.net_id, ssid_num))
            else:
                self.ssids_l3.append([])
        return self.ssids_l3

    def u_getSSIDS_l7(self):
        self.ssids_l7 = []
        for ssid_num in range(0,15):
            if ssid_num in self.ssids_range:
                self.ssids_l7.append(self.db.wireless.getNetworkWirelessSsidFirewallL7FirewallRules(self.net_id, ssid_num))
            else:
                self.ssids_l7.append([])
        return self.ssids_l7

    def u_getSSIDS_ts(self):
        self.ssids_ts = []
        for ssid_num in range(0,15):
            if ssid_num in self.ssids_range:
                self.ssids_ts.append(self.db.wireless.getNetworkWirelessSsidTrafficShapingRules(self.net_id, ssid_num))
            else:
                self.ssids_ts.append([])
        return self.ssids_ts

    def u_getSSIDS_ipsk(self):    
        self.ssids_ipsk = []
        for ssid_num in range(0,15):
            if ssid_num in self.ssids_range:
                self.ssids_ipsk.append(self.db.wireless.getNetworkWirelessSsidIdentityPsks(self.net_id, ssid_num))
            else:
                self.ssids_ipsk.append([])
        return self.ssids_ipsk
 

    def u_getNetworkSwitchMtu(self):
        self.getNetworkSwitchMtu = self.db.switch.getNetworkSwitchMtu(self.net_id)
        return self.getNetworkSwitchMtu
        
    def u_getNetworkSwitchSettings(self):
        self.getNetworkSwitchSettings = self.db.switch.getNetworkSwitchSettings(self.net_id)
        return self.getNetworkSwitchSettings
        
    def u_getNetworkSwitchDscpToCosMappings(self):
        self.getNetworkSwitchDscpToCosMappings = self.db.switch.getNetworkSwitchDscpToCosMappings(self.net_id)
        return self.getNetworkSwitchDscpToCosMappings
        
    def u_getNetworkSwitchRoutingMulticast(self):
        self.getNetworkSwitchRoutingMulticast = self.db.switch.getNetworkSwitchRoutingMulticast(self.net_id)
        return self.getNetworkSwitchRoutingMulticast
       
    def u_getNetworkSwitchAccessControlLists(self):
        self.getNetworkSwitchAccessControlLists = self.db.switch.getNetworkSwitchAccessControlLists(self.net_id)
        return self.getNetworkSwitchAccessControlLists
        
    def u_getNetworkSwitchStormControl(self):
        try:
            self.getNetworkSwitchStormControl = self.db.switch.getNetworkSwitchStormControl(self.net_id)
        except:
            #print("Unexpected error:", sys.exc_info()[0])
            return
            #raise
        return self.getNetworkSwitchStormControl
        
    def u_getNetworkSwitchQosRules(self):
        self.getNetworkSwitchQosRules = self.db.switch.getNetworkSwitchQosRules(self.net_id)
        return self.getNetworkSwitchQosRules

    def u_getNetworkSwitchQosRulesOrder(self):
        self.getNetworkSwitchQosRulesOrder = self.db.switch.getNetworkSwitchQosRulesOrder(self.net_id)
        return self.getNetworkSwitchQosRulesOrder
    
    ##MG update functions
    def u_getNetworkCellularGatewayDhcp(self):
        self.getNetworkCellularGatewayDhcp = self.db.cellularGateway.getNetworkCellularGatewayDhcp(self.net_id)
        return self.getNetworkCellularGatewayDhcp

    def u_getNetworkCellularGatewaySubnetPool(self):
        self.getNetworkCellularGatewaySubnetPool = self.db.cellularGateway.getNetworkCellularGatewaySubnetPool(self.net_id)
        return self.getNetworkCellularGatewaySubnetPool

    def u_getNetworkCellularGatewayUplink(self):
        self.getNetworkCellularGatewayUplink = self.db.cellularGateway.getNetworkCellularGatewayUplink(self.net_id)
        return self.getNetworkCellularGatewayUplink

    def u_getNetworkCellularGatewayConnectivityMonitoringDestinations(self):
        self.getNetworkCellularGatewayConnectivityMonitoringDestinations = self.db.cellularGateway.getNetworkCellularGatewayConnectivityMonitoringDestinations(self.net_id)
        return self.getNetworkCellularGatewayConnectivityMonitoringDestinations

    #Per device rules, out of scope for now, can be done, some work needed. - MARK
    #def u_getDeviceCellularGatewayPortForwardingRules(self):
    #    self.getDeviceCellularGatewayPortForwardingRules = self.db.cellularGateway.getDeviceCellularGatewayPortForwardingRules(self.net_id)
    #    return self.getDeviceCellularGatewayPortForwardingRules


    #same as compare() but strips out ID/networkID for profiles/group policies etc
    def soft_compare(self, A, B):
        t_A = copy.deepcopy(A)
        t_B = copy.deepcopy(B)
        if 'id' in t_A: t_A.pop('id')
        if 'networkId' in t_A: t_A.pop('networkId')
        if 'groupPolicyId' in t_A: t_A.pop('groupPolicyId')
        if 'id' in t_B: t_B.pop('id')
        if 'networkId' in t_B: t_B.pop('networkId')
        if 'groupPolicyId' in t_B: t_B.pop('groupPolicyId')

        if 'dnsRewrite' in t_A: t_A.pop('dnsRewrite')
        if 'dnsRewrite' in t_B: t_B.pop('dnsRewrite')
        if 'adultContentFilteringEnabled' in t_A: t_A.pop('adultContentFilteringEnabled')
        if 'adultContentFilteringEnabled' in t_B: t_B.pop('adultContentFilteringEnabled')

            
        #had to add some logic to pop the "id" and "radsecEnabled". 'id' is unique and 'radsecEnabled' is beta for openroaming
        if 'radiusServers' in t_A:
            t_A['radiusServers'][0].pop('id')
            if 'radsecEnabled' in t_A['radiusServers'][0]: t_A['radiusServers'][0].pop('radsecEnabled')

            if 'radiusAccountingServers' in t_A: 
                t_A['radiusAccountingServers'][0].pop('id')  
                if 'radsecEnabled' in t_A['radiusAccountingServers'][0]: t_A['radiusAccountingServers'][0].pop('radsecEnabled')     
        if 'radiusServers' in t_B:
            t_B['radiusServers'][0].pop('id')
            if 'radsecEnabled' in t_B['radiusServers'][0]: t_B['radiusServers'][0].pop('radsecEnabled')

            if 'radiusAccountingServers' in t_B: 
                t_B['radiusAccountingServers'][0].pop('id')  
                if 'radsecEnabled' in t_B['radiusAccountingServers'][0]: t_B['radiusAccountingServers'][0].pop('radsecEnabled') 
            

        return self.compare(t_A,t_B)

    #compares JSON objects, directionarys and unordered lists will be equal 
    def compare(self, A, B):
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
                if a in B and not self.compare(A[a],B[a]):
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

    #This is the master function to clone from a different network. Each section marks/clean/unclean in order to sync smarter and without redoing the whole network object
    def cloneFrom(self, master):
        if not self.CLEAN:
            print(f'ERROR!!! Clone Target is unclean.... syncing')
            #self.sync()
            exit()
        #logic to prevent cloning from unclean masters
        if not master.CLEAN:
            print(f'ERROR!!! Cloning from unclean master')
            #master.sync()
            exit()
       
        print(f'{bc.White}Cloning network[{bc.WARNING}{self.name}{bc.White}][{bc.WARNING}{self.net_id}{bc.White}] from master[{bc.WARNING}{master.name}{bc.White}][{bc.WARNING}{master.net_id}{bc.White}] {bc.ENDC}')
        self.NET_cloneFrom(master) 
        if self.SYNC_MR: self.MR_cloneFrom(master)
        if self.SYNC_MS: self.MS_cloneFrom(master)
        if self.SYNC_MX: self.MX_cloneFrom(master)
        if self.SYNC_MG: self.MG_cloneFrom(master)

        print()
        return

    #This function covers cloning master network settings, alerts, group policies
    def NET_cloneFrom(self, master):
        
        print(f'{bc.OKGREEN}Starting Network configuration clone...{bc.ENDC}') 
        ### Clone Traffic Analytics Settings
        if not self.compare(master.getNetworkTrafficAnalysis, self.getNetworkTrafficAnalysis):
            if self.WRITE:
                print(f'\t{bc.OKBLUE}Updating Traffic Analytics Settings in network {bc.WARNING}{self.name}{bc.ENDC}')
                self.CLEAN = False
                self.db.networks.updateNetworkTrafficAnalysis(self.net_id,**master.getNetworkTrafficAnalysis)
        if not self.CLEAN:
            self.u_getNetworkTrafficAnalysis()
            self.CLEAN = True
        ### /end-Traffic Analytics Settings

        ## Clone Syslog Settings
        if not self.compare(master.getNetworkSyslogServers['servers'], self.getNetworkSyslogServers['servers']): 

            #kinda works.... will trigger "change" if the 'roles' are unordered
            if self.WRITE: 
                print(f'\t{bc.OKGREEN}Updating Syslog Settings in network {bc.WARNING}{self.name}{bc.ENDC}')
                self.CLEAN = False
                self.db.networks.updateNetworkSyslogServers(self.net_id, **{'servers': []})
                self.db.networks.updateNetworkSyslogServers(self.net_id,**master.getNetworkSyslogServers)

        if not self.CLEAN:
            self.u_getNetworkSyslogServers()
            self.CLEAN = True
        ## / end-Syslog Settings

        ## Clone SNMP Settings
        if not self.compare(master.getNetworkSnmp, self.getNetworkSnmp):
            if self.WRITE: 
                print(f'\t{bc.OKGREEN}Updating SNMP Settings in network {bc.WARNING}{self.name}{bc.ENDC}')
                self.CLEAN = False
                self.db.networks.updateNetworkSnmp(self.net_id,**master.getNetworkSnmp)
        ## / end-SNMP Settings
        if not self.CLEAN:
            self.u_getNetworkSnmp()
            self.CLEAN = True

        #Webhooks
        if not self.compare(master.getNetworkWebhooksHttpServers,self.getNetworkWebhooksHttpServers):
            curr_list = []
            for cwh in self.getNetworkWebhooksHttpServers:
                curr_list.append(cwh['name'])
            for mwh in master.getNetworkWebhooksHttpServers:
                if not mwh['name'] in curr_list:
                    if self.WRITE:
                        print(f'\t\t{bc.OKBLUE}-Webhook {bc.WARNING}{mwh["name"]}{bc.ENDC}')
                        self.CLEAN = False
                        mwh_tmp = copy.deepcopy(mwh)
                        mwh_tmp.pop('networkId')
                        self.db.networks.createNetworkWebhooksHttpServer(self.net_id, **mwh_tmp)
        if not self.CLEAN:
            self.u_getNetworkWebhooksHttpServers()
            self.CLEAN = True


        #Network Alerts
        if not self.compare(master.getNetworkAlertsSettings, self.getNetworkAlertsSettings):
            if self.WRITE:
                self.CLEAN = False
                self.db.networks.updateNetworkAlertsSettings(self.net_id, **master.getNetworkAlertsSettings)
        if not self.CLEAN:
            self.u_getNetworkAlertsSettings()        
            self.CLEAN = True
    
        #Group Policies
        for master_gp in master.getNetworkGroupPolicies:
            tempGP = copy.deepcopy(master_gp)
            tempGP.pop('groupPolicyId')
            if self.WRITE:
                local_gp = self.find_fromName(self.getNetworkGroupPolicies, tempGP['name'])

                if local_gp == None:
                    print(f'\t\t{bc.OKBLUE}Creating GP Policy named {tempGP["name"]}{bc.ENDC}')
                    self.CLEAN = False
                    try:
                        self.db.networks.createNetworkGroupPolicy(self.net_id,**tempGP)
                    except:
                        print(f'{bc.FAIL}ERROR: Cannot create GP policy named {tempGP["name"]}')

                else:
                    local_gpid = local_gp['groupPolicyId']
                    tempGP['groupPolicyId'] = local_gpid
                    #print()
                    #print(f'TMPGP {tempGP}')
                    #print()
                    #print(f'FROMGP {self.find_fromName(master.getNetworkGroupPolicies, tempGP["name"])}')
                    if not self.soft_compare(tempGP, self.find_fromName(master.getNetworkGroupPolicies, tempGP['name'])):
                        print(f'\t\t{bc.OKBLUE}Updating GP Policy named {tempGP["name"]}{bc.ENDC}')
                        self.CLEAN = False
                        self.db.networks.updateNetworkGroupPolicy(self.net_id, **tempGP)
                    #else:
                        #print(f'\t\t{bc.OKBLUE}SAME SAME!! GP Policy named {tempGP["name"]}{bc.ENDC}')
                        
        if not self.CLEAN:
            self.u_getNetworkGroupPolicies()
            self.CLEAN = True

        return

    def MS_cloneFrom(self, master):
        if not 'switch' in self.getNetwork['productTypes']:
            print(f'\t\t{bc.FAIL}Target network does not contain switching{bc.ENDC}')
            return
        
        print(f'{bc.OKGREEN}Starting Switch configuration clone...{bc.ENDC}') 
        #MTU
        if not self.compare(master.getNetworkSwitchMtu, self.getNetworkSwitchMtu):
            if self.WRITE:
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating switch MTU settings...{bc.ENDC}') 
                self.db.switch.updateNetworkSwitchMtu(self.net_id, **master.getNetworkSwitchMtu)
            if not self.CLEAN:
                self.u_getNetworkSwitchMtu()
                self.CLEAN = True
        
        #Switch Settings
        if not self.compare(master.getNetworkSwitchSettings, self.getNetworkSwitchSettings):
            if self.WRITE:
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating switch default VLAN settings...{bc.ENDC}')
                self.db.switch.updateNetworkSwitchSettings(self.net_id, **master.getNetworkSwitchSettings)
            if not self.CLEAN:
                self.u_getNetworkSwitchSettings()
                self.CLEAN = True

        #DSCP-COS Settings
        if not self.compare(master.getNetworkSwitchDscpToCosMappings, self.getNetworkSwitchDscpToCosMappings):
            if self.WRITE:
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating switch DSCP-COS settings...{bc.ENDC}')
                self.db.switch.updateNetworkSwitchDscpToCosMappings(self.net_id, **master.getNetworkSwitchDscpToCosMappings)
            if not self.CLEAN:
                self.u_getNetworkSwitchDscpToCosMappings()
                self.CLEAN = True         

        #Mutlicast Settings
        if not self.compare(master.getNetworkSwitchRoutingMulticast, self.getNetworkSwitchRoutingMulticast):
            if self.WRITE:
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating Switch Multicast settings...{bc.ENDC}')
                self.db.switch.updateNetworkSwitchRoutingMulticast(self.net_id, **master.getNetworkSwitchRoutingMulticast)
            if not self.CLEAN:
                self.u_getNetworkSwitchRoutingMulticast()
                self.CLEAN = True         


        #Switch ACL Settings
        if not self.compare(master.getNetworkSwitchAccessControlLists, self.getNetworkSwitchAccessControlLists):
            if self.WRITE:
                acls = copy.deepcopy(master.getNetworkSwitchAccessControlLists)
                acls['rules'].remove(acls['rules'][len(acls['rules'])-1]) #remove the default rule at the end
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating Switch ACL rules...{bc.ENDC}')
                self.db.switch.updateNetworkSwitchAccessControlLists(self.net_id, **acls)
            if not self.CLEAN:
                self.u_getNetworkSwitchAccessControlLists()
                self.CLEAN = True         

       
       #StormControl Settings
        if not self.compare(master.getNetworkSwitchStormControl, self.getNetworkSwitchStormControl):
            if self.WRITE:
                self.CLEAN = False
                print(f'\t {bc.OKGREEN}-Updating Switch StormControl rules...{bc.ENDC}')
                try:
                    self.db.switch.updateNetworkSwitchStormControl(self.net_id, **getNetworkSwitchStormControl)                
                except:
                    print(f'\t {bc.FAIL}-Failed to copy storm control settings{bc.ENDC}')

            if not self.CLEAN:
                self.u_getNetworkSwitchStormControl()
                self.CLEAN = True         

        #QoS Rules
        if not self.soft_compare(master.getNetworkSwitchQosRules, self.getNetworkSwitchQosRules):
            
            #{'ruleIds': ['577586652210270187', '577586652210270188', '577586652210270189']}
            rOrder_src = master.getNetworkSwitchQosRules
            rOrder_dst = self.getNetworkSwitchQosRules
            qosRuns = 0
            for rid in rOrder_src:
                rid_exists = False
                for rid2 in rOrder_dst:
                    if rid['vlan'] == None or rid['vlan'] == rid2['vlan']:
                        if rid['protocol'] == None or rid['protocol'] == rid2['protocol'] :
                            if rid['srcPort'] == None or rid['srcPort'] == rid2['srcPort']:
                                if rid['dstPort'] == None or rid['dstPort'] == rid2['dstPort']:
                                    if rid['dstPort'] == None or rid['dscp'] == rid2['dscp']:
                                        rid_exists = True

                        
                if rid_exists: 
                    #print(f'Duplicate rule, skipping!')
                    continue
                
                if qosRuns == 0:
                    qosRuns += 1
                    print(f'\t{bc.OKGREEN}-Cloning Switch QoS Rules...')


                #[{'id': '577586652210270187','vlan': None,'protocol': 'ANY','srcPort': None,'dstPort': None,'dscp': -1}, .. ]
                rule = None
                for r in master.getNetworkSwitchQosRules:
                    if r['id'] == rid['id']:
                        rule = copy.deepcopy(r)
                
                if rule == None:
                    print(f'{bc.FAIL}ERROR FINDING QoS RULE!!!{bc.ENDC}')
                else:
                    try:
                        #pop the id, and srcPort/dstPort if they're empty, otherwismne it'll throw an error
                        rule.pop('id')
                        if rule['srcPort'] == None: rule.pop('srcPort')
                        if rule['dstPort'] == None: rule.pop('dstPort') 
                        self.db.switch.createNetworkSwitchQosRule(self.net_id,**rule)
                        print(f'\t\t{bc.OKGREEN}-Rule Created[{bc.WARNING}{rule}{bc.OKGREEN}]')
                    except:
                        print(f'\t\t{bc.OKGREEN}-Rule already exists{bc.ENDC}')


        #stp = self.db.switch.getNetworkSwitchStp(mr_obj.net_id)
        #self.db.switch.updateNetworkSwitchStp(self.net_id,**stp)
        #print(f'\t {bcolors.OKGREEN}-Cloning switch Spanning Tree settings...')
        

        return
    
    def MX_cloneFrom(self, master):


        return

    def MG_cloneFrom(self, master):
        print(f'{bc.LightMagenta}Starting Cellular Gateway configuration clone...{bc.ENDC}') 
        #MG
        #getNetworkCellularGatewayDhcp = None
        if not self.compare(master.getNetworkCellularGatewayDhcp, self.getNetworkCellularGatewayDhcp):
            if self.WRITE:
                print(f'\t{bc.LightMagenta}Cloning DHCP settings...{bc.ENDC}') 
                self.CLEAN = False
                self.db.cellularGateway.updateNetworkCellularGatewayDhcp(self.net_id, **master.getNetworkCellularGatewayDhcp)
            if not self.CLEAN:
                self.u_getNetworkCellularGatewayDhcp()
                self.CLEAN = True

        #getNetworkCellularGatewaySubnetPool = None
        if not self.compare(master.getNetworkCellularGatewaySubnetPool, self.getNetworkCellularGatewaySubnetPool):
            if self.WRITE:
                print(f'\t{bc.LightMagenta}Cloning Subnet settings...{bc.ENDC}') 
                self.CLEAN = False
                self.db.cellularGateway.updateNetworkCellularGatewaySubnetPool(self.net_id, **master.getNetworkCellularGatewaySubnetPool)
            if not self.CLEAN:
                self.u_getNetworkCellularGatewaySubnetPool()
                self.CLEAN = True

        #getNetworkCellularGatewayUplink = None
        if not self.compare(master.getNetworkCellularGatewayUplink, self.getNetworkCellularGatewayUplink):
            if self.WRITE:
                print(f'\t{bc.LightMagenta}Cloning GatewayUplink settings...{bc.ENDC}') 
                self.CLEAN = False
                self.db.cellularGateway.updateNetworkCellularGatewayUplink(self.net_id, **master.getNetworkCellularGatewayUplink)
            if not self.CLEAN:
                self.u_getNetworkCellularGatewayUplink()
                self.CLEAN = True

        #endpoint broken? 500 error. still works tho
        #getNetworkCellularGatewayConnectivityMonitoringDestinations = None
        if not self.compare(master.getNetworkCellularGatewayConnectivityMonitoringDestinations, self.getNetworkCellularGatewayConnectivityMonitoringDestinations):
            if self.WRITE:
                self.CLEAN = False
                try:
                    print(f'\t{bc.LightMagenta}Cloning ConnectivityMonitoring settings...{bc.ENDC}') 
                    self.db.cellularGateway.updateNetworkCellularGatewayConnectivityMonitoringDestinations(self.net_id, **master.getNetworkCellularGatewayConnectivityMonitoringDestinations)
                except:
                    #something
                    pass
                    #print(f'Still has that error... CGCMD')
            if not self.CLEAN:
                self.u_getNetworkCellularGatewayConnectivityMonitoringDestinations()
                self.CLEAN = True
        
        #getDeviceCellularGatewayPortForwardingRules = None
        #if not self.compare(master.getDeviceCellularGatewayPortForwardingRules, self.getDeviceCellularGatewayPortForwardingRules):
        #    if self.WRITE:
        #        self.CLEAN = False
        #        self.db.cellularGateway.updateDeviceCellularGatewayPortForwardingRules(self.net_id, **master.getDeviceCellularGatewayPortForwardingRules)
        #    if not self.CLEAN:
        #        self.u_getDeviceCellularGatewayPortForwardingRules()
        #        self.CLEAN = True


        #print(f'{bc.OKGREEN}Cellular Gateway clone...DONE{bc.ENDC}') 
        return
    
    
    def MR_cloneFrom(self, master):

        print(f'{bc.OKBLUE}Starting Wireless configuration clone...{bc.ENDC}') 

        #some optimizations
        CLEAN_L3 = True
        CLEAN_L7 = True
        CLEAN_TS = True

        #SSIDS
        
        #Process all SSIDs
        for i in range(0,15):
            if 'Unconfigured SSID' in self.ssids[i]['name'] and 'Unconfigured SSID' in master.ssids[i]['name']: #Don't process SSIDs that are unconfigured
                #print("bypass!!!") 
                continue
            if not self.soft_compare(master.ssids[i], self.ssids[i]):
                temp_SSID = copy.deepcopy(master.ssids[i]) #Make a copy of the master SSID.... overrides will be needed to write
                print(f'\t-{bc.OKBLUE} SSID_Num[{i}] configuring SSID[{master.ssids[i]["name"]}] ')

                ###  START OF THE OVERRIDES/EXCEPTIONS
                if 'encryptionMode' in temp_SSID and temp_SSID['encryptionMode'] == 'wpa-eap':
                    temp_SSID['encryptionMode'] = 'wpa'
                #If the SSID has a single radius server, it'll error if these are set to "None" so pop them
                if 'radiusFailoverPolicy' in temp_SSID and temp_SSID['radiusFailoverPolicy'] == None:
                    temp_SSID.pop('radiusFailoverPolicy')
                    #temp_SSID['radiusFailoverPolicy'] = 'Allow access'
                if 'radiusLoadBalancingPolicy' in temp_SSID and temp_SSID['radiusLoadBalancingPolicy'] == None:
                    temp_SSID.pop('radiusLoadBalancingPolicy')
                    #temp_SSID['radiusLoadBalancingPolicy'] = 'Strict priority order'
                if not 'apTagsAndVlanIds' in temp_SSID: #this is to fix the case where the "target" network has APvlanTags but the source does not. This wipes the target if the source has no tags.
                    temp_SSID['apTagsAndVlanIds']= []
                

                config = configparser.ConfigParser()
                config.sections()
                config.read('autoSYNC.cfg')
                secret = config['RAD_KEYS']['_ALL_'].replace('"','').replace(' ','')
                if temp_SSID['name'] in config['RAD_KEYS']:
                    secret = config['RAD_KEYS'][temp_SSID['name']].replace('"','').replace(' ','')
                if "meraki123!" in secret:
                        print(f'\t\t{bc.FAIL}Using DEFAULT!!! Radius Secret [{bc.WARNING}{secret}{bc.FAIL}]')
                        #sys.exit(1)   

                if 'radiusServers' in temp_SSID:
                    #print(f'{bc.OKGREEN}Using Secret [{bc.WARNING}{secret}{bc.OKGREEN}]')
                    for rs in temp_SSID['radiusServers']:
                        rs['secret'] = secret

                if 'radiusAccountingServers' in temp_SSID:
                    for ras in temp_SSID['radiusAccountingServers']:
                        ras['secret'] = secret
         
                
                
                ### END OF THE OVERRIDES/EXCEPTIONS


                try:
                    #print(f'Writing {temp_SSID}')
                    if self.WRITE: 
                        self.ssids[temp_SSID['number']] = self.db.wireless.updateNetworkWirelessSsid(self.net_id,**temp_SSID)
                        self.CLEAN = False
                except:
                    print(f'Error writing SSID[{temp_SSID["name"]}]')
                    print(temp_SSID)
                    print("Unexpected error:", sys.exc_info()) 
                    raise

            #Clone the L3 FW rules
            if not self.compare(self.ssids_l3[i], master.ssids_l3[i]):
                #print(f'L3 is not the same')
                print(f'\t\t-{bc.OKBLUE} Copied L3 rules for SSID[{self.ssids[i]["name"]}] ')
                lanAccess = True
                l3rules = copy.deepcopy(master.ssids_l3[i])
                newL3 = {}
                newL3['rules'] = []
                for rule in l3rules['rules']:
                    if rule['destCidr'] == "Local LAN":
                        if rule['policy'] == "deny": lanAccess = False
                        else: lanAccess = True
                        
                        l3rules['rules'].remove(rule) #pull out the allow Lan Access rule, it's boolean
                    if rule['comment'] == "Default rule" or not rule['destCidr'] == "Local LAN":
                        newL3['rules'].append(rule) #pull out default rule, always the same
                
                #print(f'L3 Rules are {newL3}')
                newL3['allowLanAccess'] = lanAccess
                if self.WRITE: 
                    self.ssids_l3[i] = self.db.wireless.updateNetworkWirelessSsidFirewallL3FirewallRules(self.net_id,i, **newL3)
                    self.CLEAN = False
                    CLEAN_L3 = False

            #Clone the L7 FW rules
            if not self.compare(self.ssids_l7[i], master.ssids_l7[i]):
                l7rules = copy.deepcopy(master.ssids_l7[i])
                #print(f'L7 not the same ... cloning')
                print(f'\t\t-{bc.OKBLUE} Copied L7 rules for SSID[{self.ssids[i]["name"]}] ')
                if self.WRITE: 
                    self.ssids_l7[i] = self.db.wireless.updateNetworkWirelessSsidFirewallL7FirewallRules(self.net_id,i, **l7rules)
                    self.CLEAN = False
                    CLEAN_L7 = False


            #Clone the TS Rules
            if not self.compare(self.ssids_ts[i], master.ssids_ts[i]):
                print(f'\t\t-{bc.OKBLUE} Copied Traffic Shaping rules for SSID[{self.ssids[i]["name"]}] ')
                try:
                    TSrules = copy.deepcopy(master.ssids_ts[i])
                    if self.WRITE: 
                        self.ssids_ts[i] = self.db.wireless.updateNetworkWirelessSsidTrafficShapingRules(self.net_id, i, **TSrules)
                        self.CLEAN = False
                        CLEAN_TS = False
                except:
                    print(f'\t\t-{bc.FAIL}Failed to update TrafficShaping. Make sure all rules are complete{bc.ENDC}')


            

        if not self.CLEAN:
            self.u_getSSIDS() #this also updates ssids_range
            if self.hasAironetIE: self.u_getSSIDS_aie()
            if not CLEAN_L3: self.u_getSSIDS_l3()
            if not CLEAN_L7: self.u_getSSIDS_l7()
            if not CLEAN_TS: self.u_getSSIDS_ts()
            self.CLEAN = True
        
        for i in self.ssids_range: # and self.hasAironetIE:
            if self.hasAironetIE and not self.compare(self.aironetie[i], master.aironetie[i]):
                if self.WRITE:
                    self.CLEAN = False
                    self.setaironetie(self.net_id, i, master.aironetie[i])
                    print(f'{bc.OKBLUE}\t\tConfiguring AironetIE[{bc.WARNING}{master.aironetie[i]}{bc.OKBLUE}] on SSID[{bc.WARNING}{i}{bc.OKBLUE}]{bc.ENDC}')

        if not self.CLEAN:
            if self.hasAironetIE: 
                self.hasAironetIE = None
                self.u_getSSIDS_aie()
            self.CLEAN = True

        #RFProfiles - (if it exists and not equal, delete/update. If it doesn't exist, create)
        self_RFPS= copy.deepcopy(self.getNetworkWirelessRfProfiles)
        master_RFPS = copy.deepcopy(master.getNetworkWirelessRfProfiles)
        for srfp in self_RFPS:
            srfp.pop('id')
            srfp.pop('networkId')
        for mrfp in master_RFPS:
            mrfp.pop('id')
            mrfp.pop('networkId')
       
        if not self.compare(self_RFPS,master_RFPS): #Profiles are NOT the same
            for masterRF in master.getNetworkWirelessRfProfiles:
                found = False
                for selfRF in self.getNetworkWirelessRfProfiles:
                    if masterRF['name'] == selfRF['name']:
                        #print(f'RF Profile[{masterRF["name"]}] FOUND')
                        found = True
                        if not self.soft_compare(masterRF, selfRF): #It's in there but might not be the same
                            print(f'\t{bc.OKBLUE}RF Profile[{bc.WARNING}{masterRF["name"]}{bc.OKBLUE}] !!! Updating RF Profile{bc.ENDC}')
                            newRF = copy.deepcopy(masterRF)
                            newRF.pop('id')
                            newRF.pop('networkId')
                            newRF.pop('name')
                            newRF = self.MR_rfp_pwr(newRF)
                            if self.WRITE: 
                                self.db.wireless.updateNetworkWirelessRfProfile(self.net_id,selfRF['id'], **newRF) 
                                self.CLEAN = False
                    
                #no more RFProfiles in self, create one
                if not found: 
                    print(f'\t{bc.OKBLUE}RF Profile[{bc.WARNING}{masterRF["name"]}{bc.OKBLUE}]!!! New RFP created in network{bc.ENDC}')
                    newRF = copy.deepcopy(masterRF)
                    newRF.pop('id')
                    newRF.pop('networkId')
                    newRF = self.MR_rfp_pwr(newRF)
                    if self.WRITE: 
                        self.db.wireless.createNetworkWirelessRfProfile(self.net_id,**newRF)
                        self.CLEAN = False
            #wouldn't be here without something being different, so at least resync this part
        if not self.CLEAN:
            self.u_getNetworkWirelessRfProfiles()
            self.CLEAN = True


        #SSIDS_iPSK
        #for ssid_num in range(0,15):
        ipsk_tmp = []
        for r in range(0,15):
            ipsk_tmp.append({})
        for ssid_num in self.ssids_range:
            #if not ssid_num in self.ssids_range: continue
            #ipsk_tmp.append({}) #keep track of master iPSKs so we can remove unused ones from local(self)
            for m_ipsk in master.ssids_ipsk[ssid_num]:
                if not m_ipsk['name'] in ipsk_tmp[ssid_num]:
                    ipsk_tmp[ssid_num][m_ipsk['name']] = m_ipsk['passphrase']

                #ipsks are not empty, find the matching group policy
                new_ipsk = copy.deepcopy(m_ipsk)
                new_ipsk.pop('id') #pop off the ID from master, new one will be created "local"
                master_GP_tmp = master.find_fromGPID(master.getNetworkGroupPolicies, str(new_ipsk['groupPolicyId'])) 
                local_GP_tmp = self.find_fromName(self.getNetworkGroupPolicies, str(master_GP_tmp['name']))
                new_ipsk['groupPolicyId'] = local_GP_tmp['groupPolicyId']
                exists = False
                for s_ipsk in self.ssids_ipsk[ssid_num]:
                    if new_ipsk['name'] == s_ipsk['name']:
                        exists = True #exists, ignore unless passwords are different
                        if not new_ipsk['passphrase'] == s_ipsk['passphrase']: #if passwords are different, delete the ipsk and re-create
                            if self.WRITE:
                                self.CLEAN = False
                                try:
                                    self.db.wireless.deleteNetworkWirelessSsidIdentityPsk(self.net_id, ssid_num, s_ipsk['id'])
                                except:
                                    print(f'ERROR: iPSK Issue, resyncing and trying again')
                                    self.u_getSSIDS_ipsk()
                                    self.db.wireless.deleteNetworkWirelessSsidIdentityPsk(self.net_id, ssid_num, s_ipsk['id'])

                                exists = False
                
                if not exists and self.WRITE:
                    self.CLEAN = False
                    try:
                        self.db.wireless.createNetworkWirelessSsidIdentityPsk(self.net_id, ssid_num, **new_ipsk)
                    except:
                        print(f'{bc.FAIL}iPSK already created or still there{bc.ENDC}')

            

        if not self.CLEAN:
            self.u_getSSIDS_ipsk()
            self.CLEAN = True
        
        #cleanUP local iPSK
        for ssid_num in self.ssids_range:
            for s_ipsk in self.ssids_ipsk[ssid_num]:
                if not s_ipsk['name'] in ipsk_tmp[ssid_num]:
                    if self.WRITE:
                        self.CLEAN = False
                        print(f'\t\t{bc.OKBLUE}-Removing Legacy iPSK[{s_ipsk["name"]}]{bc.ENDC}')
                        self.db.wireless.deleteNetworkWirelessSsidIdentityPsk(self.net_id, ssid_num, s_ipsk['id'])
        
        ### Clone Wireless Settings
        if not self.compare(master.getNetworkWirelessSettings, self.getNetworkWirelessSettings):
            if self.WRITE: 
                print(f'\t{bc.OKBLUE}-Updating Wireless Settings in network {bc.WARNING}{self.name}{bc.ENDC}')
                self.CLEAN = False
                self.db.wireless.updateNetworkWirelessSettings(self.net_id,**master.getNetworkWirelessSettings)
        if not self.CLEAN:
            self.u_getNetworkWirelessSettings()
            self.CLEAN = True
        ### /end-Wifi Settings

        ## Clone Bluetooth/IOT Settings
        if not self.compare(master.getNetworkWirelessBluetoothSettings, self.getNetworkWirelessBluetoothSettings):
            if self.WRITE: 
                print(f'\t{bc.OKBLUE}-Updating Bluetooth/IOT Settingsin network {bc.WARNING}{self.name}{bc.ENDC}')
                self.CLEAN = False
                self.db.wireless.updateNetworkWirelessBluetoothSettings(self.net_id,**btCFG)
        if not self.CLEAN:
            self.u_getNetworkWirelessBluetoothSettings()
            self.CLEAN = True
        ## / end-Bluetooth/IOT

        if not self.CLEAN:
            print(f'ERROR: Something when horribly wrong.... unclean clone....')
            sys.exit()
        #self.sync()  #if this object is CLEAN, then you shouldn't have to re-sync (basically rebuilding it from scratch)
        return

    #Helper function in order to set minimal power levels via API. Below certain values, API's will error out.
    def MR_rfp_pwr(self, RFP):
        if 'twoFourGhzSettings' in RFP:
            if 'minPower' in RFP['twoFourGhzSettings'] and RFP['twoFourGhzSettings']['minPower'] < 5:
                RFP['twoFourGhzSettings']['minPower'] = 5
            if 'maxPower' in RFP['twoFourGhzSettings'] and RFP['twoFourGhzSettings']['maxPower'] < 5:
                RFP['twoFourGhzSettings']['maxPower'] = 5
            
        if 'fiveGhzSettings' in RFP:
            if 'minPower' in RFP['fiveGhzSettings'] and RFP['fiveGhzSettings']['minPower'] < 5:
                RFP['fiveGhzSettings']['minPower'] = 8
            if 'maxPower' in RFP['fiveGhzSettings'] and RFP['fiveGhzSettings']['maxPower'] < 5:
                RFP['fiveGhzSettings']['maxPower'] = 8
        return RFP


    #returns object in list where "name" matches <name>
    def find_fromName(self, listDicts, name):
        for ld in listDicts:
            if ld['name'] == name:
                return ld #ld['groupPolicyId']
        return None

    #returns object in list where "name" matches <name>
    def find_fromGPID(self, listDicts, gpid):
        for ld in listDicts:
            if 'groupPolicyId' in ld and ld['groupPolicyId'] == gpid:
                return ld
        return None



    #Wipes SSIDs to default
    def wipeALL(self):
        if not self.WRITE:
            print(f'{bc.FAIL}ERROR, this network does not have the WRITE flag set{bc.ENDC}')
            return
        
        self.CLEAN = False
        count = 0
        print(f'{bc.FAIL}Wiping network wireless settings Net[{bc.Blink}{self.name}{bc.ENDC}]')
        #wipe all the SSIDs
        while count < 15:
            if self.WRITE: self.db.wireless.updateNetworkWirelessSsid(self.net_id, count, name="Unconfigured SSID "+str(count+1), enabled=False, authMode="open", ipAssignmentMode="NAT mode", minBitrate="1", bandSelection="Dual band operation", perClientBandwidthLimitUp="0", perClientBandwidthLimitDown="0", perSsidBandwidthLimitUp="0", perSsidBandwidthLimitDown="0", mandatoryDhcpEnabled=False, visible=True, availableOnAllAps= True, availabilityTags=[], useVlanTagging=False)
            count += 1
    
        #wipe all the RF profiles
        #current = self.db.wireless.getNetworkWirelessRfProfiles(self.net_id)
        current = self.getNetworkWirelessRfProfiles
        for rfp in current:
            if self.WRITE: self.db.wireless.deleteNetworkWirelessRfProfile(self.net_id, rfp['id'])

        #wipe all the iPSKs
        for i in self.ssids_range:
            #if i >= len(self.ssids_ipsk): continue #if there's 8 elements, index of 7 would be the 8th item. if i=8
            temp_ipsks = self.ssids_ipsk[i]
            if len(temp_ipsks) == 0: continue #No ipsk here... moving on
            for ipsk in temp_ipsks:
                if self.WRITE: 
                    #try:
                    self.db.wireless.deleteNetworkWirelessSsidIdentityPsk(self.net_id,i,ipsk['id'])
                    #except:
                    #    print(f'{bc.FAIL}ERROR: Cannot delete iPSK {ipsk["id"]}')


        #wipe all L3
        for i in self.ssids_range:
            temp_l3fw = self.ssids_l3[i]
            if len(temp_l3fw) == 2 and temp_l3fw['rules'][0]['policy'] == 'allow':
                continue #if there are only two rules and the default-LAN is default ('allow') not clear default
            if self.WRITE: self.db.wireless.updateNetworkWirelessSsidFirewallL3FirewallRules(self.net_id,i, rules = [], allowLanAccess = True)
        
        #wipe all L7
        for i in self.ssids_range:
            temp_l7fw = self.ssids_l7[i]['rules']
            if len(temp_l7fw) == 0:
                continue 
            if self.WRITE: self.db.wireless.updateNetworkWirelessSsidFirewallL7FirewallRules(self.net_id,i, rules = [])

        #Wipe Traffic shaping rules
        defaultTS = {'trafficShapingEnabled': True, 'defaultRulesEnabled': True, 'rules': []}
        for i in self.ssids_range:
            temp_ts = self.ssids_ts[i]
            if not self.compare(temp_ts, defaultTS):
                if self.WRITE: self.db.wireless.updateNetworkWirelessSsidTrafficShapingRules(self.net_id,i, **defaultTS)

        #WirelessSettings
        if self.WRITE:
            tmp_ws = {'meshingEnabled': False, 'ipv6BridgeEnabled': False, 'locationAnalyticsEnabled': False, 'ledLightsOn': True, 'upgradeStrategy': 'minimizeUpgradeTime'}
            self.db.wireless.updateNetworkWirelessSettings(self.net_id, **tmp_ws)
        

        #Bluetooth
        if self.WRITE:
            self.db.wireless.updateNetworkWirelessBluetoothSettings(self.net_id, **{'scanningEnabled': False, 'advertisingEnabled': False})

        #Group-Policies
        for t_gp in self.getNetworkGroupPolicies:
            if self.WRITE:
                print(f"Wiping GroupPolicyId['{t_gp['groupPolicyId']}']")
                self.db.networks.deleteNetworkGroupPolicy(self.net_id, t_gp['groupPolicyId'])


        print(f'{bc.OKGREEN}{bc.Blink}Done.{bc.ResetBlink} Wiped all SSIDs and RF-profiles{bc.ENDC}')

        #WEBHOOKS
        print(f'{bc.FAIL}Wiping network settings Net[{bc.Blink}{self.name}{bc.ENDC}]')
        for wh in self.getNetworkWebhooksHttpServers:
            if self.WRITE:
                self.db.networks.deleteNetworkWebhooksHttpServer(self.net_id,wh['id'])
        
        #ALERTS
        cleared = self.getNetworkAlertsSettings
        cleared['defaultDestinations'] = {'emails' : [], 'snmp' : False, 'allAdmins' : False, 'httpsServerIds' : []}
        for c in cleared['alerts']:
            if 'type' in c and 'enabled' in c:
                c['enabled'] = False
                c['snmp'] = False
                c['allAdmins'] = False
                c['httpServerIds'] = []
                c['alertDestinations'] = {'emails': [], 'snmp': False, 'allAdmins': False, 'httpServerIds': []}
        if self.WRITE:
            self.db.networks.updateNetworkAlertsSettings(self.net_id, **cleared)

        #SNMP
        if self.WRITE:
            self.db.networks.updateNetworkSnmp(self.net_id, **{'access' : 'none'})

        #Traffic Shaping
        if self.WRITE:
            self.db.networks.updateNetworkTrafficAnalysis(self.net_id, **{'mode' : 'disabled'})

        #Syslog Settings
        if self.WRITE:
            self.db.networks.updateNetworkSyslogServers(self.net_id, **{'servers': []})
        
        if self.WRITE:
            for i in range(0,15):
                for i in self.ssids_range:
                    
                    #defaultAIE = {'ccxNameIeEnabled': False, 'fastLaneEnabled': False}
                    #self.setaironetie(self.net_id, i, defaultAIE)
                    print(f'{bc.OKBLUE}\t\Defaulting AironetIE[{bc.WARNING}{self.aironetie[i]}{bc.OKBLUE}] on SSID[{bc.WARNING}{i}{bc.OKBLUE}]{bc.ENDC}')


        print(f'{bc.OKGREEN}{bc.Blink}Done.{bc.ResetBlink} Wiped all Alerts/NetworkSettings{bc.ENDC}')


        #Switch Settings
        #MTU
        if self.WRITE:
            self.db.switch.updateNetworkSwitchMtu(self.net_id, **{'defaultMtuSize': 9578, 'overrides': []})
        
        #Default VLAN
        if self.WRITE:
            self.db.switch.updateNetworkSwitchSettings(self.net_id, **{'vlan': 1, 'useCombinedPower': False, 'powerExceptions': []})

        #DSCP-COS
        defaultDSCPCOS = {'mappings': [{'dscp': 0, 'cos': 0, 'title': 'default'}, {'dscp': 10, 'cos': 0, 'title': 'AF11'}, {'dscp': 18, 'cos': 1, 'title': 'AF21'}, {'dscp': 26, 'cos': 2, 'title': 'AF31'}, {'dscp': 34, 'cos': 3, 'title': 'AF41'}, {'dscp': 46, 'cos': 3, 'title': 'EF voice'}]}
        if self.WRITE:
            self.db.switch.updateNetworkSwitchDscpToCosMappings(self.net_id, **defaultDSCPCOS)


        #Multicast
        defaultMC = {'defaultSettings': {'igmpSnoopingEnabled': True, 'floodUnknownMulticastTrafficEnabled': True}, 'overrides': []}
        if self.WRITE:
            self.db.switch.updateNetworkSwitchRoutingMulticast(self.net_id, **defaultMC)

        #ACL Rules
        #defaultACL = {'rules': [{'comment': 'Default rule', 'policy': 'allow', 'ipVersion': 'any', 'protocol': 'any', 'srcCidr': 'any', 'srcPort': 'any', 'dstCidr': 'any', 'dstPort': 'any', 'vlan': 'any'}]}
        defaultACL = {'rules': []}
        if self.WRITE:
            self.db.switch.updateNetworkSwitchAccessControlLists(self.net_id, **defaultACL)


        #QoS Rules
        if self.WRITE:
            for q_rid in self.getNetworkSwitchQosRules:
                self.db.switch.deleteNetworkSwitchQosRule(self.net_id, q_rid['id'])


        
        #Storm Control (TBD)

        
        #self.CLEAN = True
        self.sync()
        return
    ##END OF wipeALL
    def getorgid(self, p_apikey, p_orgname):
        #looks up org id for a specific org name
        #on failure returns 'null'

        r = requests.get('https://api.meraki.com/api/v0/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})

        if r.status_code != requests.codes.ok:
                return 'null'

        rjson = r.json()


        for record in rjson:
                if record['name'] == p_orgname:
                        return record['id']
        return('null')

    def getaironetie(self, p_netid, p_ssid):
            #looks up org id for a specific org name
            #on failure returns 'null'
            p_apikey = g.get_api_key()
            r = requests.get('https://api.meraki.com/api/v1/networks/%s/wireless/ssids/%s/overrides' % (p_netid, p_ssid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})

            if r.status_code != requests.codes.ok:
                    return 'null'

            rjson = r.json()


            return rjson

    def setaironetie(self, p_netid, p_ssid, p_data):
            #looks up org id for a specific org name
            #on failure returns 'null'

            p_apikey = g.get_api_key()

            r = requests.put('https://api.meraki.com/api/v1/networks/%s/wireless/ssids/%s/overrides' % (p_netid, p_ssid), data=json.dumps(p_data), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            

            if r.status_code != requests.codes.ok:
                return 'null'

            rjson = r.json()

            return rjson


### End of class mNET ######




if __name__ == '__main__':

    print()

    #mnet3.wipeALL()
    #mnet3.cloneFrom(mnet)

