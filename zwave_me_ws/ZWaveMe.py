import json
import threading

from .WebsocketListener import WebsocketListener
import time


class ZWaveMe:
    """Main controller class"""

    def __init__(self, on_device_create, on_device_update, on_new_device,
                 url, token, platforms=None):
        self.on_device_create = on_device_create
        self.on_device_update = on_device_update
        self.on_new_device = on_new_device
        self.url = url
        self.token = token
        self.platforms = platforms
        self._ws = None
        self._wshost = None
        self.start_ws()
        self.thread = None
        self.devices = []

    def start_ws(self):
        """get/find the websocket host"""
        self.thread = threading.Thread(target=self.init_websocket)
        self.thread.daemon = True
        self.thread.start()

    def send_command(self, device_id, command):
        self._ws.send(
            json.dumps(
                {
                    "event": "httpEncapsulatedRequest",
                    "data": {
                        "method": "GET",
                        "url": "/ZAutomation/api/v1/devices/{}/command/{}".format(
                            device_id, command
                        )
                    }
                }
            )
        )

    def get_device_info(self, device_id):
        self._ws.send(
            json.dumps(
                {
                    "event": "httpEncapsulatedRequest",
                    "data": {
                        "method": "GET",
                        "url": "/ZAutomation/api/v1/devices/{}".format(
                            device_id
                        )
                    }
                }
            )
        )

    def init_websocket(self):
        # keep websocket open indefinitely
        while True:
            self._ws = WebsocketListener(
                ZWaveMe=self,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                token=self.token,
                url=self.url,
            )

            try:
                self._ws.run_forever(ping_interval=5)
            finally:
                self._ws.close()
            time.sleep(5)

    def on_message(self, _, utf):
        if utf:
            dict_data = json.loads(utf)
            if "type" not in dict_data.keys():
                return
            try:
                if dict_data["type"] == "ws-reply":
                    body = json.loads(dict_data["data"]["body"])
                    if "devices" in body["data"]:
                        self.devices = [
                            device
                            for device in body["data"]["devices"]
                            if device["deviceType"] in self.platforms
                        ]
                        self.on_device_create(self.devices)
                    elif "id" in body['data']:
                        self.on_new_device(body['data'])
                elif dict_data["type"] == "me.z-wave.devices.level":
                    self.on_device_update(dict_data["data"])
                elif dict_data["type"] == "me.z-wave.namespaces.update":
                    for data in dict_data['data']:
                        if data['id'] == 'devices_all':
                            new_devices = [x['deviceId'] for x in data['params']]
                            devices_to_install = set(new_devices)-set([x['id'] for x in self.devices])
                            for device in devices_to_install:
                                self.get_device_info(device)
            except Exception as e:
                pass

    def on_error(self, *args, **kwargs):
        error = args[-1]

    def on_close(self, _, *args):
        self._ws.connected = False


    def get_ws(self):
        return self._ws

    def get_wshost(self):
        return self._wshost
