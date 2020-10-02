# autoSYNC
Synchronizes meraki network settings from a parent network (golden config) to child networks for a more flexible template alternative


1. tag all your MR networks with "autoSYNC"
2. tag ONE network, your 'golden' network with "as:master" AND "autoSYNC"
3. export your API key to CLI
4. run the autoSYNC.py script. it'll do the rest


This is beta, lots of stuff broken. May release the blue smoke from your equipment, don't use in production!
