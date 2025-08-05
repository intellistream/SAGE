# SAGE Project Makefile

.PHONY: build install help

# Build all wheels using the build script
build:
	@echo "Building all wheels..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/build_all_wheels.sh > ~/.sage/makefile_logs/build.log 2>&1

# Install all wheels using the install script
install:
	@echo "Installing wheels..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/install_wheels.sh > ~/.sage/makefile_logs/install.log 2>&1

# Show help information
help:
	@echo "Available targets:"
	@echo "  build   - Build all wheels using build_all_wheels.sh"
	@echo "  install - Install wheels using install_wheels.sh"
	@echo "  help    - Show this help message"