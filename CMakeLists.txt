cmake_minimum_required(VERSION 3.20)
project(gorf-port VERSION 0.1.0 LANGUAGES C CXX)   # version of the Gorf release packages

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
set(BB_PACKAGE_VERSION ${PROJECT_VERSION} CACHE STRING "" FORCE)
set(BB_PACKAGE_README ${CMAKE_CURRENT_SOURCE_DIR}/README.md CACHE FILEPATH "" FORCE)

# Put the executable at the top of the build folder.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

# ---- optional: recompiled code (breadbin-recomp, launcher docs/recomp.md) ------
# Off by default. Turned on, the build runs breadbin-recomp on YOUR Gorf dump and
# builds the generated C into the executable. That C is derived from the ROM, so such
# a build is for you only: it lives in the build folder, is never committed, and the
# launcher disables packaging for it.
option(GORF_RECOMP "Build in recompiled code generated from your own Gorf ROM (personal builds only)" OFF)
set(GORF_ROM "" CACHE FILEPATH "Your Gorf cartridge dump (.crt), needed by GORF_RECOMP")
if(GORF_RECOMP)
    set(GORF_RECOMP_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/breadbin-recomp)
    if(NOT EXISTS ${GORF_RECOMP_DIR}/CMakeLists.txt)
        message(FATAL_ERROR "The breadbin-recomp submodule is missing. Run:\n  git submodule update --init --recursive")
    endif()
    if(NOT GORF_ROM OR NOT EXISTS "${GORF_ROM}")
        message(FATAL_ERROR "GORF_RECOMP needs your ROM: -DGORF_ROM=/path/to/Gorf.crt")
    endif()
    # The generator is a host tool: build it on its own (no clash with the launcher's targets).
    include(ExternalProject)
    set(_tool_dir ${CMAKE_CURRENT_BINARY_DIR}/breadbin-recomp-tool)
    set(_tool ${_tool_dir}/bin/breadbin-recomp${CMAKE_EXECUTABLE_SUFFIX})
    ExternalProject_Add(gorf_recomp_tool
        SOURCE_DIR ${GORF_RECOMP_DIR}
        BINARY_DIR ${_tool_dir}
        CMAKE_ARGS -DCMAKE_BUILD_TYPE=Release -DRECOMP_BUILD_TESTS=OFF
                   -DCMAKE_RUNTIME_OUTPUT_DIRECTORY=${_tool_dir}/bin
                   -DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE=${_tool_dir}/bin
        BUILD_COMMAND ${CMAKE_COMMAND} --build ${_tool_dir} --config Release --target breadbin-recomp
        INSTALL_COMMAND ""
        BUILD_BYPRODUCTS ${_tool}
        BUILD_ALWAYS ON)
    # Fixed shard count, so the file list is known when configuring. The hints name
    # the dump's SHA-1: the generator refuses any other ROM, and the launcher runs the
    # code only on that exact cartridge data (not with patch mods).
    set(_gen ${CMAKE_CURRENT_BINARY_DIR}/generated)
    set(_shards 8)
    set(_outputs ${_gen}/program.c)
    math(EXPR _last "${_shards} - 1")
    foreach(i RANGE ${_last})
        string(LENGTH "${i}" _len)
        if(_len EQUAL 1)
            set(i "00${i}")
        elseif(_len EQUAL 2)
            set(i "0${i}")
        endif()
        list(APPEND _outputs ${_gen}/shard_${i}.c)
    endforeach()
    add_custom_command(OUTPUT ${_outputs}
        COMMAND ${_tool} gen "${GORF_ROM}" --hints ${CMAKE_CURRENT_SOURCE_DIR}/recomp/hints.toml
                --shards ${_shards} -o ${_gen}
        DEPENDS gorf_recomp_tool "${GORF_ROM}" ${CMAKE_CURRENT_SOURCE_DIR}/recomp/hints.toml
        COMMENT "Recompiling your Gorf ROM to C (breadbin-recomp)"
        VERBATIM)
    add_custom_target(gorf_recomp_generate DEPENDS ${_outputs})
    set(BB_RECOMP_SOURCES "${_outputs}" CACHE STRING "" FORCE)
    set(BB_RECOMP_INCLUDE ${GORF_RECOMP_DIR}/runtime CACHE PATH "" FORCE)
    set(BB_RECOMP_DEPENDS gorf_recomp_generate CACHE STRING "" FORCE)
    message(STATUS "Gorf: recompiled code from ${GORF_ROM} (personal build: don't distribute it)")
else()
    set(BB_RECOMP_SOURCES "" CACHE STRING "" FORCE)
    set(BB_RECOMP_DEPENDS "" CACHE STRING "" FORCE)
endif()

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
