#pragma once

#include <iostream>
#include <cassert>

#ifndef assertv

#ifndef USE_CASSERT
#define USE_CASSERT 0
#endif

#define assertv(e1, e2) \
    do { \
        if (USE_CASSERT) { \
            assert(e1 == e2); \
        } else { \
            if (!(e1 == e2)) { \
                std::cerr << "Assertion failed: " << #e1 << " == " << #e2 << \
                " (" << e1 << " == " << e2 << "), line " << __LINE__ << std::endl; \
            } \
        } \
    } while (0)

#endif