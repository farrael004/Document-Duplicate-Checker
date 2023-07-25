from deduplication import secret
from requests_ntlm import HttpNtlmAuth
import requests
import json

def get_digest_token():
    """
    This function retrieves a token for accessing a SharePoint site. \
    It sends a POST request to the specified URL with the necessary \
    authentication information. If the request is successful, it \
    extracts the token from the response and returns it.

    Returns:
    --------
    - token: str
        A string representing the token for accessing the SharePoint site.

    Raises:
    -------
    - Exception
        If the POST request fails or returns a non-200 status code, an \
        exception is raised and an error message is displayed.
    """
    url = f"https://collab.agr.gc.ca/co/{secret.project}/_api/contextinfo"

    while True:
        USERNAME = f"AAFC-AAC\\{input('Username: ')}"
        PASSWORD = input("Password: ")
        headers = {
            "Accept": "application/json; odata=verbose",
            "Content-Type": "application/json;odata=verbose"
        }

        response = requests.post(url, headers=headers, auth=HttpNtlmAuth(USERNAME, PASSWORD))

        if response.status_code == 200:
            content = json.loads(response._content)
            token = content['d']['GetContextWebInformation']['FormDigestValue']
            content_type = content['d']['GetContextWebInformation']['SupportedSchemaVersions']['__metadata']['type']

            return token, USERNAME, PASSWORD
        else:
            print("Incorrect credentials.")

url = f"https://collab.agr.gc.ca/co/{secret.project}/_api/lists(guid'{secret.guid}')/items"

token, USERNAME, PASSWORD = get_digest_token()

headers = {
    "Accept": "application/json; odata=verbose",
    "Content-Type": "application/json;odata=verbose",
    "X-RequestDigest": token
}

response = requests.get(url, headers=headers, auth=HttpNtlmAuth(USERNAME, PASSWORD))

if response.status_code == 200 or response.status_code == 201:
    print(response.content)
else:
    print(response.content)