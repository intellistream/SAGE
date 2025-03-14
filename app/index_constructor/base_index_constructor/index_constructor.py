import os
import warnings
from app.utils import load_corpus

class IndexConstructor:
    """Base class for constructing indexes."""

    def __init__(self, corpus_path, save_dir):
        self.corpus_path = corpus_path
        self.save_dir = save_dir
        self.prepare_save_dir()
        self.corpus = load_corpus(self.corpus_path)
        print("Finish loading corpus...")

    def prepare_save_dir(self):
        """Prepare the directory to save the index."""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        else:
            if len(os.listdir(self.save_dir)) > 0:
                warnings.warn("Save directory is not empty, files may be overwritten.", UserWarning)

    def build_index(self):
        """Build the index. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method.")