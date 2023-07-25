import streamlit as st
import plotly.graph_objs as go
import numpy as np
import pandas as pd
from scipy.sparse import vstack
from scipy.sparse.linalg import svds

@st.cache_data
def get_plot(cluster_list: list, documents: pd.DataFrame, directory: str):
    """
    This function plots a 3-dimensional scatter plot using the data \
    from the documents dataframe, where each data point is assigned \
    a color based on its cluster label.

    Parameters:
    -----------
    - cluster_list: list
        A list of cluster labels.
    - documents: DataFrame
        A dataframe containing the document data, including cluster labels and vector representations.
    - directory: str
        The directory path where the documents are stored.

    Returns:
    --------
    A dictionary with the following keys:
    - 'figure': go.Figure
        The 3-dimensional scatter plot figure.
    - 'hover_texts': list
        A list of hover texts for each data point, displaying the file paths of the corresponding documents.
    """
    # Create a color map for each cluster
    color_map = {c: np.random.rand(3) for c in cluster_list}

    # Assign a color to each data point based on its cluster
    colors = [color_map[label] for label in documents['label']]

    # Set transparency for each data point
    alpha = 0.5

    with st.spinner('Plotting...'):
        # Standardize the data
        vectors_sparse = vstack(documents['vector'].to_list()).astype(float)
        #normalized_vectors = normalize(vectors_sparse)

        # Get three dimentional projection of the vectors
        svd = svds(vectors_sparse, k=3)
        data = svd[0]

    hover_texts = documents['path'].apply(lambda x: x.replace(directory, '')).to_list()
    hover_texts_with_index = documents['path'].apply(lambda x: x.replace(directory, f"{str(documents['path'].tolist().index(x))} - ")).to_list()

    # Create a scatter3d trace with colors and transparency
    trace = go.Scatter3d(
        x=data[:, 0],
        y=data[:, 1],
        z=data[:, 2],
        hovertext=hover_texts_with_index,
        hovertemplate= "%{hovertext}",
        mode='markers',
        marker=dict(
            size=8,
            color=colors,
            opacity=alpha
        )
    )

    # Create the layout
    layout = go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(
            xaxis=dict(title='X', showticklabels=False),
            yaxis=dict(title='Y', showticklabels=False),
            zaxis=dict(title='Z', showticklabels=False)
        )
    )

    # Create the figure
    fig = go.Figure(data=[trace], layout=layout)

    return {'figure': fig, 'hover_texts': hover_texts}