from streamlit.web import cli
from git import Repo
from git.exc import NoSuchPathError
import os


dir_path = os.path.dirname(os.path.realpath("__file__")) + "\\ddc"

# Update repo or clone if it doesn't exist
try:
    repo = Repo('ddc/')
    origin = repo.remote(name='origin')
    origin.pull()
except NoSuchPathError:
    repo = Repo.clone_from("https://github.com/farrael004/Document-Duplicate-Checker", dir_path, branch="main")

# Launch app
cli.main_run_clExplicit('ddc/deduplication/app.py', 'streamlit run')