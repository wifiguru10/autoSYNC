#!/usr/bin/python3

### mNetlib by Nico Darrow

### Description

    ##SSID Object
        #{'number': 0,
        #'name': 'Retail Guest',
        #'enabled': True,
        #'splashPage': 'None',
        #'ssidAdminAccessible': False,
        #'authMode': 'psk',
        #'psk': 'guestSSID!',
        #'encryptionMode': 'wpa',
        #'wpaEncryptionMode': 'WPA2 only',
        #'ipAssignmentMode': 'NAT mode',
        #'minBitrate': 11,
        #'bandSelection': 'Dual band operation',
        #'perClientBandwidthLimitUp': 0,
        #'perClientBandwidthLimitDown': 0,
        #'perSsidBandwidthLimitUp': 0,
        #'perSsidBandwidthLimitDown': 0,
        #'mandatoryDhcpEnabled': False,
        #'visible': True,
        #'availableOnAllAps': False,
        #'availabilityTags': ['guest']}

import copy
import configparser
import sys
import time

class bcolors:
 
    ResetAll = "\033[0m"

    Bold       = "\033[1m"
    Dim        = "\033[2m"
    Underlined = "\033[4m"
    Blink      = "\033[5m"
    Reverse    = "\033[7m"
    Hidden     = "\033[8m"

    ResetBold       = "\033[21m"
    ResetDim        = "\033[22m"
    ResetUnderlined = "\033[24m"
    ResetBlink      = "\033[25m"
    ResetReverse    = "\033[27m"
    ResetHidden     = "\033[28m"

    Default      = "\033[39m"
    Black        = "\033[30m"
    Red          = "\033[31m"
    Green        = "\033[32m"
    Yellow       = "\033[33m"
    Blue         = "\033[34m"
    Magenta      = "\033[35m"
    Cyan         = "\033[36m"
    LightGray    = "\033[37m"
    DarkGray     = "\033[90m"
    LightRed     = "\033[91m"
    LightGreen   = "\033[92m"
    LightYellow  = "\033[93m"
    LightBlue    = "\033[94m"
    LightMagenta = "\033[95m"
    LightCyan    = "\033[96m"
    White        = "\033[97m"

    BackgroundDefault      = "\033[49m"
    BackgroundBlack        = "\033[40m"
    BackgroundRed          = "\033[41m"
    BackgroundGreen        = "\033[42m"
    BackgroundYellow       = "\033[43m"
    BackgroundBlue         = "\033[44m"
    BackgroundMagenta      = "\033[45m"
    BackgroundCyan         = "\033[46m"
    BackgroundLightGray    = "\033[47m"
    BackgroundDarkGray     = "\033[100m"
    BackgroundLightRed     = "\033[101m"
    BackgroundLightGreen   = "\033[102m"
    BackgroundLightYellow  = "\033[103m"
    BackgroundLightBlue    = "\033[104m"
    BackgroundLightMagenta = "\033[105m"
    BackgroundLightCyan    = "\033[106m"
    BackgroundWhite        = "\033[107m"

    HEADER = '\033[97m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BLINK_FAIL = Red + Blink

    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
 

class MR_network:

    name  = ""
    db = None #this hold the Dashboard API Object
    org_id = ""
    url = ""
    timeZone = ""
    tags = ""
    net_id = ""
    wirelessSettings = "" #this holds 'getNetworkWirelessSettings'
    L3firewallRules = "" #this should hold an array of L3 rules [0] = SSID-0
    L7firewallRules = "" #this should hold an array of L7 rules [0] = SSID-0
    radius_secret = "meraki123!"
    ssids = {}  #  ssid[0] = {<SSID Object>}
    ssids_changed = ""  #holds array of SSID's that changed, to bypass writing to non-changed
    rfprofiles = {} 
    WRITE = False #default is False, init() sets this
    #Group Policies
    master_GP = None #this holds the master group policy list (for SSID reference, iPSK)
    local_GP  = None #this holds the Local networks GP list
    master_IPSK = {} #this should hold { '<SSID#>' : [{'id': 74,'name': 'PSK1', 'passphrase': 'somethingsomething!', 'groupPolicyId': 123},..] }


    #Initialize with network_Id
    def __init__(self, db, net_id, write_flag):
        self.ssids = {}
        network_info = db.networks.getNetwork(net_id)
        if "wireless" in network_info['productTypes']:
            self.db = db
            self.WRITE = write_flag
            self.net_id = net_id
            self.name = network_info['name']
            self.org_id = network_info['organizationId']
            self.url = network_info['url']
            self.timeZone = network_info['timeZone']
            self.tags = network_info['tags']        
            self.master_GP = []
            self.local_GP = []
            self.sync()
            return 
        else:
            print(f'ERROR: Cannot initialize MR_network object, source net[{net_id}] does not have a wireless nework')
        return
    ### end-of __init__
    #Pull the dashboard config from all SSIDs and updates stored
    def getSSIDS(self):
        count = 0
        while count < 15:
            self.getSSID(count)
            count += 1
        return
    
    #Pulls the dashboard config from a single SSID and updates stored
    def getSSID(self,ssid_num):
        self.ssids[ssid_num] = self.db.wireless.getNetworkWirelessSsid(self.net_id, ssid_num)
        return

    #Pulls the dashboard config for the RF Profiles
    def getRF(self):
        self.rfprofiles = copy.deepcopy(self.db.wireless.getNetworkWirelessRfProfiles(self.net_id))
        return

    #Get's latest version of config
    def sync(self):
        self.getSSIDS()
        self.getRF()
        return

    #returns the RF Profile matching the name
    def findRFP(self, pName, rfp_list):
        for rfp in rfp_list:
            if 'name' in rfp and pName == rfp['name']:
                return rfp
        return

 
    #Checks the current RFprofiles with the ones in 
    def updateRF(self):
        current = self.db.wireless.getNetworkWirelessRfProfiles(self.net_id)
        for rfp in self.rfprofiles:
            name = rfp['name']
            cfound = self.findRFP(name,current)
            if not cfound == None:
                if self.isSameRFP(rfp, cfound):
                    #print("SAME RF PROFILE PASSING")
                    continue
                else:
                    print(f'\t{bcolors.OKBLUE}Updating a RF profile [{bcolors.WARNING}{name}{bcolors.OKBLUE}]{bcolors.ENDC}')
                    rfp.pop('name') #this needs to be done otherwise the update will fail
                    #print(rfp)
                    if self.WRITE: self.db.wireless.updateNetworkWirelessRfProfile(self.net_id, rfProfileId=cfound['id'], **rfp)
            else:
                print(f' {bcolors.OKBLUE}-Creating a new RF Profile [{bcolors.WARNING}{name}{bcolors.OKBLUE}]')
                #print(rfp)
                if self.WRITE: self.db.wireless.createNetworkWirelessRfProfile(self.net_id, **rfp)
                
        return

    #returns True if the same, otherwise false if there's differences
    def isSameSSID(self, ssid1_obj, ssid2_obj):
        ossid = ssid1_obj #local SSID, "original"
        tssid = ssid2_obj #remote SSID, "target"
        for t in tssid:
            if t in ['dot11w', 'dot11r']: #until the endpoint is fixed, bypass
                continue
            if t == "radiusFailoverPolicy" or t == "radiusLoadBalancingPolicy": #Glitch not being able to set "None" so bypass
                continue
            if not t in ossid:
                print(f'Value [{t}] is not in ossid[{ossid}]')
                #time.sleep(5)
                return False
            if t in ossid and not ossid[t] == tssid[t] and not type(tssid[t]) == list and not type(tssid[t]) == dict:
                print(f'Value [{tssid[t]}] is not equal to ossid[{ossid[t]}]')
                #time.sleep(5)
                return False

            #'dot11w': {'enabled': False, 'required': False},                                                                           |
            #'dot11r': {'enabled': False, 'adaptive': False},   
            #THIS WONT WORK - BUG in API so 11r/11w settings can't be migrated at this time 11/2020
            #if t == 'dot11w':
            #    if not tssid[t]['enabled'] == ossid[t]['enabled']: return False
            #    if not tssid[t]['required'] == ossid[t]['required']: return False
            #if t == 'dot11r':
            #    if not tssid[t]['enabled'] == ossid[t]['enabled']: return False
            #    if not tssid[t]['adaptive'] == ossid[t]['adaptive']: return False
 
            #this will catch radius servers
            if type(tssid[t]) == list and not t in ['dot11w', 'dot11r']:
                # [{'id': 577586652210309197, 'host': '56.43.23.23', 'port': 1812, 'radsecEnabled': True}]  
                if not len(tssid[t]) == len(ossid[t]): #if the amount of entries don't match, lose equivalency :P
                    print(f'{bcolors.OKBLUE}LIST LENTH MISMATCH')
                    return False
            
            ### <TODO> We should be able to compare iPSKs keys, but can't without WLAN-ID
            #if t == 'authMode' and tssid[t] == 'ipsk-without-radius':
            #    print("Matching IPSK SSID")
            #    tipsk = self.db.wireless.getNetworkWirelessSsidIdentityPsks(mr_obj.net_id,count)
 
        return True

    #returns True if they're the same contents
    def isSameRFP(self, rfp1, rfp2):
        for r in rfp1:
            if r == 'id' or r == 'networkId':
                continue
            if r in rfp2 and not rfp1[r] == rfp2[r]:
                return False
        return True

    #returns true if both sets of alert{} is the same
    def isSameAlerts(self, alert1, alert2):
        for a in alert1:
            if a in alert2 and not alert1[a] == alert2[a]:
                return False
        return True

    #Wipes SSIDs to default
    def wipeALL(self):
        count = 0
        print(f'{bcolors.FAIL}Wiping network {bcolors.Blink}{self.name}{bcolors.ENDC}')
        #wipe all the SSIDs
        while count < 15:
            if self.WRITE: self.db.wireless.updateNetworkWirelessSsid(self.net_id, count, name="Unconfigured SSID "+str(count+1), enabled=False, authMode="open", ipAssignmentMode="NAT mode", minBitrate="1", bandSelection="Dual band operation", perClientBandwidthLimitUp="0", perClientBandwidthLimitDown="0", perSsidBandwidthLimitUp="0", perSsidBandwidthLimitDown="0", mandatoryDhcpEnabled=False, visible=True, availableOnAllAps= True, availabilityTags=[], useVlanTagging=False)
            count += 1
        self.getSSIDS()
    
        #wipe all the RF profiles
        current = self.db.wireless.getNetworkWirelessRfProfiles(self.net_id)
        self.rfprofiles.clear()
        for rfp in current:
            if self.WRITE: self.db.wireless.deleteNetworkWirelessRfProfile(self.net_id, rfProfileId=rfp['id'])

        print(f'{bcolors.OKGREEN}{bcolors.Blink}Done.{bcolors.ResetBlink} Wiped all SSIDs and RF-profiles{bcolors.ENDC}')
        return

    #returns the RF Profile matching the name
    def getRFP(self, pName):
        for rfp in self.rfprofiles:
            if 'name' in rfp and pName == rfp['name']:
                return rfp
        return
    

    #Wipes current network settings before cloning
    def clone_force(self, mr_obj):
        self.wipeALL()
        self.clone(mr_obj)
        return

    #If both networks contain "switching" then copy those settings
    def clone_switch(self, mr_obj):
        print(f'\t{bcolors.OKBLUE}Switch Setting Cloning on Switch[{bcolors.WARNING}{self.name}{bcolors.OKBLUE}]')
        dst_net = self.db.networks.getNetwork(self.net_id)
        if not 'switch' in dst_net['productTypes']:
            print(f'\t\t{bcolors.FAIL}Target network does not contain switching{bcolors.ENDC}')
            return
        src_net = self.db.networks.getNetwork(mr_obj.net_id)
        if not 'switch' in src_net['productTypes']:
            print(f'\t\t{bcolors.FAIL}Source network does not contain switching{bcolors.ENDC}')
            return
       
        print(f'{bcolors.OKGREEN}Starting switch configuration/clone!{bcolors.ENDC}') 
        mtu = self.db.switch.getNetworkSwitchMtu(mr_obj.net_id)
        self.db.switch.updateNetworkSwitchMtu(self.net_id, **mtu)
        print(f'\t {bcolors.OKGREEN}-Cloning switch MTU settings...')
        sw_settings = self.db.switch.getNetworkSwitchSettings(mr_obj.net_id) 
        self.db.switch.updateNetworkSwitchSettings(self.net_id, **sw_settings)
        print(f'\t {bcolors.OKGREEN}-Cloning switch Default VLAN settings...')
        dscp2cos = self.db.switch.getNetworkSwitchDscpToCosMappings(mr_obj.net_id)
        self.db.switch.updateNetworkSwitchDscpToCosMappings(self.net_id, **dscp2cos)
        print(f'\t {bcolors.OKGREEN}-Cloning switch DSCP-2-COS mappings...')
        #stp = self.db.switch.getNetworkSwitchStp(mr_obj.net_id)
        #self.db.switch.updateNetworkSwitchStp(self.net_id,**stp)
        #print(f'\t {bcolors.OKGREEN}-Cloning switch Spanning Tree settings...')
        multiC = self.db.switch.getNetworkSwitchRoutingMulticast(mr_obj.net_id)
        self.db.switch.updateNetworkSwitchRoutingMulticast(self.net_id, **multiC)
        print(f'\t {bcolors.OKGREEN}-Cloning switch Multicast settings...')
        acls = self.db.switch.getNetworkSwitchAccessControlLists(mr_obj.net_id)
        acls['rules'].remove(acls['rules'][len(acls['rules'])-1]) #remove the default rule at the end
        self.db.switch.updateNetworkSwitchAccessControlLists(self.net_id, **acls)
        print(f'\t {bcolors.OKGREEN}-Cloning switch ACL rules...')
        try:
            storm = self.db.switch.getNetworkSwitchStormControl(mr_obj.net_id)
            self.db.switch.updateNetworkSwitchStormControl(self.net_id, **storm)
            print(f'\t {bcolors.OKGREEN}-Cloning storm control settings{bcolors.ENDC}')

        except:
            print(f'\t {bcolors.FAIL}-Failed to copy storm control settings{bcolors.ENDC}')


        rules_src = self.db.switch.getNetworkSwitchQosRules(mr_obj.net_id)
        rules_dst = self.db.switch.getNetworkSwitchQosRules(self.net_id)
        if not len(rules_src) == len(rules_dst): #I know, super simple comparison
            print(f'\t{bcolors.OKGREEN}-Cloning Switch QoS Rules...')
            #{'ruleIds': ['577586652210270187', '577586652210270188', '577586652210270189']}
            rOrder_src = self.db.switch.getNetworkSwitchQosRulesOrder(mr_obj.net_id)
            rOrder_dst = self.db.switch.getNetworkSwitchQosRulesOrder(self.net_id)
            for rid in rOrder_src['ruleIds']:
                #[{'id': '577586652210270187','vlan': None,'protocol': 'ANY','srcPort': None,'dstPort': None,'dscp': -1}, .. ]
                rule = self.db.switch.getNetworkSwitchQosRule(mr_obj.net_id,rid)
                try:
                    #pop the id, and srcPort/dstPort if they're empty, otherwise it'll throw an error
                    rule.pop('id')
                    if rule['srcPort'] == None: rule.pop('srcPort')
                    if rule['dstPort'] == None: rule.pop('dstPort') 
                    self.db.switch.createNetworkSwitchQosRule(self.net_id,**rule)
                    print(f'\t\t{bcolors.OKGREEN}-Rule Created[{bcolors.WARNING}{rule}{bcolors.OKGREEN}]')
                except:
                    print(f'\t\t{bcolors.OKGREEN}-Rule already exists{bcolors.ENDC}')
        return





    #Clones source <mr_obj> to current object/network
    def clone(self, mr_obj):
        ssid_mask = []
        #clone the SSIDs
        count = 0
        ssid_change = False
        while count < 15: #Process the SSIDs and look for changes
            if mr_obj.ssids[count]['name'][:17] == 'Unconfigured SSID':
                count += 1
                continue
            if not self.isSameSSID(self.ssids[count], mr_obj.ssids[count]):
                self.ssids[count] = copy.deepcopy(mr_obj.ssids[count])
                #print(f'Change in SSID[{count}]')
                ssid_change = True
                ssid_mask.append(count)
                if mr_obj.ssids[count]['authMode'] == 'ipsk-without-radius':
                    print("FOUND IPSK SSID")
                    self.master_IPSK[count] = self.db.wireless.getNetworkWirelessSsidIdentityPsks(mr_obj.net_id,count)
            
            count += 1
        # end while-count

        #print(f'Starting GP SYNC')
        self.updateGP(mr_obj) #kick off GP sync before SSID update, der
        
        if ssid_change: self.updateSSIDS()
   
 	#clone the RF Profiles
        rfp_change = False
        for sRFP in mr_obj.rfprofiles:
            found = self.findRFP(sRFP['name'], self.rfprofiles)
            if found == None:
                #no local object
                tmp = copy.deepcopy(sRFP)
                tmp.pop('networkId')
                tmp.pop('id')
                self.rfprofiles.append(tmp)
                rfp_change = True
            else:
                #found local object 
                if self.isSameRFP(found, sRFP):
                    continue
                else: #doesn't match
                    print("Different")
                    rfp_change = True
                    self.rfprofiles.remove(found)
                    tmp = copy.deepcopy(sRFP)
                    tmp.pop('networkId')
                    self.rfprofiles.append(tmp)
        
        if rfp_change: self.updateRF() 

        anyChange=False
        if ssid_change or rfp_change:
            anyChange=True
            print(f'\t{bcolors.OKBLUE}Changes SSID_CHANGE[{bcolors.WARNING}{ssid_change}{bcolors.OKBLUE}] RFP[{bcolors.WARNING}{rfp_change}{bcolors.OKBLUE}]')
            print(f'\t{bcolors.OKBLUE}Updating SSIDS in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            print(f'\t{bcolors.OKBLUE}Updating RF Profiles in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')


                ## Clone SplashSettings
        ## / end-SplashSettings

        if anyChange:
            ### Clone Wireless Settings
            print(f'\t{bcolors.OKBLUE}Updating Wireless Settings in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            wifiCFG = self.db.wireless.getNetworkWirelessSettings(mr_obj.net_id)
            if self.WRITE: self.db.wireless.updateNetworkWirelessSettings(self.net_id,**wifiCFG)
            ### /end-Wifi Settings
 
            ### Clone Traffic Analytics Settings
            print(f'\t{bcolors.OKBLUE}Updating Traffic Analytics Settings in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            taCFG = self.db.networks.getNetworkTrafficAnalysis(mr_obj.net_id)
            if self.WRITE: self.db.networks.updateNetworkTrafficAnalysis(self.net_id,**taCFG)
            ### /end-Traffic Analytics Settings

            ## Clone Bluetooth/IOT Settings
            print(f'\t{bcolors.OKBLUE}Updating Bluetooth/IOT Settingsin network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            btCFG = self.db.wireless.getNetworkWirelessBluetoothSettings(mr_obj.net_id)
            if self.WRITE: self.db.wireless.updateNetworkWirelessBluetoothSettings(self.net_id,**btCFG)
            ## / end-Bluetooth/IOT

            ## Clone Syslog Settings
            print(f'\t{bcolors.OKBLUE}Updating Syslog Settingsin network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            try:
                syslogCFG = self.db.networks.getNetworkSyslogServers(mr_obj.net_id)
                if self.WRITE: self.db.networks.updateNetworkSyslogServers(self.net_id,**syslogCFG)
            except:
                print(f'\t\t-{bcolors.FAIL}Failed to update syslog. Make sure all roles are compatible across clones{bcolors.ENDC}')
            ## / end-Syslog Settings

            ## Clone SNMP Settings
            print(f'\t{bcolors.OKBLUE}Updating SNMP Settingsin network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            snmpCFG = self.db.networks.getNetworkSnmp(mr_obj.net_id)
            if self.WRITE: self.db.networks.updateNetworkSnmp(self.net_id,**snmpCFG)
            ## / end-SNMP Settings


            ###Clone Alerts
            current_alerts = self.db.networks.getNetworkAlertsSettings(self.net_id)
            try:
                alerts = self.db.networks.getNetworkAlertsSettings(mr_obj.net_id)
            except:
                print(f'{bcolors.FAIL}Alert Failure: Alerts[{bcolors.WARNING}{current_alerts}{bcolors.FAIL}]')
            if not self.isSameAlerts(current_alerts, alerts):

                #clone the webhooks
                print(f'\t{bcolors.OKBLUE}Updating Web-Hooks in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')

                src_WH  = self.db.networks.getNetworkWebhooksHttpServers(mr_obj.net_id)
                curr_WH = self.db.networks.getNetworkWebhooksHttpServers(self.net_id)
                currentlist = []
                for cwh in curr_WH: #make list of current hooks
                    currentlist.append(cwh['name'])
                    #self.db.networks.deleteNetworkWebhooksHttpServer(self.net_id,cwh['id'])
                tmpName = "Unassigned" 
                for swh in src_WH: #create new webhooks
                    if swh['name'] in currentlist:
                        continue
                    try: 
                       wh = self.db.networks.getNetworkWebhooksHttpServer(mr_obj.net_id,swh['id'])
                       wh.pop('id')
                       wh.pop('networkId')
                       tmpName = wh['name']
                       if self.WRITE: self.db.networks.createNetworkWebhooksHttpServer(self.net_id, **wh)
                       print(f'\t\t{bcolors.OKBLUE}-Webhook {bcolors.WARNING}{tmpName}{bcolors.ENDC}')
                    except:
                       print(f'\t\t{bcolors.FAIL}-Webhook {bcolors.WARNING}{tmpName}{bcolors.FAIL} already exists{bcolors.ENDC}')
                ### /end-Webhooks

                ### Clone Alerts
                print(f'\t{bcolors.OKBLUE}Updating Alerts in network {bcolors.WARNING}{self.name}{bcolors.ENDC}')
                try:
                    if self.WRITE: self.db.networks.updateNetworkAlertsSettings(self.net_id, **alerts)
                except:
                    print(f'{bcolors.FAIL}Failure on alerts[{bcolors.WARNING}{alerts}{bcolors.FAIL}]')
                ### / end-Alerts
            ### /end-Alerts and Webhooks
            
                       


            ### Clone L3/L7/TS Rules
            count = 0
            print(f'\t{bcolors.OKBLUE}Updating L3/L7/TS Rules in {bcolors.WARNING}{self.name}{bcolors.ENDC}')
            while count < 15:
                if not count in ssid_mask:
                    count += 1
                    continue
                print(f'\t\t-{bcolors.OKBLUE}SSID {bcolors.WARNING}{count} {bcolors.OKBLUE}updated')
                l3rules = self.db.wireless.getNetworkWirelessSsidFirewallL3FirewallRules(mr_obj.net_id,count)
                lanAccess = True
                newL3 = {}
                newL3['rules'] = []
                #print(f'L3Rules: {l3rules}')
                for rule in l3rules['rules']:
                    if rule['destCidr'] == "Local LAN":
                        if rule['policy'] == "deny": lanAccess = False
                        else: lanAccess = True
                        
                        l3rules['rules'].remove(rule) #pull out the allow Lan Access rule, it's boolean
                    if rule['comment'] == "Default rule" or not rule['destCidr'] == "Local LAN":
                        newL3['rules'].append(rule) #pull out default rule, always the same
                
                #print(f'L3 Rules are {newL3}')
                newL3['allowLanAccess'] = lanAccess
                if self.WRITE: self.db.wireless.updateNetworkWirelessSsidFirewallL3FirewallRules(self.net_id,count, **newL3)
                l7rules = self.db.wireless.getNetworkWirelessSsidFirewallL7FirewallRules(mr_obj.net_id,count)
                if self.WRITE: self.db.wireless.updateNetworkWirelessSsidFirewallL7FirewallRules(self.net_id,count, **l7rules)
                try:
                    TSrules = self.db.wireless.getNetworkWirelessSsidTrafficShapingRules(mr_obj.net_id, count)
                    if self.WRITE: self.db.wireless.updateNetworkWirelessSsidTrafficShapingRules(self.net_id, count, **TSrules)
                except:
                    print(f'\t\t-{bcolors.FAIL}Failed to update TrafficShaping. Make sure all rules are complete{bcolors.ENDC}')


                count += 1
            ### /end-L3/L7/TS
            print()	
        ### /end-anyChange
        return anyChange

    #returns GP id of group-policy in GP-array
    def findGPname(self,GP_array,GPid):
        key = 'groupPolicyId'
        if len(GP_array) == 0: #short circuit empty targets
            return 
        if GPid < 1:
            print("NULL GPid")
            return 
        for gp in GP_array:
            if key in gp and int(gp[key]) == int(GPid): 
                return gp['name']
        return 


    #returns GP id of group-policy in GP-array
    def findGPid(self,GP_array,value):
        key = 'name'
        if len(GP_array) == 0: #short circuit empty targets
            return 0
        if value == None or len(value) == 0:
            print("NULL VALUE")
            return 0
        for gp in GP_array:
            if key in gp and gp[key] == str(value): 
                return int(gp['groupPolicyId'])
        
        print(f'{bcolors.FAIL}Cant find key[{bcolors.WARNING}{key}{bcolors.FAIL}] value[{bcolors.WARNING}{value}{bcolors.FAIL}]{bcolors.ENDC}')
        return -1


    #this will make sure all GP's in Golden network matches target
    def updateGP(self,mr_obj):
        #print(f'Updating GP now.....')
        oGP = self.db.networks.getNetworkGroupPolicies(mr_obj.net_id)
        tGP = self.db.networks.getNetworkGroupPolicies(self.net_id)

        self.master_GP = []
        self.local_GP = []
        for o in oGP:
            self.master_GP.append(copy.deepcopy(o))
            value = o['name']
            target_index = self.findGPid(tGP,value)
            if target_index < 1:
                o.pop('groupPolicyId')
                print(f'{bcolors.OKBLUE}Creating Group Policy[{bcolors.WARNING}{value}{bcolors.OKBLUE}] in Network[{bcolors.WARNING}{self.name}{bcolors.OKBLUE}]')
                self.db.networks.createNetworkGroupPolicy(self.net_id, **o)
                
        tGP = self.db.networks.getNetworkGroupPolicies(self.net_id)
        self.local_GP = copy.deepcopy(tGP)
        
        #for t in tGP:
        #    self.local_GP.append(copy.deepcopy(t))

        return

    #Pushes configuration from all stored SSID's to target
    def updateSSIDS(self):
        count = 0
        while count < 15:
            current = self.db.wireless.getNetworkWirelessSsid(self.net_id, count)
            if not self.isSameSSID(current, self.ssids[count]):
                self.updateSSID(count)
            count += 1
        self.getSSIDS()
        return
 
    #Pushes configuration from stored to target
    def updateSSID(self,ssid_num):
        ssid = self.ssids[ssid_num]
        data = {}
        name = ssid['name']
        print(f'{bcolors.OKBLUE}Updating Network[{bcolors.WARNING}{self.name}{bcolors.OKBLUE}] ID[{bcolors.WARNING}{self.net_id}{bcolors.OKBLUE}] Number[{bcolors.WARNING}{ssid_num}{bcolors.OKBLUE}] SSID[{bcolors.WARNING}{name}{bcolors.OKBLUE}]{bcolors.ENDC}')

        if 'encryptionMode' in ssid and ssid['encryptionMode'] == 'wpa-eap':
            ssid['encryptionMode'] = 'wpa'

        #If the SSID has a single radius server, it'll error if these are set to "None" so pop them
        if 'radiusFailoverPolicy' in ssid and ssid['radiusFailoverPolicy'] == None:
            ssid.pop('radiusFailoverPolicy')
            #ssid['radiusFailoverPolicy'] = 'Allow access'
        if 'radiusLoadBalancingPolicy' in ssid and ssid['radiusLoadBalancingPolicy'] == None:
            ssid.pop('radiusLoadBalancingPolicy')
            #ssid['radiusLoadBalancingPolicy'] = 'Strict priority order'
            
            
        config = configparser.ConfigParser()
        config.sections()
        config.read('autoSYNC.cfg')
        secret = config['RAD_KEYS']['_ALL_'].replace('"','').replace(' ','')
        if ssid['name'] in config['RAD_KEYS']:
            secret = config['RAD_KEYS'][ssid['name']].replace('"','').replace(' ','')

        if 'radiusServers' in ssid:
            #print(f'{bcolors.OKGREEN}Using Secret [{bcolors.WARNING}{secret}{bcolors.OKGREEN}]')
            for rs in ssid['radiusServers']:
                rs['secret'] = secret
        if 'radiusAccountingServers' in ssid:
            for ras in ssid['radiusAccountingServers']:
               ras['secret'] = secret

        #print(ssid)

        if self.WRITE: 
            self.db.wireless.updateNetworkWirelessSsid(self.net_id, **ssid)
        
            #deal with iPSK to GP mappings
            if ssid['authMode'] == "ipsk-without-radius":
                #self.update
                ipsks = self.master_IPSK[ssid_num] #pull the previously stored from Golden/Master
                #print(f'iPSKs for SSID[{ssid_num}] iPSK[{ipsks}]')
                local_ipsks = self.db.wireless.getNetworkWirelessSsidIdentityPsks(self.net_id,ssid_num)
 
                #Lazy man's way instead of searching
#                for li in local_ipsks:
#                    self.db.wireless.deleteNetworkWirelessSsidIdentityPsk(target_netid,ssid_num,li['id'])
#                    print(f'Deleting iPSK.....')
                
                for i in ipsks:
                    #print(f'IPSK[{i}]')
                    source_name = self.findGPname(self.master_GP, i['groupPolicyId'])
                    source_id = i['groupPolicyId']
                    target_id = self.findGPid(self.local_GP, source_name)
                    i['groupPolicyId'] = target_id #this is where we assign the new GP_id to the golden iPSK entry to match
                    local_ipskID = 0
                    local_ipskDIFF = False
                    for li in local_ipsks:
                        #print(li)
                        if li['name'] == i['name']: 
                            local_ipskID = li['id']
                            if not li['passphrase'] == i['passphrase']: local_ipskDIFF = True #this is easy

                            local_ipsk_target_name = self.findGPname(self.local_GP, li['groupPolicyId'])
                            #check to see if the target(local) group-policy name matches golden
                            if not source_name == local_ipsk_target_name:#if the source name doesn't match local
                                local_ipskDIFF = True

                    #print(self.master_GP)
                    #print(self.local_GP)
                    i.pop('id') #need to pop it otherwise can't write/update
                    if target_id < 1 or local_ipskID == 0: #doesn't exist
                        print(f'{bcolors.OKBLUE}Created iPSK Entry [{bcolors.WARNING}{i["name"]}{bcolors.OKBLUE}]')
                        self.db.wireless.createNetworkWirelessSsidIdentityPsk(self.net_id,ssid_num, **i)
                    else: #it already exists, update!
                        if local_ipskDIFF:
                            print(f'{bcolors.OKBLUE}Updating iPSK Entry [{bcolors.WARNING}{i["name"]}{bcolors.OKBLUE}]')
                            self.db.wireless.updateNetworkWirelessSsidIdentityPsk(self.net_id,ssid_num, local_ipskID, **i)

        return
    ### end-of updateSSID()


    #Returns SSID info for a single stored SSID
    def showSSID(self,ssid_num):
        return self.ssids[ssid_num]

    #Returns SSID info for all stored SSIDs
    def showSSIDS(self):
        return self.ssids


### END-OF class MR_network


class MS_switch:
    name = ""
    vlans = []  # list of vlans
    macs = []  # list of macs in 00:ab:cd:ed:cb:a0  format
    macTable = []  # array of dictionary objects
    unique = 0

    parse = None  # this is the raw CiscoConfParse object
    length = 0

    def __init__(self):
        self.name = ""
        self.macs = []
        self.macTable = []
        self.unique = 0
        self.parse = None
        self.length = 0

### END-OF class MS_switch
