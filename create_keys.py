#!/usr/bin/python

import os
import json
import base64

PATH = '~/.meraki'
config = {}
api_key = input("Please enter your API key: ").strip()
config['api_key'] = base64.b64encode(bytearray(api_key, 'utf-8')).decode('utf-8')

file_path = os.path.expanduser(PATH)
with open(file_path, 'w') as meraki_file:
    meraki_file.write(json.dumps(config))

os.chmod(file_path, 0o600)
print('API Key saved in ' + file_path + ' successfully!')




