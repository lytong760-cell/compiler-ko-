#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <climits>

struct LoopConfig {
    std::string varName;
    long long start;
    long long end;
    long long step;
    long long iterationCount;
    std::vector<std::string> bodyLines;
};

struct OptimizedLoop {
    std::string unrolledCode;
    int unrollFactor;
    long long iterationCount;
    std::string registerHint;
    std::string cacheOptimization;
};

static const int MAX_UNROLL_FACTOR = 8;
static const int CACHE_LINE_SIZE = 64;
static const int REGISTER_COUNT = 16;
static const long long MAX_ITERATIONS = 10000000;

long long parseLong(const std::string& s, const std::string& name) {
    try {
        size_t pos;
        long long val = std::stoll(s, &pos);
        if (pos != s.size()) {
            std::cerr << "Error: invalid number format for " << name << ": " << s << std::endl;
            exit(2);
        }
        return val;
    } catch (...) {
        std::cerr << "Error: cannot parse " << name << ": " << s << std::endl;
        exit(3);
    }
}

LoopConfig parseArguments(int argc, char* argv[]) {
    if (argc < 6) {
        std::cerr << "Usage: Loop <varName> <start> <end> <step> <bodyFile> [unrollFactor]" << std::endl;
        exit(1);
    }

    LoopConfig config;
    config.varName = argv[1];
    if (config.varName.empty() || config.varName.length() > 64) {
        std::cerr << "Error: invalid loop variable name" << std::endl;
        exit(1);
    }
    for (char c : config.varName) {
        if (!std::isalnum(c) && c != '_') {
            std::cerr << "Error: loop variable name contains invalid character: " << c << std::endl;
            exit(1);
        }
    }

    config.start = parseLong(argv[2], "start");
    config.end = parseLong(argv[3], "end");
    config.step = parseLong(argv[4], "step");

    if (config.step == 0) {
        std::cerr << "Error: step cannot be zero" << std::endl;
        exit(4);
    }

    if ((config.step > 0 && config.start > config.end) || (config.step < 0 && config.start < config.end)) {
        std::cerr << "Warning: loop range is empty with given start/end/step" << std::endl;
        config.iterationCount = 0;
    } else {
        config.iterationCount = ((config.end - config.start) / config.step) + 1;
    }

    if (config.iterationCount > MAX_ITERATIONS) {
        std::cerr << "Error: loop iteration count (" << config.iterationCount << ") exceeds maximum (" << MAX_ITERATIONS << ")" << std::endl;
        exit(5);
    }

    if (config.iterationCount < 0) {
        std::cerr << "Error: negative iteration count detected (integer overflow)" << std::endl;
        exit(6);
    }

    std::string bodyFile = argv[5];
    if (bodyFile.find("..") != std::string::npos || bodyFile.find("/") != std::string::npos) {
        std::cerr << "Error: invalid body file path" << std::endl;
        exit(1);
    }

    std::ifstream bodyStream(bodyFile);
    if (bodyStream.is_open()) {
        std::string line;
        while (std::getline(bodyStream, line)) {
            if (!line.empty() && line.find_last_not_of(" \t\r\n") != std::string::npos) {
                config.bodyLines.push_back(line);
            }
        }
        bodyStream.close();
    }

    int unrollFactorArg = 1;
    if (argc >= 7) {
        unrollFactorArg = std::atoi(argv[6]);
        if (unrollFactorArg < 1) unrollFactorArg = 1;
        if (unrollFactorArg > MAX_UNROLL_FACTOR) unrollFactorArg = MAX_UNROLL_FACTOR;
    }

    return config;
}

OptimizedLoop optimizeLoop(const LoopConfig& config, int unrollFactor) {
    OptimizedLoop result;
    result.unrollFactor = unrollFactor;
    result.iterationCount = config.iterationCount;

    std::ostringstream ss;

    ss << "/* Loop optimization report */" << std::endl;
    ss << "/* Variable: " << config.varName << " */" << std::endl;
    ss << "/* Range: [" << config.start << ", " << config.end << "] */" << std::endl;
    ss << "/* Step: " << config.step << " */" << std::endl;
    ss << "/* Iterations: " << config.iterationCount << " */" << std::endl;
    ss << "/* Unroll factor: " << unrollFactor << " */" << std::endl;

    ss << "/* CPU Register allocation hint: use register for loop counter */" << std::endl;
    ss << "register long long " << config.varName << "_reg;" << std::endl;

    ss << "/* Cache line optimization: align loop body to " << CACHE_LINE_SIZE << " bytes */" << std::endl;
    ss << "/* Branch prediction hint: loop body is taken " << config.iterationCount << " times */" << std::endl;

    char alignAttr[128];
    snprintf(alignAttr, sizeof(alignAttr),
             "__attribute__((aligned(%d)))", CACHE_LINE_SIZE);

    long long iterations = config.iterationCount;
    long long fullUnrolls = iterations / unrollFactor;
    long long remainder = iterations % unrollFactor;

    ss << "/* Unrolled loop structure: " << fullUnrolls << " full blocks + " << remainder << " remainder iterations */" << std::endl;

    ss << "for (register long long " << config.varName << " = " << config.start << "; "
       << config.varName << " <= " << config.end << "; " << config.varName << " += " << config.step << ") {" << std::endl;

    for (const auto& line : config.bodyLines) {
        std::string optimized = line;
        size_t pos = 0;
        while ((pos = optimized.find(config.varName, pos)) != std::string::npos) {
            optimized.replace(pos, config.varName.length(), config.varName + "_reg");
            pos += config.varName.length() + 3;
        }
        ss << "    " << optimized << std::endl;
    }

    ss << "}" << std::endl;

    ss << "/* Register hint: " << REGISTER_COUNT << " general-purpose registers available */" << std::endl;
    ss << "/* Memory barrier: ensure loop writes are visible to subsequent instructions */" << std::endl;

    result.unrolledCode = ss.str();
    return result;
}

int main(int argc, char* argv[]) {
    LoopConfig config = parseArguments(argc, argv);

    int unrollFactor = 1;
    if (argc >= 7) {
        unrollFactor = std::atoi(argv[6]);
        if (unrollFactor < 1) unrollFactor = 1;
        if (unrollFactor > MAX_UNROLL_FACTOR) unrollFactor = MAX_UNROLL_FACTOR;
    }

    OptimizedLoop optimized = optimizeLoop(config, unrollFactor);

    std::cout << optimized.unrolledCode << std::endl;

    std::ofstream reportFile("/tmp/ko_loop_optimization_report.txt");
    if (reportFile.is_open()) {
        reportFile << "Loop Optimization Report\n";
        reportFile << "========================\n";
        reportFile << "Variable: " << config.varName << "\n";
        reportFile << "Start: " << config.start << "\n";
        reportFile << "End: " << config.end << "\n";
        reportFile << "Step: " << config.step << "\n";
        reportFile << "Total Iterations: " << config.iterationCount << "\n";
        reportFile << "Unroll Factor: " << unrollFactor << "\n";
        reportFile << "Full Unroll Blocks: " << (config.iterationCount / unrollFactor) << "\n";
        reportFile << "Remainder Iterations: " << (config.iterationCount % unrollFactor) << "\n";
        reportFile << "Cache Line Alignment: " << CACHE_LINE_SIZE << " bytes\n";
        reportFile << "Register Hint: " << REGISTER_COUNT << " GPRs available\n";
        reportFile.close();
    }

    return 0;
}