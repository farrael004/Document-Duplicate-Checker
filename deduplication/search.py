import streamlit as st
import re
import pandas as pd
from files import open_file_with_default_app, open_file_with_explorer

@st.cache_data
def find_occurences(text: str, query: str, case_sensitive: bool=True, exact_word: bool=True):
    """
    This function takes in a text, a query, and optional parameters for \
    case sensitivity and exact word matching. It finds occurrences of \
    the query in the text and extracts excerpts around each occurrence.

    Parameters:
    -----------
    - text: str
        The text to search for occurrences of the query.
    - query: str
        The query to search for in the text.
    - case_sensitive: bool, optional
        Determines whether the search is case sensitive or not. Default is True.
    - exact_word: bool, optional
        Determines whether the query should match whole words only. Default is True.

    Returns:
    --------
    - excerpts: list
        A list of excerpts extracted from the text. Each excerpt contains \
        the original text with the matched query highlighted using HTML tags.
    """
    excerpts = []
    query_length = len(query)
    max_excerpt_length = 1000

    # Apply case sensitivity based on the setting
    if not case_sensitive:
        processed_text = text.lower()
        query = query.lower()
    else:
        processed_text = text

    # Build the regular expression pattern
    if exact_word:
        pattern = r"\b" + re.escape(query) + r"\b"
    else:
        pattern = re.escape(query)

    # Find the indices of the matches in the text
    match_indices = [m.start() for m in re.finditer(pattern, processed_text, re.IGNORECASE if not case_sensitive else 0)]

    # Extract excerpts around each match index
    last_end_index = 0
    for index in match_indices:
        # Check if the current index is within the previous excerpt
        if index < last_end_index:
            continue

        # Extract fixed length excerpts
        start_index = max(0, index - max_excerpt_length // 2)
        end_index = min(len(text), index + query_length + max_excerpt_length // 2)

        # Update the last_end_index value
        last_end_index = end_index

        # Include the original text (with case sensitivity) in the excerpt
        original_text = text[start_index:end_index]

        # Wrap the matched text in an HTML tag
        highlighted_excerpt = re.sub(pattern, r"<span style='background-color: yellow'>\g<0></span>", original_text, flags=re.IGNORECASE if not case_sensitive else 0)
        excerpts.append(highlighted_excerpt)

    return excerpts


def chunk_text(text: str, max_length: int=1000):
    """
    This function takes in a string containing text and splits it into \
    chunks, where each chunk has a maximum length specified by the \
    'max_length' parameter.

    Parameters:
    -----------
    - text: str
        The input text to be split into chunks.
    - max_length: int, optional
        The maximum length of each chunk. Defaults to 1000.

    Returns:
    --------
    - split_paragraphs: list[str]
        A list of strings, where each string is a chunk of the input text.
    """
    split_paragraphs = []
    for paragraph in text.split("\n"):
        if paragraph in [" \r", "\r", ""]: continue
        # Split the paragraph until no parts are larger than the max length
        first_section = True
        while len(paragraph) > max_length:
            split_index = paragraph.find('.\n', max_length)
            # If there's no '.\n' after the max length, check for the next instance of '.['
            if split_index == -1:
                split_index = paragraph.find('.[', max_length)
                # If there's no instance of '.[' after the max length, just split at the max length
                if split_index == -1:
                    split_index = max_length
            split_paragraph = paragraph[:split_index]
            # Indicate where strings were split with '(...)'
            if not first_section:
                split_paragraph = '(...)' + split_paragraph
            split_paragraph = split_paragraph + '(...)'
            split_paragraphs.append(split_paragraph)
            paragraph = paragraph[split_index:]
            first_section = False
        split_paragraphs.append(paragraph)
    return split_paragraphs


def exact_search(text_data: pd.DataFrame, query: str, directory: str, case_sensitive: bool, exact_word: bool):
    """
    This function performs an exact search on text data and displays matching results.

    Parameters:
    -----------
    - text_data: pd.DataFrame
        A pandas DataFrame containing text data to be searched.
    - query: str
        The search query to be matched against the text data.
    - directory: str
        The directory path where the text files are located.
    - case_sensitive: bool
        A boolean value indicating whether the search should be case sensitive or not.
    - exact_word: bool
        A boolean value indicating whether the search should match exact words or not.
    """
    text_data['matches'] = text_data['text'].apply(lambda x: find_occurences(x, query, case_sensitive, exact_word))
    for i, file in text_data.iterrows():
        if len(file['matches']) > 0:
            with st.expander(file['filename'].replace(directory, '')):
                col1, col2, col3 = st.columns((1,1,6))
                if col1.button('Open', key=f"{file['filename']} 3", use_container_width=True):
                    open_file_with_default_app(file['filename'])
                if col2.button('Folder', key=f"{file['filename']} 4", use_container_width=True):
                    open_file_with_explorer(file['filename'])
                for match in file['matches']:
                    st.divider()
                    st.write(match, unsafe_allow_html=True)