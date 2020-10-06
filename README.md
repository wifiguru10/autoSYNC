## autoSYNC
Synchronizes meraki network settings from a parent network (golden config) to child networks for a more flexible template alternative

1. Edit the 'autoSYNC.cfg.default' file and save it to 'autoSYNC.cfg'
2. tag all your MR networks with TARGET tag (default is 'autoSYNC')
3. tag ONE network, your MASTER network with MASTER tag AND TARGET tag (default master tag is 'golden')
4. You can only have one MASTER in each network
4. run the autoSYNC.py script. it'll do the rest

## notes
1. Run create_keys.py to import your API key


This is beta, lots of stuff broken. May release the blue smoke from your equipment, don't use in production!

## what will sync today? **Updated[Oct 6 '20]**
# General
* **Gold** Master network changes replicate to children networks
* Changes in children networks revert to match Master network (only pushes changes, not whole profile)
* Syslog Servers
* SNMP Settings
* Network Alerts
* Webhooks

# Wireless
* SSID Syncronization
* RF-Profiles
* Wireless Network Settings
* Traffic Analysis
* Bluetooth Settings
* Per-SSID L3 Firewall Rules
* Per-SSID L7 Firewall Rules

# Switching
* MTU settings
* Switch Network Settings
* DSCP-2-COS Mappings
* Spanning-Tree settings
* Multicast Settings
* Switch ACL rules
* Network Storm Control
* Switch QoS Rules

## what's next?
# General
* Group-Policies

# Wireless
* iPSK w/o radius keys

# Switching
* auto-STP mapping based on switch type (ex. MS425 priority of 4096 vs MS210 with priority of 32768)
* auto-Aggregation
* autoMAC integration (port provisioning and 
