/*
 * Assertion macro that does not abort the program, but prints a message to
 * std::cerr instead.
 */

#pragma once

#include <cassert>
#include <iostream>

#ifndef assertv

#ifndef USE_CASSERT
#define USE_CASSERT 0
#endif

#define assertv(e1, e2)                                                   \
    do {                                                                  \
        if (USE_CASSERT) {                                                \
            assert(e1 == e2);                                             \
        } else {                                                          \
            if (!(e1 == e2)) {                                            \
                std::cerr << "Assertion failed: " << #e1 << " == " << #e2 \
                          << " (" << e1 << " == " << e2 << "), line "     \
                          << __LINE__ << std::endl;                       \
            }                                                             \
        }                                                                 \
    } while (0)

#endif
