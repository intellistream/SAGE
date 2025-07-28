#!/bin/bash

# SAGE Kafka Installation Script
# Installs Kafka to third_party directory if not already available in system

set -e  # Exit on any error

# Variables
SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
THIRD_PARTY_DIR="$SAGE_ROOT/third_party"
KAFKA_DIR="$THIRD_PARTY_DIR/kafka"
KAFKA_VERSION="3.7.2"
SCALA_VERSION="2.13"
KAFKA_PACKAGE="kafka_${SCALA_VERSION}-${KAFKA_VERSION}"
KAFKA_URL="https://downloads.apache.org/kafka/${KAFKA_VERSION}/${KAFKA_PACKAGE}.tgz"
KAFKA_LOGS_DIR="$THIRD_PARTY_DIR/kafka-logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function check_system_kafka() {
    print_status "Checking for existing Kafka installation..."
    
    # Check if Kafka is running on default port
    if netstat -tuln 2>/dev/null | grep -q ":9092 "; then
        print_success "Found running Kafka on port 9092"
        return 0
    fi
    
    # Check common Kafka installation paths
    if command -v kafka-server-start.sh >/dev/null 2>&1; then
        print_success "Found Kafka in system PATH"
        return 0
    fi
    
    # Check if Kafka exists in common directories
    for kafka_path in "/opt/kafka" "/usr/local/kafka" "$HOME/kafka"; do
        if [ -d "$kafka_path" ] && [ -f "$kafka_path/bin/kafka-server-start.sh" ]; then
            print_success "Found Kafka installation at $kafka_path"
            return 0
        fi
    done
    
    print_warning "No existing Kafka installation found"
    return 1
}

function check_java() {
    print_status "Checking Java installation..."
    
    if ! command -v java >/dev/null 2>&1; then
        print_error "Java is required but not installed. Please install Java 8 or later."
        print_status "On Ubuntu/Debian: sudo apt-get install openjdk-11-jdk"
        print_status "On CentOS/RHEL: sudo yum install java-11-openjdk-devel"
        exit 1
    fi
    
    java_version=$(java -version 2>&1 | grep -oP 'version "?(1\.)?\K\d+' | head -1)
    if [ "$java_version" -lt 8 ]; then
        print_error "Java 8 or later is required. Found Java $java_version"
        exit 1
    fi
    
    print_success "Java $java_version found"
}

function download_kafka() {
    print_status "Downloading Kafka $KAFKA_VERSION..."
    
    # Create third_party directory
    mkdir -p "$THIRD_PARTY_DIR"
    cd "$THIRD_PARTY_DIR"
    
    # Remove existing Kafka directory if it exists
    if [ -d "$KAFKA_DIR" ]; then
        print_warning "Removing existing Kafka installation..."
        rm -rf "$KAFKA_DIR"
    fi
    
    # Download Kafka
    if ! wget -O "${KAFKA_PACKAGE}.tgz" "$KAFKA_URL"; then
        print_error "Failed to download Kafka from $KAFKA_URL"
        exit 1
    fi
    
    print_success "Kafka downloaded successfully"
}

function install_kafka() {
    print_status "Installing Kafka..."
    
    cd "$THIRD_PARTY_DIR"
    
    # Extract Kafka
    if ! tar -xzf "${KAFKA_PACKAGE}.tgz"; then
        print_error "Failed to extract Kafka archive"
        exit 1
    fi
    
    # Rename to standard kafka directory
    mv "$KAFKA_PACKAGE" kafka
    
    # Clean up archive
    rm -f "${KAFKA_PACKAGE}.tgz"
    
    # Create logs directory
    mkdir -p "$KAFKA_LOGS_DIR"
    
    print_success "Kafka installed to $KAFKA_DIR"
}

function configure_kafka() {
    print_status "Configuring Kafka..."
    
    # Create custom server.properties
    cat > "$KAFKA_DIR/config/sage-server.properties" << EOF
# SAGE Kafka Configuration
broker.id=0
listeners=PLAINTEXT://localhost:9092
log.dirs=$KAFKA_LOGS_DIR
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
num.partitions=1
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=localhost:2181
zookeeper.connection.timeout.ms=18000
group.initial.rebalance.delay.ms=0
auto.create.topics.enable=true
EOF
    
    # Create custom zookeeper.properties
    cat > "$KAFKA_DIR/config/sage-zookeeper.properties" << EOF
# SAGE Zookeeper Configuration
dataDir=$THIRD_PARTY_DIR/zookeeper-data
clientPort=2181
maxClientCnxns=0
admin.enableServer=false
EOF
    
    # Create zookeeper data directory
    mkdir -p "$THIRD_PARTY_DIR/zookeeper-data"
    
    print_success "Kafka configuration completed"
}

function create_management_scripts() {
    print_status "Creating Kafka management scripts..."
    
    # Create start script
    cat > "$KAFKA_DIR/sage-kafka-start.sh" << 'EOF'
#!/bin/bash
# SAGE Kafka Start Script

KAFKA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$(dirname "$KAFKA_DIR")/kafka-logs"

echo "Starting SAGE Kafka services..."

# Check if services are already running
if pgrep -f "sage-zookeeper.properties" > /dev/null; then
    echo "Zookeeper is already running"
else
    echo "Starting Zookeeper..."
    nohup "$KAFKA_DIR/bin/zookeeper-server-start.sh" "$KAFKA_DIR/config/sage-zookeeper.properties" > "$LOGS_DIR/zookeeper.log" 2>&1 &
    sleep 3
fi

if pgrep -f "sage-server.properties" > /dev/null; then
    echo "Kafka is already running"
else
    echo "Starting Kafka..."
    nohup "$KAFKA_DIR/bin/kafka-server-start.sh" "$KAFKA_DIR/config/sage-server.properties" > "$LOGS_DIR/kafka.log" 2>&1 &
    sleep 3
fi

echo "SAGE Kafka services started"
echo "Kafka is available at localhost:9092"
echo "Logs are in: $LOGS_DIR"
EOF

    # Create stop script
    cat > "$KAFKA_DIR/sage-kafka-stop.sh" << 'EOF'
#!/bin/bash
# SAGE Kafka Stop Script

KAFKA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping SAGE Kafka services..."

# Stop Kafka
if pgrep -f "sage-server.properties" > /dev/null; then
    echo "Stopping Kafka..."
    "$KAFKA_DIR/bin/kafka-server-stop.sh"
    sleep 2
fi

# Stop Zookeeper
if pgrep -f "sage-zookeeper.properties" > /dev/null; then
    echo "Stopping Zookeeper..."
    "$KAFKA_DIR/bin/zookeeper-server-stop.sh"
    sleep 2
fi

echo "SAGE Kafka services stopped"
EOF

    # Create status script
    cat > "$KAFKA_DIR/sage-kafka-status.sh" << 'EOF'
#!/bin/bash
# SAGE Kafka Status Script

echo "SAGE Kafka Status:"
echo "=================="

if pgrep -f "sage-zookeeper.properties" > /dev/null; then
    echo "✅ Zookeeper: Running"
else
    echo "❌ Zookeeper: Stopped"
fi

if pgrep -f "sage-server.properties" > /dev/null; then
    echo "✅ Kafka: Running"
else
    echo "❌ Kafka: Stopped"
fi

if netstat -tuln 2>/dev/null | grep -q ":9092 "; then
    echo "✅ Port 9092: Available"
else
    echo "❌ Port 9092: Not accessible"
fi
EOF

    # Make scripts executable
    chmod +x "$KAFKA_DIR/sage-kafka-start.sh"
    chmod +x "$KAFKA_DIR/sage-kafka-stop.sh"
    chmod +x "$KAFKA_DIR/sage-kafka-status.sh"
    
    print_success "Management scripts created"
}

function create_env_setup() {
    print_status "Creating environment setup..."
    
    # Create environment file
    cat > "$THIRD_PARTY_DIR/kafka-env.sh" << EOF
#!/bin/bash
# SAGE Kafka Environment Setup

export SAGE_KAFKA_HOME="$KAFKA_DIR"
export SAGE_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Add Kafka to PATH if not already there
if [[ ":$PATH:" != *":$KAFKA_DIR/bin:"* ]]; then
    export PATH="$KAFKA_DIR/bin:$PATH"
fi

echo "SAGE Kafka environment loaded"
echo "Kafka Home: $SAGE_KAFKA_HOME"
echo "Bootstrap Servers: $SAGE_KAFKA_BOOTSTRAP_SERVERS"
EOF
    
    chmod +x "$THIRD_PARTY_DIR/kafka-env.sh"
    
    print_success "Environment setup created at $THIRD_PARTY_DIR/kafka-env.sh"
}

function test_installation() {
    print_status "Testing Kafka installation..."
    
    # Source the environment
    source "$THIRD_PARTY_DIR/kafka-env.sh"
    
    # Start Kafka
    "$KAFKA_DIR/sage-kafka-start.sh"
    
    # Wait for services to start
    sleep 5
    
    # Test Kafka
    if "$KAFKA_DIR/sage-kafka-status.sh" | grep -q "✅ Kafka: Running"; then
        print_success "Kafka is running successfully!"
        
        # Create a test topic
        "$KAFKA_DIR/bin/kafka-topics.sh" --create --topic sage-test --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 2>/dev/null || true
        
        # List topics to verify
        if "$KAFKA_DIR/bin/kafka-topics.sh" --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "sage-test"; then
            print_success "Test topic created successfully!"
            
            # Clean up test topic
            "$KAFKA_DIR/bin/kafka-topics.sh" --delete --topic sage-test --bootstrap-server localhost:9092 2>/dev/null || true
        fi
    else
        print_error "Kafka failed to start properly"
        return 1
    fi
}

function main() {
    echo "============================================"
    echo "         SAGE Kafka Installation"
    echo "============================================"
    
    # Check if system already has Kafka
    if check_system_kafka; then
        print_success "Kafka is already available on this system"
        print_status "SAGE will use the existing Kafka installation"
        print_status "Bootstrap servers: localhost:9092"
        return 0
    fi
    
    # Check Java
    check_java
    
    # Install Kafka
    download_kafka
    install_kafka
    configure_kafka
    create_management_scripts
    create_env_setup
    
    print_success "Kafka installation completed!"
    print_status "To use SAGE Kafka:"
    print_status "  1. Start: $KAFKA_DIR/sage-kafka-start.sh"
    print_status "  2. Stop:  $KAFKA_DIR/sage-kafka-stop.sh"
    print_status "  3. Status: $KAFKA_DIR/sage-kafka-status.sh"
    print_status "  4. Environment: source $THIRD_PARTY_DIR/kafka-env.sh"
    
    # Ask user if they want to test
    read -p "Do you want to test the Kafka installation now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_installation
    fi
    
    print_success "SAGE Kafka setup complete!"
}

# Run main function
main "$@"