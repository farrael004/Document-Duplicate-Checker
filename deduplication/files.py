import streamlit as st
import extract_msg
import docx2txt
from pptxer.presentations_text_extractor import __extract_presentation_texts_from_path__ as extract_pptx_text
import PyPDF2
import pandas as pd
from time import perf_counter
import os
import hashlib
import zipfile
import shutil
import platform
import subprocess


@st.cache_resource
def get_data(files: list[str], directory: str, text_extensions: list[str]):
    """
    This function takes in a list of file names, a directory path, and a list of \
    file extensions as inputs. It reads the files in the directory with the specified \
    extensions, extracts data from them using the 'get_data_from_text_file' function, \
    and returns a pandas DataFrame with the extracted data.

    Parameters:
    -----------
    - files: list[str]
        A list of file names to be processed.
    - directory: str
        The path to the directory where the files are located.
    - text_extensions: list[str]
        A list of file extensions that are supported for text extraction.

    Returns:
    --------
    - text_data: pandas DataFrame
        A DataFrame containing the extracted filename, text, and hash from the specified files and extensions, with all duplicate entries removed.
    - image_data: pandas DataFrame
        A DataFrame containing the extracted filename, and hash from image files, with all duplicate entries removed.
    - generic_data: pandas DataFrame
        A DataFrame containing the extracted filename, and hash from the remaining files, with all duplicate entries removed.
    """
    text_data = []
    image_data = []
    generic_data = []
    progress_bar = st.empty()
    start_time = perf_counter()
    for i, file in enumerate(files):
        if is_temp_file(file): continue

        progress_bar.progress((i+1)/len(files), f'Loading {file.replace(directory, "")}')
        ext = file.split('.')[-1].lower()
        if is_text_document(ext, text_extensions):
            text_data.append(get_data_from_text_file(file, ext))
        elif is_image_document(ext):
            image_data.append(get_data_from_generic_file(file))
        else:
            generic_data.append(get_data_from_generic_file(file))

    
    text_data = pd.DataFrame.from_records(text_data)
    image_data = pd.DataFrame.from_records(image_data)
    generic_data = pd.DataFrame.from_records(generic_data)

    progress_bar.empty()

    files_analyzed = len(text_data.index) + len(image_data.index) + len(generic_data.index)

    return text_data, image_data, generic_data, files_analyzed, perf_counter() - start_time

def is_temp_file(file):
    filename = str(os.path.basename(file))
    return filename.startswith('~$')

def is_text_document(ext, text_extensions):
    return ext in text_extensions

def is_image_document(ext):
    return ext in ['bmp', 'png', 'jpg', 'jpeg', 'gif', 'tiff']


@st.cache_data
def get_data_from_generic_file(file):
    """
    This function takes in a file path as input. It reads the file \
    and extracts the MD5 hash from the file's contents and returns \
    a dictionary containing the file name and hash.

    Parameters:
    -----------
    - file: str
        The name of the file to be processed.

    Returns:
    --------
    - data: dict
        A dictionary containing the file name and MD5 hash of the file's contents.
    """
    with open(file, 'rb') as f:  # Open the file in binary mode
        contents = f.read()  # Read the contents as bytes
    hash = hashlib.md5(contents).hexdigest()  # Calculate the hash of the file's contents
    return {'filename': file, 'hash': hash}


@st.cache_data
def get_data_from_text_file(file: str, ext: str):
    """
    This function takes in a file path and its extension as inputs. \
    It reads the file and extracts the text data from it using the \
    'get_text_from_file' function. It also calculates the MD5 hash of \
    the file's contents and returns a dictionary containing the file \
    name, text data, and hash.

    Parameters:
    -----------
    - file: str
        The name of the file to be processed.
    - ext: str
        The extension of the file to be processed.

    Returns:
    --------
    - data: dict
        A dictionary containing the file name, text data, and MD5 hash of the file's contents.
    """

    text = get_text_from_file(file, ext)
    try:
        with open(file, 'rb') as f:  # Open the file in binary mode
            contents = f.read()  # Read the contents as bytes
    except PermissionError:
        st.error(f'Permission error. The file `{file}` cannot be opened. If this file is already open, close all applications that are interacting with it.')
        st.stop()
    hash = hashlib.md5(contents).hexdigest()  # Calculate the hash of the file's contents
    return {'filename': file, 'text': text, 'hash': hash}


def remove_duplicates(files: list[str], directory: str):
    """
    This function takes in a list of file names and a directory path as inputs. \
    It identifies any duplicate files based on their hash values, and returns a \
    new list of files with the duplicates removed. 

    Parameters:
    -----------
    - files: list[str]
        A list of file names to be processed.
    - directory: str
        The path to the directory where the files are located.

    Returns:
    --------
    - files: list[str]
        A new list of files with duplicate files removed.
        
    Side Effects:
    -------------
    - This function displays the list of duplicate files and their respective paths \
    in an expandable section using Streamlit.
    """
    duplicates = files[files.duplicated(subset='hash', keep=False)]
    all_duplicates = []


    if duplicates.empty: return files, all_duplicates

    all_duplicates = []
    for i, hash_value in enumerate(duplicates['hash'].unique()):

        with st.expander(f"Duplicates {i+1}", expanded=True):
            duplicate_filenames = [
                filename.replace(directory, '')
                for filename in duplicates[duplicates['hash'] == hash_value]['filename']
            ]
            all_duplicates += duplicate_filenames
            for filename in duplicate_filenames:
                path = filename.replace(directory, '')
                st.write(path)
                col1, col2, col3, col4 = st.columns((1,1,1,5))
                if col1.button('Open', key=f"{path} duplicate 1", use_container_width=True):
                    open_file_with_default_app(directory + path)
                if col2.button('Folder', key=f"{path} duplicate 2", use_container_width=True):
                    open_file_with_explorer(directory + path)
                st.write("")
                st.write("")

    files = files.drop_duplicates(subset='hash', keep=False)

    return files, all_duplicates


def get_text_from_file(file: str, ext: str):
    """
    This function takes in a file name and its extension as inputs. It reads the \
    file and extracts the text from it, depending on its extension. 

    Parameters:
    -----------
    - file: str
        A file name to be processed.
    - ext: str
        A file extension to be processed. Only files with these extensions are currently supported.

    Returns:
    --------
    - text: str
        A string containing the extracted text from the specified file.
    """
    if ext == 'pdf':
        fileReader = PyPDF2.PdfReader(file)
        text = '\n'.join([page.extract_text() for page in fileReader.pages])
    elif ext == 'msg':
        msg = extract_msg.Message(file)
        text = msg.body
    elif ext == 'docx':
        try:
            text = docx2txt.process(file)
        except zipfile.BadZipFile:
            st.error("Make sure all Word files are closed and refresh the page.")
            st.stop()
    elif ext == 'txt':
        with open(file, 'r') as f:
            text = f.read()
    elif ext == 'pptx':
        presentation = extract_pptx_text(file, False)
        text = ''
        for p in presentation:
            for info in p['slides']:
                text += info['bodyText'] + '\n'
    else:
        return ''

    return text


def copy_file(relative_path, directory, subfolder_name, root_folder_name):
    source_path = directory + relative_path
    destination_folder = os.path.join(directory,root_folder_name,subfolder_name)
    destination_path = os.path.join(destination_folder,relative_path)
    os.makedirs(destination_folder, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def delete_folder(directory, root_folder):
    folder_path = os.path.join(directory, root_folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


def open_file_with_default_app(file_path):
    """
    This function attempts to open a file with the default application associated \
    with its file type. The function first determines the operating system and \
    then uses the appropriate method to open the file.

    Parameters:
    -----------
    - file_path: str
        The path to the file that should be opened.

    Raises:
    -------
    - IOError: If the file could not be opened or if the default application could not be determined.

    Note:
    -----
    - This function is currently only supported on Unix-based systems (Linux, macOS) and Windows.
    """
    try:
        system = platform.system()
        if os.name == 'posix':  # Unix-based systems (Linux, macOS)
            os.system('open "{}"'.format(path))
        elif system == 'Windows':
            os.startfile(file_path)
        else:
            print('Unsupported operating system:', system)
    except Exception as e:
        st.error("Unable to open the file with the default application.")
        print(e)


def open_file_with_explorer(file_path):
    """
    This function opens the file specified by the given file path using the default \
    file explorer on the user's operating system.

    Parameters:
    -----------
    - file_path: str
        The path of the file to be opened.

    Notes:
    -----
    - This function is currently only supported on Unix-based systems (Linux, macOS) and Windows.
    """
    system = platform.system()
    if system == 'Windows':
        subprocess.Popen(f'explorer /select,"{file_path}"')
    elif system == 'Darwin':  # macOS
        subprocess.call(['open', '-R', file_path])
    elif system == 'Linux':
        subprocess.call(['xdg-open', os.path.dirname(file_path)])
    else:
        print('Unsupported operating system:', system)


def get_files(directory):
    """
    This function takes in a directory path as input and returns a list of files found \
    within the specified directory.

    Parameters:
    -----------
    - directory: str
        A directory path to be searched for files.

    Returns:
    --------
    - files: list
        A list of file paths found within the specified directory.
    """
    if directory == '':
        st.stop()

    if not os.path.isdir(directory):
        st.warning('Specified folder does not exist')
        st.stop()


    start_time = perf_counter()
    try:
        with st.spinner("Gathering files"):
            files = [os.path.join(root, file) for root, _, files in os.walk(directory) for file in files]
    except Exception as e:
        st.warning("Could not access the specified folder path due to the following error:")
        st.error(e)
        st.stop()

    if len(files) < 1:
        st.warning("Specified folder is empty")
        st.stop()

    st.session_state['log_data']['files_found'] = len(files)
    st.session_state['log_data']['timer'][0] = perf_counter() - start_time
    
    return files