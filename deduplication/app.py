import streamlit as st
from logs import login
from files import get_files, get_data, remove_duplicates
from clustering import cluster
from search import exact_search


st.set_page_config(
    page_title="Duplicate Document Checker", page_icon="📘"
)

login()

st.title("📘Duplicate Document Checker")

app = st.container()

st.divider()
with st.expander("Help", expanded=False):
    st.markdown("""
1. **Clusters**: Each cluster is represented by an expandable section. \
The percentage value shown at the top of the section represents the average \
similarity within that cluster. Higher percentages indicate a higher level \
of similarity among the documents in the cluster.
    
2. **Similarities**: Within each cluster, individual documents are listed along \
with their corresponding average similarity scores. The scores are displayed \
as percentages, indicating the similarity between the document and other \
documents in the same cluster. Higher percentages suggest a greater similarity.

3. **Ordering**: The documents are sorted based on their average similarity scores, \
with the most similar documents appearing at the top. This arrangement helps \
identify the most closely related documents within the cluster.

4. **Colors**: The average similarity within the cluster is highlighted in red, \
providing a quick reference point for the overall similarity level in the cluster. \
The individual document similarities are displayed in green, allowing you to identify \
the most similar documents at a glance.
""")
    
with app:
    st.markdown('---')
    directory = st.text_input('Folder path', help="Root folder where all subfolders and documents to be analyzed are.")
    tab1, tab2, tab3, tab4 = st.tabs(['Duplicates', 'Similar documents', 'Visualizer', 'Search'])
    visualizer = tab2.container()

    if 'log_data' not in st.session_state:
        st.session_state['log_data'] = {}
        st.session_state['log_data']['timer'] = [0,0,0]

    files = get_files(directory)

    text_extensions = ["pdf", "docx", "msg", "txt", "pptx"]
    with tab1:
        text_data, image_data, generic_data, files_analyzed, time = get_data(files, directory, text_extensions)
        
        duplicate_filenames = []
        text_data, duplicate_filenames = remove_duplicates(text_data, directory)
        duplicate_filenames += duplicate_filenames
        image_data, duplicate_filenames = remove_duplicates(image_data, directory)
        duplicate_filenames += duplicate_filenames
        generic_data, duplicate_filenames = remove_duplicates(generic_data, directory)
        duplicate_filenames += duplicate_filenames

    st.session_state['log_data']['duplicates_found'] = len(duplicate_filenames)
    st.session_state['log_data']['files_analysed'] = files_analyzed
    st.session_state['log_data']['timer'][1] = time
    st.session_state['log_data']['root_directory'] = directory[-255:]

    form_args = {}

with st.sidebar:
    st.subheader('Settings')
    algo_option = st.selectbox('Which task do you want to perform?',
                                ('Select a task', 'Similarity clustering', 'Topic clustering'))
    
    if algo_option == 'Select a task':
        st.warning('Please select a task')
        st.stop()
    
    elif algo_option == 'Similarity clustering':
        with st.form('Form'):
            sensitivity = st.slider('Sensitivity', min_value=0, max_value=100, value=50, step=5, help="This controls the level of granularity in the similarity results. Increasing it will group more documents together, potentially including less similar ones. Decreasing it will produce tighter clusters, with only highly similar documents grouped together.")
            sensitivity = sensitivity/100
            n_gram_length = 3 #st.slider('N-gram', min_value=1, max_value=10, value=3, step=1, help="Determines the size of text chunks used for comparison. Higher values increase specificity, while lower values make the analysis broader.")
            form_args["sensitivity"] = sensitivity
            form_args["n_gram_length"] = n_gram_length
            submit_button = st.form_submit_button('Submit', use_container_width=True)
    
    elif algo_option == 'Topic clustering':
        with st.form('Form'):
            n_features = st.slider('No. of Features', min_value=1000, max_value=15000, value=10000, step=500, help="This controls the number of features")
            alpha = st.slider('Alpha', min_value=0.0, max_value=1.0, value=0.5, step=0.1, help="...")
            cut_off = st.slider('Cut-off Value', min_value=0.0, max_value=1.0, value=0.25, step=0.05, help="...")
            form_args["n_features"] = n_features
            form_args["alpha"] = alpha
            form_args["cut_off"] = cut_off
            submit_button = st.form_submit_button('Submit', use_container_width=True)
            

with app:
    if algo_option == 'Topic clustering' or algo_option == 'Similarity clustering':
        cluster(directory, tab2, tab3, visualizer, form_args, algo_option, submit_button, text_extensions, text_data, generic_data)

    with tab4:
        query = st.text_area('Query')
            
        t1, t2 = st.columns((1,3))
        exact_word = t1.checkbox('Word matching', True)
        case_sensitive = t2.checkbox('Case sensitive', True)
        if query == "": st.stop()
        exact_search(text_data, query, directory, case_sensitive, exact_word)