"""Root entry point for Streamlit Community Cloud."""
from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).parent / 'Mini Proyek' / 'app.py'),
    run_name='__main__',
)
