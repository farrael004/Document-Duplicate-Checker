from streamlit.web import cli
import streamlit as st
import hashlib
import numpy as np
import pandas as pd
import zipfile
import PyPDF2
import numpy as np
import itertools
from uuid import uuid1
import scipy
from collections import defaultdict
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
from multiprocessing import Pool
import extract_msg
from pptxer.presentations_text_extractor import __extract_presentation_texts_from_path__ as extract_pptx_text
import docx2txt
import numpy as np
import plotly.graph_objs as go
import streamlit as st
from sklearn.preprocessing import normalize
from scipy.sparse import vstack
from scipy.sparse.linalg import svds
import os
import re
import ktrain
from requests_ntlm import HttpNtlmAuth

cli.main_run_clExplicit('deduplication/app.py', 'streamlit run')