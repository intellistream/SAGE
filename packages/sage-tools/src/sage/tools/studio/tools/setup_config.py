#!/usr/bin/env python3
"""
SAGE Studio Configuration Setup

This script configures Angular Studio to use the correct output paths
from the centralized SAGE output paths configuration.
"""

import json
import os
import sys
from pathlib import Path


def setup_studio_config():
    """Setup Studio configuration with correct paths"""

    # Add the packages to Python path
    current_dir = Path(__file__).parent
    packages_dir = current_dir.parent.parent.parent.parent / "packages"
    sys.path.insert(0, str(packages_dir / "sage-common" / "src"))

    try:
        from sage.common.config.output_paths import get_sage_paths

        # Get the correct paths
        paths = get_sage_paths()
        studio_dist_dir = paths.studio_dist_dir

        # Convert to relative path from studio directory
        studio_dir = current_dir
        relative_dist_path = os.path.relpath(studio_dist_dir, studio_dir)

        print(f"Studio directory: {studio_dir}")
        print(f"Studio dist directory: {studio_dist_dir}")
        print(f"Relative dist path: {relative_dist_path}")

        # Update angular.json
        angular_json_path = studio_dir / "angular.json"

        if angular_json_path.exists():
            with open(angular_json_path, 'r') as f:
                config = json.load(f)

            # Update outputPath and cache path
            if 'projects' in config and 'dashboard' in config['projects']:
                if 'architect' in config['projects']['dashboard']:
                    if 'build' in config['projects']['dashboard']['architect']:
                        if 'options' in config['projects']['dashboard']['architect']['build']:
                            config['projects']['dashboard']['architect']['build']['options']['outputPath'] = relative_dist_path

                            # Update cache path
                            if 'cli' not in config:
                                config['cli'] = {}
                            if 'cache' not in config['cli']:
                                config['cli']['cache'] = {}
                            
                            cache_dir = paths.studio_dir / "cache"
                            relative_cache_path = os.path.relpath(cache_dir, studio_dir)
                            config['cli']['cache']['path'] = relative_cache_path
                            config['cli']['cache']['enabled'] = True
                            config['cli']['cache']['environment'] = "all"
                            config['cli']['analytics'] = False

                            # Write back to file
                            with open(angular_json_path, 'w') as f:
                                json.dump(config, f, indent=2)

                            print(f"✅ Updated angular.json outputPath to: {relative_dist_path}")
                            print(f"✅ Updated angular.json cache path to: {relative_cache_path}")
                        else:
                            print("❌ Could not find build options in angular.json")
                    else:
                        print("❌ Could not find build configuration in angular.json")
                else:
                    print("❌ Could not find architect configuration in angular.json")
            else:
                print("❌ Could not find dashboard project in angular.json")
        else:
            print(f"❌ angular.json not found at: {angular_json_path}")

    except ImportError as e:
        print(f"❌ Could not import output_paths: {e}")
        # Fallback to default relative path
        fallback_path = "../../../.sage/studio/dist"
        print(f"⚠️ Using fallback path: {fallback_path}")

        angular_json_path = current_dir / "angular.json"
        if angular_json_path.exists():
            with open(angular_json_path, 'r') as f:
                config = json.load(f)

            if 'projects' in config and 'dashboard' in config['projects']:
                if 'architect' in config['projects']['dashboard']['architect']['build']['options']:
                    config['projects']['dashboard']['architect']['build']['options']['outputPath'] = fallback_path

                    with open(angular_json_path, 'w') as f:
                        json.dump(config, f, indent=2)

                    print(f"✅ Updated angular.json outputPath to fallback: {fallback_path}")


if __name__ == "__main__":
    setup_studio_config()