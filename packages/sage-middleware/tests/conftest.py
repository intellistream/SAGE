import warnings

# Filter Swig warnings from importlib
warnings.filterwarnings("ignore", message="builtin type SwigPyPacked has no __module__ attribute")
warnings.filterwarnings("ignore", message="builtin type SwigPyObject has no __module__ attribute")
warnings.filterwarnings("ignore", message="builtin type swigvarlink has no __module__ attribute")

# NOTE: We removed the aggressive module mocking that was causing test failures.
# Tests that need specific modules should handle import errors gracefully
# using try/except or pytest.importorskip().
#
# Previous problematic mocking:
# - mock_module("faiss") -> caused isinstance() errors with faiss.IndexIDMap
# - mock_module("sage.middleware.components.sage_refiner") -> caused ContextService tests to fail
# - mock_module("torch") -> caused TextDetector tests to fail
#
# If a test needs to mock these dependencies, it should do so at the test level,
# not globally in conftest.py.
