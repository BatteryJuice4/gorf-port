cmake_minimum_required(VERSION 3.20)
project(gorf-port LANGUAGES C CXX)

# Gorf, built as a branded Breadbin-6502 executable with the game pack embedded.
# The launcher is a git submodule pinned to a tagged release.

set(GORF_GAMEPACK_DIR ${CMAKE_CURRENT_SOURCE_DIR}/gamepacks/gorf)
set(GORF_LAUNCHER_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/breadbin-6502)

if(NOT EXISTS ${GORF_LAUNCHER_DIR}/CMakeLists.txt)
    message(FATAL_ERROR "The launcher submodule is missing. Run:\n  git submodule update --init --recursive")
endif()

# Launcher options for a branded build.
set(BB_GAMEPACK_DIR ${GORF_GAMEPACK_DIR} CACHE PATH "" FORCE)
set(BB_OUTPUT_NAME "gorf" CACHE STRING "" FORCE)
set(BB_BUILD_TESTS OFF CACHE BOOL "" FORCE)

# Put the executable at the top of the build folder.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

add_subdirectory(${GORF_LAUNCHER_DIR} breadbin-6502)

# Refuse to build against a launcher older than the game pack requires.
get_directory_property(GORF_LAUNCHER_VERSION DIRECTORY ${GORF_LAUNCHER_DIR} DEFINITION breadbin-6502_VERSION)
file(READ ${GORF_GAMEPACK_DIR}/game.toml GORF_TOML)
string(REGEX MATCH "min_launcher_version[ \t]*=[ \t]*\"([0-9.]+)\"" _ "${GORF_TOML}")
set(GORF_MIN_LAUNCHER "${CMAKE_MATCH_1}")
if(NOT GORF_LAUNCHER_VERSION)
    message(FATAL_ERROR "Can't read the launcher version from the submodule")
endif()
if(GORF_MIN_LAUNCHER AND GORF_LAUNCHER_VERSION VERSION_LESS GORF_MIN_LAUNCHER)
    message(FATAL_ERROR "game.toml needs Breadbin-6502 ${GORF_MIN_LAUNCHER} or newer, "
                        "but the submodule is ${GORF_LAUNCHER_VERSION}.")
endif()
message(STATUS "Gorf: Breadbin-6502 ${GORF_LAUNCHER_VERSION} (game pack needs >= ${GORF_MIN_LAUNCHER})")

# ---- tests (pack validation; no ROMs needed) ---------------------------------
option(GORF_BUILD_TESTS "Build the game pack tests" ON)
if(GORF_BUILD_TESTS)
    enable_testing()
    add_executable(test_gorf_pack tests/test_gorf_pack.c)
    target_link_libraries(test_gorf_pack PRIVATE bb_core)
    target_compile_definitions(test_gorf_pack PRIVATE GORF_PINNED_LAUNCHER="${GORF_LAUNCHER_VERSION}")
    set_target_properties(test_gorf_pack PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
    if(NOT MSVC)
        target_compile_options(test_gorf_pack PRIVATE -Wall -Wextra)
    endif()
    add_test(NAME gorf_pack COMMAND test_gorf_pack ${GORF_GAMEPACK_DIR}/game.toml)
endif()
