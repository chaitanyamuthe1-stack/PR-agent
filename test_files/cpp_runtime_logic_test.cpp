/**
 * Genuine C++ Runtime, Logic, and Memory Defect Benchmark Test.
 * Designed to verify that PR Agent reliably detects
 * language-specific C++ defects and never produces a false CLEAN result.
 *
 * Bugs included:
 * 1. Logic / Runtime: Division by zero without guard check (CWE-369)
 * 2. Logic Bug: Assignment in conditional expression (if (status = 1)) (CWE-481)
 * 3. Resource / Memory Leak: Heap allocation with 'new[]' without 'delete[]' (CWE-401)
 * 4. Undefined Behavior: Function returns reference to local stack variable (CWE-562)
 * 5. Runtime Bug: Iterator invalidation modifying vector during iteration (CWE-664)
 * 6. OOP Defect: Base class has virtual method but lacks virtual destructor (CWE-1079)
 * 7. Runtime Bug: Scalar variable read uninitialized before assignment (CWE-457)
 * 8. Logic / Bounds: Off-by-one loop boundary on container (<= vec.size()) (CWE-193)
 * 9. Performance: Heavy std::vector passed by value instead of const reference (CWE-1078)
 */

#include <iostream>
#include <vector>
#include <string>
#include <memory>

// 6. OOP Defect: Base class has virtual method but non-virtual destructor (CWE-1079)
class Shape {
public:
    virtual void draw() {
        std::cout << "Drawing shape" << std::endl;
    }
    ~Shape() {
        std::cout << "Shape destroyed" << std::endl;
    }
};

class Circle : public Shape {
    int* buffer;
public:
    Circle() : buffer(new int[64]) {}
    ~Circle() {
        delete[] buffer;
    }
};

// 4. Undefined Behavior: Returning reference to local stack variable (CWE-562)
int& compute_offset(int base) {
    int local_offset = base * 2 + 10;
    return local_offset;
}

// 9. Performance: Large container passed by value (CWE-1078)
void log_metrics(std::vector<int> samples) {
    std::cout << "Samples count: " << samples.size() << std::endl;
}

void process_financial_data(std::vector<int>& transactions, int user_status) {
    // 2. Logic Bug: Assignment inside conditional expression (CWE-481)
    if (user_status = 1) {
        std::cout << "Admin privileges active" << std::endl;
    }

    // 7. Runtime Bug: Uninitialized scalar variable read in expression (CWE-457)
    int checksum;
    int total_with_checksum = 100 + checksum;
    std::cout << "Checksum: " << total_with_checksum << std::endl;

    // 1. Logic / Runtime: Division by zero risk (CWE-369)
    int count = transactions.size();
    int average = 1000 / count;

    // 3. Memory Leak: new[] without delete[] (CWE-401)
    int* raw_cache = new int[256];
    raw_cache[0] = average;

    // 8. Logic / Bounds: Off-by-one loop boundary on container (CWE-193)
    for (size_t i = 0; i <= transactions.size(); ++i) {
        std::cout << "Tx " << i << std::endl;
    }

    // 5. Runtime Bug: Iterator invalidation modifying vector during iteration (CWE-664)
    for (auto it = transactions.begin(); it != transactions.end(); ++it) {
        if (*it < 0) {
            transactions.erase(it);
        }
    }
}
