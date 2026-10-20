// Clean C++ test fixture (Phase 6 verification)
#include <iostream>
#include <string>
#include <memory>
#include <vector>

void process_data(const std::string& input, int total_elements) {
    // Bounds check and guarded division (CWE-369 safe)
    double average = (total_elements > 0) ? (100.0 / total_elements) : 0.0;
    std::cout << "Average: " << average << std::endl;

    // Safe memory management via smart pointers (CWE-401 safe)
    auto buffer = std::make_unique<std::vector<int>>();
    buffer->push_back(42);

    // Safe string manipulation
    std::string safe_copy = input;
    std::cout << "Payload length: " << safe_copy.length() << std::endl;
}

int main() {
    process_data("hello", 5);
    return 0;
}
