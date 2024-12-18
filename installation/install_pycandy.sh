     #!/bin/bash

     # Set package name and version
     PACKAGE_NAME="candy"
     PACKAGE_VERSION="0.1.0"

    # Step 0: Env config
    pip show wheel >/dev/null 2>&1 || pip install wheel

     # Step 1: Define paths
     BUILD_DIR="./candy"
     DIST_DIR="./dist"
     SITE_PACKAGES=$(python3 -c "import site; print(site.getusersitepackages())")

     # Step 2: Create necessary directories
     mkdir -p "$BUILD_DIR" "$DIST_DIR"

     # Step 3: Copy .so files to build directory
     echo "Copying .so files from $SITE_PACKAGES to $BUILD_DIR"
     cp "$SITE_PACKAGES"/*.so "$BUILD_DIR/" || {
         echo "Error: No .so files found in $SITE_PACKAGES."
         exit 1
     }

     # Step 3.5: Ensure the package has an __init__.py file
    echo "Ensuring $BUILD_DIR/__init__.py exists..."
    touch "$BUILD_DIR/__init__.py"

     # Step 4: Package the Python module
     echo "Building the Python package..."
     python3 setup.py sdist bdist_wheel || {
         echo "Error: Failed to build the package."
         exit 1
     }

     # Step 5: Install the package
     WHEEL_FILE="$DIST_DIR/${PACKAGE_NAME}-${PACKAGE_VERSION}-py3-none-any.whl"
     if [ -f "$WHEEL_FILE" ]; then
         echo "Installing $WHEEL_FILE..."
         pip install --force-reinstall "$WHEEL_FILE" || {
             echo "Error: Failed to install the package."
             exit 1
         }
     else
         echo "Error: Wheel file not found. Build may have failed."
         exit 1
     fi

     echo "Package installed successfully."
