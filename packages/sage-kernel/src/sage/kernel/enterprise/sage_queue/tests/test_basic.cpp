#include <iostream>
#include <dlfcn.h>
#include "ring_buffer.h"

int main() {
    std::cout << "Testing SAGE Queue library..." << std::endl;
    
    // Try to load the library dynamically to verify it's built correctly
    void* handle = dlopen("./libring_buffer.so", RTLD_LAZY);
    if (!handle) {
        std::cerr << "Error: Cannot load library: " << dlerror() << std::endl;
        return 1;
    }
    
    std::cout << "✓ Library loaded successfully" << std::endl;
    
    dlclose(handle);
    
    std::cout << "✓ All tests passed" << std::endl;
    return 0;
}
