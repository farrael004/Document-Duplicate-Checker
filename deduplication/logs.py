import streamlit as st
import requests
import json
import pandas as pd
from time import perf_counter
from datetime import datetime
from requests_ntlm import HttpNtlmAuth
import secret
import os

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
    url = f"https://{secret.site}{secret.project}/_api/contextinfo"
    USERNAME = f"{secret.username_prefix}{st.session_state['username']}"
    PASSWORD = st.session_state['password']
    headers = {
        "Accept": "application/json; odata=verbose",
        "Content-Type": "application/json;odata=verbose"
    }

    response = requests.post(url, headers=headers, auth=HttpNtlmAuth(USERNAME, PASSWORD))

    if response.status_code == 200:
        content = json.loads(response._content)
        token = content['d']['GetContextWebInformation']['FormDigestValue']
        content_type = content['d']['GetContextWebInformation']['SupportedSchemaVersions']['__metadata']['type']

        return token
    else:
        sharepoint_error_message(response._content)
        st.stop()

def sharepoint_error_message(error_message):
    st.error("There was an error connecting to SharePoint in order to perform telemetry logging.")
    if error_message != b'':
        st.error(error_message)

def add_log(form_args: dict, algo_option: str, start_time: float, documents: pd.DataFrame):
    """
    This function is responsible for logging data related to clustering \
    operations. It updates session state variables with information such \
    as the clustering type, number of documents clustered, sensitivity, \
    number of features, alpha value, cutoff value, duration of the process, \
    and the root directory. 

    Parameters:
    -----------
    - form_args: dict
        A dictionary containing form arguments.
    - algo_option: str
        An option representing the chosen clustering type.
    - start_time: float
        The start time of the clustering process.
    - documents: pd.DataFrame
        A dataframe of documents that were clustered.
    """
    if not st.session_state['log_metrics']:
        return
    
    st.session_state['log_data']['clustering_type'] = algo_option

    if algo_option == 'Similarity clustering':
        st.session_state['log_data']['documents_clustered'] = len(documents)
        st.session_state['log_data']['sensitivity'] = form_args['sensitivity']
        st.session_state['log_data']['n_features'] = 'N/A'
        st.session_state['log_data']['alpha'] = 'N/A'
        st.session_state['log_data']['cut_off'] = 'N/A'
        st.session_state['log_data']['timer'][2] = perf_counter() - start_time

    if algo_option == 'Topic clustering':
        st.session_state['log_data']['documents_clustered'] = len(documents)
        st.session_state['log_data']['n_features'] = form_args['n_features']
        st.session_state['log_data']['alpha'] = form_args['alpha']
        st.session_state['log_data']['cut_off'] = form_args['cut_off']
        st.session_state['log_data']['sensitivity'] = 'N/A'
        st.session_state['log_data']['timer'][2] = perf_counter() - start_time

    fields = [
        'duplicates_found',
        'files_analysed',
        'clustering_type',
        'documents_clustered',
        'sensitivity',
        'n_features',
        'alpha',
        'cut_off',
        'duration',
        'root_directory'
    ]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = {
        "__metadata": {
            "type": f"SP.Data.{secret.type}"
        },
        "Title": timestamp,
        "files_found": st.session_state['log_data']['files_found']
    }
    for field in fields:
        if field == 'duration':
            body[field] = float(f"{sum(st.session_state['log_data']['timer']):.2f}")
            continue
        if st.session_state['log_data'][field] == 'N/A':
            continue
        body[field] = st.session_state['log_data'][field]

    url = f"https://{secret.site}{secret.project}/_api/lists(guid'{secret.guid}')/items"

    headers = {
        "Accept": "application/json; odata=verbose",
        "Content-Type": "application/json;odata=verbose",
        "X-RequestDigest": get_digest_token()
    }

    USERNAME = f"{secret.username_prefix}{st.session_state['username']}"
    PASSWORD = st.session_state['password']

    try:
        response = requests.post(url, json=body, headers=headers, auth=HttpNtlmAuth(USERNAME, PASSWORD))
    except Exception as e:
        sharepoint_error_message(e)

    if response.status_code == 200 or response.status_code == 201:
        pass
    else:
        sharepoint_error_message(response._content)


def login():
    """
    This function handles the login process for the user.
    """
    if 'log_metrics' not in st.session_state:
        st.session_state['log_metrics'] = None

    if st.session_state['log_metrics'] is None:
        if os.path.exists('log_metrics.txt'):
            with open('log_metrics.txt', 'r') as f:
                st.session_state['log_metrics'] = True if f.read() == "True" else False
        else:
            st.write("Log usage telemetry?")
            col1, col2, col3 = st.columns((1,1,6))
            button_yes = col1.button("Yes", use_container_width=True)
            button_no = col2.button('No', use_container_width=True)
            remember_checkbox = st.checkbox("Remember selection", help="If marked, this dialog option will not appear again. The choice you make now will be remembered next time you open this application.")
            
            if button_yes:
                st.session_state['log_metrics'] = True
                if remember_checkbox:
                    with open('log_metrics.txt', 'w') as f:
                        f.write("True")
            if button_no:
                st.session_state['log_metrics'] = False
                if remember_checkbox:
                    with open('log_metrics.txt', 'w') as f:
                        f.write("False")

            

            if button_yes or button_no:
                st.experimental_rerun()
            st.stop()
    
    if not st.session_state['log_metrics']:
        return

    if 'password_works' not in st.session_state:
        st.session_state['password_works'] = False
        st.session_state['username'] = '' 
        st.session_state['password'] = ''

    if not st.session_state['password_works']:
        st.session_state['username'] = st.text_input('Username', help="Windows username")
        st.session_state['password'] = st.text_input('Password', type='password')
        if st.button('Submit'):
            try:
                get_digest_token()
                st.session_state['password_works'] = True
            except Exception as e:
                st.error("Something went wrong when trying to login")
        if st.session_state['password_works']:
            st.experimental_rerun()
            
        st.stop()