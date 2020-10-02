# autoSYNC
Synchronizes meraki network settings from a parent network (golden config) to child networks for a more flexible template alternative

1. Edit the "autoSYNC.cfg.default" file and save it to "autoSYNC.cfg"
2. tag all your MR networks with TARGET tag
3. tag ONE network, your MASTER network with MASTER tag AND TARGET tag
4. run the autoSYNC.py script. it'll do the rest

# notes
1. Run create_keys.py to import your API key


This is beta, lots of stuff broken. May release the blue smoke from your equipment, don't use in production!
