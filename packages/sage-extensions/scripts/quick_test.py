#!/usr/bin/env python3
from sage.extensions.sage_db import SageDB
print("✓ Import successful")
db = SageDB(128)
print(f"✓ Database created: dimension={db.dimension()}")
print("✓ All tests passed!")
