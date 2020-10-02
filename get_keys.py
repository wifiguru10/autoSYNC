import os
import json
import base64

def get_api_key(path='~/.meraki'):
    file_path = os.path.expanduser(path)
    if not os.path.exists(file_path):
        print("Config file doesn't exist: " + file_path)
        api_key = input('Please enter your API key to continue: ').strip()
        return api_key
    stats = os.stat(file_path)
    mod = oct(stats.st_mode)[-2:]
    if mod != '00':
        print('WARNING: PERMISSIONS ON YOUR API KEY ARE INCORRECT')
        print('RUN THE FOLLOWING COMMAND TO FIX: ')
        print('chmod 600 ' + file_path)
        input('OR PRESS ENTER TO FIX AUTOMATICALLY')
        os.chmod(file_path, 0o600)
    with open(file_path, 'r') as meraki_file:
        config = json.loads(meraki_file.read())
    if config['api_key']:
        return base64.b64decode(bytearray(config['api_key'], 'utf-8')).decode('utf-8')
    else:
        print("Your API Key doesn't exist in your config file: " + file_path)
        api_key = input('Please enter your API key to continue: ').strip()
        return api_key


def get_titan_key(path='~/.meraki'):
    file_path = os.path.expanduser(path)
    if not os.path.exists(file_path):
        print("Config file doesn't exist: " + file_path)
        titan_key = input('Please enter your Titan AD credentials in format \"homeoffice\\<username>:<password>\": ').strip()
        return base64.b64encode(bytearray(titan_key, 'utf-8')).decode('utf-8')
    stats = os.stat(file_path)
    mod = oct(stats.st_mode)[-2:]
    if mod != '00':
        print('WARNING: PERMISSIONS ON YOUR API KEY ARE INCORRECT')
        print('RUN THE FOLLOWING COMMAND TO FIX: ')
        print('chmod 600 ' + file_path)
        input('OR PRESS ENTER TO FIX AUTOMATICALLY')
        os.chmod(file_path, 0o600)
    with open(file_path, 'r') as meraki_file:
        config = json.loads(meraki_file.read())
    if config['titan_key']:
        return config['titan_key']
    else:
        print("Your API Key doesn't exist in your config file: " + file_path)
        titan_key = input('Please enter your API key to continue: ').strip()
        return base64.b64encode(bytearray(titan_key, 'utf-8')).decode('utf-8')