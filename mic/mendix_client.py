import requests
from os import path

class MendixClient:
    local_cache = None
    base_url = ""

    def __init__(self, base_url: str, proxy: str = None, verify: bool = True):
        self.base_url = base_url
        session = requests.Session()
        if proxy is not None:
            session.proxies = {"http": proxy, "https": proxy}
        if verify is not None:
            session.verify = verify
            # Disable TLS warnings if verification is disabled
            requests.urllib3.disable_warnings(
                requests.urllib3.exceptions.InsecureRequestWarning
            )
        cookies = {"__Host-DeviceType": "Desktop", "__Host-Profile": "Responsive"}
        session.cookies.update(cookies)
        self.session = session
        self.login()  # Login anonymously

    # Login as a local or anonymous user
    def login(self, username=None, password=None):
        # Clear previous login info
        self.session.headers.update({"X-Csrf-Token": None})
        self.session.cookies.update({"__Host-XASSESSIONID": None})
        url = f"{self.base_url}/xas/"
        if not username is None:
            # Login
            data = {
                "action": "login",
                "params": {"username": username, "password": password},
            }
            r = self.session.post(url, json=data)
            if not r.status_code == 200:
                raise RuntimeError("Could not login")
            self.session.headers.update({"X-Csrf-Token": r.json().get("csrftoken")})

        # Fill the Mendix local cache and get CSRF-token
        data = {"action": "get_session_data", "params": {}}
        r = self.session.post(url, json=data)
        if not r.status_code == 200:
            raise RuntimeError("Could not acquire CSRF")
        self.session.headers.update({"X-Csrf-Token": r.json().get("csrftoken")})
        self.current_user = r.json()["user"]["attributes"]["Name"]["value"]
        self.local_cache = r.json()

    # Request objects of a certain klass/type
    def get_objects_by_klass(self, klass, limit=10, sort=None, offset=None):
        url = f"{self.base_url}/xas/"
        data = {
            "action": "retrieve_by_xpath",
            "params": {"xpath": f"//{klass}", "schema": {"amount": limit}},
        }
        if offset:
            data['params']['schema']['offset'] = offset
        if sort:
            data['params']['schema']['sort'] = sort
        r = self.session.post(url, json=data)
        return r.json().get("objects", {})

    # Request object by its guid/id
    def get_object_by_id(self, guid):
        url = f"{self.base_url}/xas/"
        data = {"action": "retrieve_by_ids", "params": {"ids": [guid], "schema": {}}}
        r = self.session.post(url, json=data)
        return r.json().get("objects", {})

    # Get all the available klasses/types from the metadata of the flow.
    def get_klasses(self):
        klasses = [i.get("objectType") for i in self.local_cache.get("metadata", [])]
        return klasses

    def update_object_attribute(self, guid, name, value):
        url = f"{self.base_url}/xas/"
        data = {
            "action": "commit",
            "params": {"guids": [guid]},
            "changes": {guid: {name: {"value": value}}},
        }
        r = self.session.post(url, json=data)
        return r.json().get("objects", {})

    def download_file(self, guid, name, directory):
        destination_path = path.join(directory, f"{guid}_{name}")
        if path.exists(destination_path):
            return True
        url = f'{self.base_url}/file'
        params = {
            'guid': guid
        }
        result = self.session.get(url, params=params)
        if not result.status_code == 200:
            return False
        else: 
            with open(destination_path, 'wb') as f:
                f.write(result.content)
            return True
