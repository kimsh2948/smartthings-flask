from flask import Flask, jsonify, abort, request, session
from flask_cors import CORS
from context import setup_logger
import requests
import pprint
import base64
import json

app = Flask(__name__)
app.secret_key = 'define_secret_key'
logger = setup_logger()
CORS(app)

smartthings_api_url = 'https://api.smartthings.com'

client_id = '7269e2f5-eb71-45b9-90ea-1d89041cc3bd'
client_secret = '5e2f70c0-3120-48ef-8958-b3ef31878e6f'

redirect_uri = 'https://port-0-smartthings-webhook-2rrqq2blmqxv7cr.sel5.cloudtype.app/oauth/callback'
auth_header = f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"

# 토큰 값을 저장하고 읽어오는 함수
def save_token(token, key):
    data = { key: token }
    with open('tokens.json', 'w') as file:
        json.dump(data, file)

def load_token(key):
    try:
        with open('tokens.json', 'r') as file:
            data = json.load(file)
            return data.get(key, None)
    except FileNotFoundError:
        return {}
    
def get_access_token():
    try:
        access_token = session.get('access_token')
        print(access_token)
        if not access_token:
            refresh_access_token()
            access_token = session.get('access_token')
        return access_token
    except Exception as e:
        logger.error(f'Error: {e}')

def refresh_access_token():
    try:
        refresh_token = load_token('refresh_token')

        token_params = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id
        }

        response = requests.post(f'{smartthings_api_url}/oauth/token', data=token_params,
                                    headers={
                                        'Authorization': auth_header,
                                        'Content-Type': 'application/x-www-form-urlencoded'}, verify=False)
        token_response = response.json()
        pprint.pprint(token_response)

        session['access_token'] = token_response['access_token']
        refresh_token = token_response['refresh_token']
        save_token(refresh_token, 'refresh_token')
    except Exception as e:
        logger.error(f'Error: {e}')

@app.route('/')
def hello_world():
    print(session)
    session.clear()
    return 'Hello World!'

@app.route('/oauth/code', methods=['GET'])
def oauth_accesstoken():
    try:
        code = request.args.get('code')
        pprint.pprint(code)

        token_params = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code': code
        }

        response = requests.post(f'{smartthings_api_url}/oauth/token', data=token_params,
                                headers={
                                    'Authorization': auth_header,
                                    'Content-Type': 'application/x-www-form-urlencoded'}, verify=False)
        token_response = response.json()
        pprint.pprint(token_response)

        session['access_token'] = token_response['access_token']
        refresh_token = token_response['refresh_token']
        save_token(refresh_token, 'refresh_token')
        print(session)

        return jsonify('Success responsed access token'), 200
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify('error : ' + e), 500

@app.route('/devices', methods=['GET'])
def device_list():
    try:
        access_token = get_access_token()

        response = requests.get(f'{smartthings_api_url}/devices', 
                                headers={'Authorization': f"Bearer {access_token}"}, verify=False)
        devices = response.json()['items']
        return jsonify(devices), 200
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify('error : ' + e), 500

@app.route('/device/status', methods=['GET'])
def device_status():
    try:
        access_token = get_access_token()

        device_id = request.args.get('device_id')
        response = requests.get(f'{smartthings_api_url}/devices/{device_id}/status', 
                                headers={'Authorization': f"Bearer {access_token}"}, verify=False)
        device_status = response.json()
        pprint.pprint(device_status)
        return jsonify(device_status), 200
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify('error : ' + e), 500

@app.route('/device/command-info', methods=['GET'])
def device_command_info():
    try:
        access_token = get_access_token()

        device_id = request.args.get('device_id')
        response = requests.get(f'{smartthings_api_url}/devices/{device_id}', 
                                headers={'Authorization': f"Bearer {access_token}"}, verify=False)
        device_info = response.json()
        pprint.pprint(device_info)

        capabilities = device_info['components'][0]['capabilities']

        commands = []
        for cap in capabilities:
            response = requests.get(f"{smartthings_api_url}/capabilities/{cap['id']}/{cap['version']}", 
                                    headers={'Authorization': f"Bearer {access_token}"}, verify=False)
            
            command_info = response.json()
            command = {
                'command_id': command_info['id'],
                'command': command_info['commands']
            }
            commands.append(command)

        return jsonify(commands), 200
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify('error : ' + e), 500
    
@app.route('/device/control', methods=['POST'])
def device_control():
    try:
        access_token = get_access_token()

        params = request.get_json()
        pprint.pprint(params)

        device_id = params['device_id']
        device_cap_id = params['device_cap_id']
        command = params['command']
        arguments = params['arguments']

        command_data = {
            'commands': [
                {
                    'component': 'main',
                    'capability': device_cap_id,
                    'command': command,
                    'arguments': arguments
                }
            ]
        }
        pprint.pprint(command_data)

        response = requests.post(f'{smartthings_api_url}/devices/{device_id}/commands', json=command_data,
                                headers={'Authorization': f"Bearer {access_token}"}, verify=False)
        device_status = response.json()
        return jsonify(device_status), 200
    except Exception as e:
        logger.error(f'Error: {e}')
        return jsonify('error : ' + e), 500

if __name__ == '__main__':
    app.run(debug=True, port=9999, host='0.0.0.0')