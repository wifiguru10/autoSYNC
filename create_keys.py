import os
import json
import base64

PATH = '~/.meraki'
config = {}
api_key = input("Please enter your API key: ").strip()
config['api_key'] = base64.b64encode(bytearray(api_key, 'utf-8')).decode('utf-8')

titan_key = input("Please enter your Titan AD credentials in format \"homeoffice\\<username>:<password>\": ").strip()
config['titan_key'] = base64.b64encode(bytearray(titan_key, 'utf-8')).decode('utf-8')

# tk_bytes = titan_key.encode("ascii")
# base64_bytes = base64.b64encode(tk_bytes)
# config['titan_key'] = base64_bytes.decode("ascii")

file_path = os.path.expanduser(PATH)
with open(file_path, 'w') as meraki_file:
    meraki_file.write(json.dumps(config))

os.chmod(file_path, 0o600)
print('API Key saved in ' + file_path + ' successfully!')
print('Titan credentials saved in ' + file_path + ' successfully!')




