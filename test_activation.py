#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from install import SageInstaller
    installer = SageInstaller()
    installer.create_activation_script('minimal')
    print('✅ Activation script created successfully!')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
