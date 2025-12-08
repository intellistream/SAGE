import sys
import warnings
from unittest.mock import MagicMock

# Filter Swig warnings from importlib
warnings.filterwarnings("ignore", message="builtin type SwigPyPacked has no __module__ attribute")
warnings.filterwarnings("ignore", message="builtin type SwigPyObject has no __module__ attribute")
warnings.filterwarnings("ignore", message="builtin type swigvarlink has no __module__ attribute")


def mock_module(name):
    m = MagicMock()
    m.__spec__ = MagicMock()
    m.__spec__.name = name
    m.__spec__.parent = name.rsplit(".", 1)[0] if "." in name else None
    m.__path__ = []
    sys.modules[name] = m
    return m


# Mock heavy dependencies to avoid import errors and speed up tests
# We must do this at the top level of conftest.py so it runs before test collection imports

# 1. Mock torch and related
mock_module("torch")
mock_module("torch.optim")
mock_module("sentence_transformers")
mock_module("faiss")

# 2. Mock transformers/datasets
mock_module("transformers")
mock_module("datasets")

# 3. Mock internal heavy modules
mock_module("sage.middleware.components")
mock_module("sage.middleware.components.sage_refiner")
mock_module("sage.libs.finetune")
mock_module("sage.libs.rag")
mock_module("sage.libs.integrations")
