import streamlit as st
import pandas as pd
import ktrain
import scipy
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import numpy as np
from sklearn.preprocessing import normalize
from time import perf_counter
from sklearn.feature_extraction.text import CountVectorizer
from plot import get_plot
from logs import add_log
from files import open_file_with_default_app, open_file_with_explorer

vectorizer = CountVectorizer(ngram_range=(1, 5))

def cluster_documents(vector: scipy.sparse._csr.csr_matrix, args: dict, data: pd.DataFrame, directory: str, algo:str):
    """
    This function performs clustering on a given sparse matrix of document vectors using the \
    DBSCAN algorithm. It then sorts the resulting clusters by their average similarity and \
    visualizes each cluster by calling the 'visualize_cluster' function.

    Parameters:
    -----------
    - vector: scipy.sparse._csr.csr_matrix
        A sparse matrix of document vectors to be clustered.
    - args: dict
        A dict parameter for the clustering algorithm that controls hyperparameters based on algorithm selected.
    - data: pd.DataFrame
        A DataFrame containing the file names and vectors.
    - directory: str
        The root directory path where the files are located.
    - algo: str
        The algorithm selected by user to perform clustering.

    Returns:
    --------
    - cluster_df: pd.DataFrame
        A DataFrame containing the cluster information for all documents.
    """

    if algo == 'Similarity clustering':
        # Run DBSCAN clustering algorithm
        sensitivity = args["sensitivity"]

        if sensitivity == 0:
            sensitivity = 0.001

        dbscan = DBSCAN(eps=sensitivity, min_samples=2)
        nodes = dbscan.fit_predict(vector.toarray())
        cluster_labels = list(set(nodes))
    
    if algo == 'Topic clustering':
        # Run Topic Modeling using LDA algorithm
        data, nodes, cluster_labels = topic_modeling(data, args)
        return data

    # Calculate info for each path and cluster
    cluster_info = get_cluster_info(nodes, cluster_labels, vector, data)

    # Get information for each document
    document_info = create_document_dataframe(cluster_info, data, directory)

    return document_info

def topic_modeling(data, args):
    """
    This function takes in a data and hyper-parameters to perform topic modeling using LDA, 
    short for Latent Dirichlet Allocation.

    Parameters:
    -----------
    - data: DataFrame
        A DataFrame containing the file names and vectors.
    - args: dict 
        A dictionary containing hyperparameters - n_features, alpha and cut_off.

    Returns:
    --------
    - data: DataFrame
        The dataframe containing topic ids as modeled by LDA algorithm
    - cluster: ndarray
        The cluster label (based on topic id) corresponsing to each document.
    - labels: list
        The unique cluster labels
    """
    with st.spinner('Modeling Topics...'):
        # Get text data corresponding to each document from the dataframe
        doc_list = data.text.values.tolist()

        # Initialize topic modeling by specifying different hyperparameters
        tm = ktrain.text.get_topic_model(texts=doc_list, n_features=args['n_features'], hyperparam_kwargs={'alpha':args['alpha']})

        # Train the model and estimate the topics and associating words with each topic
        tm.build(doc_list, args["cut_off"])

        # Get the list of dictionaries specifying topic words for each topic
        topics = tm.get_topics()

        # Create a list of topic labels based on representative words
        topic_labels = []
        for topic_words in topics:
            topic_labels.append(''.join(topic_words))

        # Create a dictionary mapping topic IDs to labels
        topic_label_dict = dict(zip(range(len(topics)), topic_labels))

        # Get the list of dictionaries specifying topic ids for each document
        docs_ = tm.get_docs()
        document_df = pd.DataFrame(docs_)

        # Map topic IDs to topic labels in the document dataframe
        document_df['topic_label'] = document_df['topic_id'].map(topic_label_dict)

        # Join the two dataframes to get topic labels in the original dataframe
        data = pd.merge(data, document_df[['text', 'topic_label']], on="text")
        cluster = np.array(data.topic_label.tolist())
        labels = data.topic_label.unique().tolist()

    return data, cluster, labels

def get_cluster_info(nodes: np.ndarray, cluster_labels: list[str], vector: scipy.sparse._csr.csr_matrix, data: pd.DataFrame):
    """
    This function takes in three inputs: a numpy array of node labels, a list of \
    cluster labels, and a sparse matrix of vector representations of the nodes. It \
    returns a list of tuples containing information about each cluster.

    Parameters:
    -----------
    - nodes: np.ndarray
        A numpy array of node labels.
    - cluster_labels: list[str]
        A list of cluster labels.
    - vector: scipy.sparse._csr.csr_matrix
        A sparse matrix of vector representations of the nodes.

    Returns:
    --------
    - cluster_info: list[tuple]
        A list of tuples containing information about each cluster. Each tuple contains \
        four elements: a numpy array of the indices of the nodes in the cluster, the \
        average cosine similarity between all pairs of nodes in the cluster, a numpy array \
        of the vector representations of the nodes in the cluster, and the cluster labels.
    """
    cluster_info = []
    for i, cluster in enumerate(cluster_labels):
        if cluster == -1:
            continue
        indices = np.where(nodes == cluster)[0]
        similarities = []
        vectors = []
        path_average_similarities = {}
        progress1 = st.empty()
        if len(indices) > 1:
            for i, index1 in enumerate(indices):
                path = data['filename'].iloc[index1]
                progress1.progress((i + 1) / len(indices), f'Calculating similarities for {path}')
                progress2 = st.empty()
                path_similarities = []
                for i, index2 in enumerate(indices):
                    if index1 == index2:
                        continue
                    similarity = cosine_similarity(vector[index1], vector[index2])
                    similarities.append(similarity)
                    path_similarities.append(similarity)
                    progress2.progress((i + 1)/ len(indices), f'{(i + 1)}/{len(indices)}')
                vectors.append(vector[index1])
                progress2.empty()
                path_average_similarity = sum(path_similarities) / len(path_similarities)
                path_average_similarities[path] = path_average_similarity
            progress1.empty()
            path_average_similarities = dict(sorted(path_average_similarities.items(), key=lambda x: x[1], reverse=True))
        
            if len(similarities) > 0:
                average_similarity = sum(similarities) / len(similarities)
            else:
                average_similarity = 0
            cluster_info.append((indices, average_similarity, path_average_similarities, np.array(vectors), cluster))

    return cluster_info


def create_document_dataframe(cluster_info, document_data, directory):
    """
    This function takes the cluster_info list and creates a DataFrame where each row represents one of the documents.

    Parameters:
    -----------
    - cluster_info: list[tuple]
        A list of tuples containing information about each cluster.
    - document_data: pd.DataFrame
        A DataFrame containing the original documents or texts, which will be used for visualization purposes.
    - directory: str
        A directory path where the resulting visualizations will be saved.
    - visualizer: st.container

    Returns:
    --------
    - cluster_df: pd.DataFrame
        A DataFrame containing the document path, vector, and cluster label for each index in the cluster_info list.
    """
    data = []
    cluster_df = pd.DataFrame()
    for info in cluster_info:
        indices, average_similarity, path_average_similarities, vectors, cluster = info
        
        for i, index in enumerate(indices):
            full_path = document_data['filename'].iloc[index]
            path = full_path.replace(directory, '')
            data.append({
                'path': full_path,
                'average_similarity': average_similarity[0][0],
                'path_average_similarities': path_average_similarities[full_path][0][0],
                'vector': vectors[i],
                'label': cluster})
        cluster_df = pd.DataFrame().from_records(data)
        cluster_df = cluster_df.sort_values(by=['average_similarity', 'path_average_similarities'], ascending=False)

    return cluster_df

def cluster(directory:str,
            tab2: st.delta_generator.DeltaGenerator,
            tab3: st.delta_generator.DeltaGenerator,
            visualizer: st.delta_generator.DeltaGenerator,
            form_args: dict,
            algo_option: str,
            submit_button: bool,
            text_extensions: list,
            text_data: pd.DataFrame,
            generic_data: pd.DataFrame):
    """
    This function clusters and visualizes documents based on their similarity \
    or assigned topics. It takes the following inputs:

    Parameters:
    -----------
    - directory: str
        The directory where the documents are stored.
    - tab2: streamlit.delta_generator.DeltaGenerator
        The expander object for the second tab.
    - tab3: streamlit.delta_generator.DeltaGenerator
        The expander object for the third tab.
    - visualizer: streamlit.delta_generator.DeltaGenerator
        The visualizer object.
    - form_args: dict
        A dictionary containing form arguments.
    - algo_option: str
        The selected algorithm option.
    - submit_button: bool
        A boolean value indicating whether the submit button has been pressed.
    - text_extensions: list
        A list of supported file extensions for text extraction.
    - text_data: pd.DataFrame
        A dataframe containing the text data of the documents.
    - generic_data: pd.DataFrame
        A dataframe containing the generic data of the documents.
    """
    with visualizer:
        if not generic_data.empty:
            with st.expander("Non-supported documents for text extraction"):
                for row in generic_data.to_records():
                    st.write(row['filename'].replace(directory, ''))
                st.divider()
                st.write('Supported file types:')
                st.write(f'{" - ".join(text_extensions)}')

        if text_data.empty:
            st.warning("No supported text documents were found.")
            st.stop()

    start_time = perf_counter()        
    vector = get_file_vectors(text_data)
    normalized_vectors = normalize(vector)

    if submit_button:
        documents = cluster_documents(normalized_vectors, form_args, text_data, directory, algo_option)
        st.session_state['documents'] = documents
        #add_log(form_args, algo_option, start_time, documents)

    if 'documents' not in st.session_state:
        tab2.info('Choose appropriate settings on the sidebar and press "Submit".')
        tab3.info('Choose appropriate settings on the sidebar and press "Submit".')
        st.stop()
    documents = st.session_state['documents']

    with visualizer:
        if algo_option == 'Similarity clustering':
            if documents.empty:
                st.success("No documents were flagged as similar with the current sensitivity.")
                st.stop()

            if 'label' not in documents:
                st.info('Press the "Submit" button to continue.')
                st.stop()
            cluster_list = documents['label'].unique()

            #delete_folder(directory, 'similar')

            for i, cluster in enumerate(cluster_list):
                rows = documents.loc[documents['label'] == cluster]
                average_similarity = rows['average_similarity'].iloc[0]
                with st.expander(f"{average_similarity.item() * 100:.2f}%"):
                    for row in rows.to_records():
                        path_avg_sim = row['path_average_similarities']
                        path = row['path']

                        #copy_file(path, directory,  f'{path_avg_sim * 100:.2f}% - {i}', 'similar')

                        st.write(path.replace(directory, ""))
                        col1, col2, col3, col4 = st.columns((1,1,1,5))
                        col3.write(f'<span style="color:green">{path_avg_sim * 100:.2f}%</span>', unsafe_allow_html=True)
                        if col1.button('Open', key=f"{path} 1", use_container_width=True):
                            open_file_with_default_app(path)
                        if col2.button('Folder', key=f"{path} 2", use_container_width=True):
                            open_file_with_explorer(path)
                        st.write("")
                        st.write("")

                    st.write(f'Average similarity within cluster: <span style="color:red">{average_similarity.item() * 100:.2f}%</span>', unsafe_allow_html=True)
        else:
            if documents.empty:
                st.success("No documents were assigned similar topics")
                st.stop()
            
            if 'topic_label' not in documents:
                st.info('Press the "Submit" button to continue.')
                st.stop()
            cluster_list = documents['topic_label'].unique()

            #delete_folder(directory, 'similar')

            for i, cluster in enumerate(cluster_list):
                rows = documents.loc[documents['topic_label'] == cluster]
                with st.expander(cluster):
                    for row in rows.to_records():
                        path = row['filename'].replace(directory, '')

                        #copy_file(path, directory,  f'{path_avg_sim * 100:.2f}% - {i}', 'similar')

                        st.write(path.replace(directory, ""))
                        col1, col2, col3, col4 = st.columns((1,1,1,5))
                        i = 1
                        while True:
                            try:
                                if col1.button('Open', key=f"{path} {i}", use_container_width=True):
                                    open_file_with_default_app(path)
                                if col2.button('Folder', key=f"{path} {i + 1}", use_container_width=True):
                                    open_file_with_explorer(path)
                                break
                            except st.errors.DuplicateWidgetID as e:
                                i += 1
                            
                        st.write("")
                        st.write("")

    with tab3:
        if algo_option != 'Similarity clustering': st.stop()
        if st.checkbox('Plot documents'):
            if algo_option != 'Topic-Modeling':
                plot_info = get_plot(cluster_list, documents, directory)

                fig = plot_info['figure']
                hover_texts = plot_info['hover_texts']
                events = fig.data[0]

                # Render the figure using Plotly
                st.plotly_chart(fig, use_container_width=True)
            
                # Display a button to show the information of the selected point
                index_input = st.number_input("Enter the index of a point", min_value=0, max_value=len(hover_texts) - 1, step=1, value=0, help="The index is the number that appears at the left of the file's name in the plot.")
                col1, col2, col3 = st.columns((1,1,6))
                if col1.button('Open', use_container_width=True):
                    open_file_with_default_app(directory + hover_texts[index_input])
                if col2.button('Folder', use_container_width=True):
                    open_file_with_explorer(directory + hover_texts[index_input])

            else:
                documents.rename(columns={'topic_label':'label', 'filename':'path'}, inplace=True)
                documents['vector'] = np.array(normalized_vectors)
                plot_info = get_plot(cluster_list, documents, directory)

                fig = plot_info['figure']
                hover_texts = plot_info['hover_texts']

                # Render the figure using Plotly
                st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def get_file_vectors(files):
    return vectorizer.fit_transform(files['text'])