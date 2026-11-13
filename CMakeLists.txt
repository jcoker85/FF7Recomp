cmake_minimum_required(VERSION 3.20)
project(FF7Recomp LANGUAGES C)

# The game is its own CMake project under games/ff7: the recompiled game code is
# linked into the executable, and the framework's build expects one game per
# CMake project. This top-level project builds it into <build>/ff7/.
include(ExternalProject)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(_ff7_cxx_arg)
if(CMAKE_CXX_COMPILER)
    set(_ff7_cxx_arg "-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}")
elseif(CMAKE_C_COMPILER MATCHES "clang(\\.exe)?$")
    string(REGEX REPLACE "clang(\\.exe)?$" "clang++\\1" _ff7_cxx "${CMAKE_C_COMPILER}")
    set(_ff7_cxx_arg "-DCMAKE_CXX_COMPILER=${_ff7_cxx}")
endif()

# The recompiled C is generated from your own disc and is not part of the
# repository.
file(GLOB _ff7_generated "${CMAKE_CURRENT_SOURCE_DIR}/games/ff7/generated/*.c")
if(NOT _ff7_generated)
    message(FATAL_ERROR "No recompiled code in games/ff7/generated. Generate it first:\n"
                        "  tools/generate.sh \"/path/to/Final Fantasy VII - Disc 1.chd\"")
endif()

ExternalProject_Add(ff7
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/games/ff7"
    BINARY_DIR "${CMAKE_BINARY_DIR}/ff7"
    CMAKE_ARGS
        "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}"
        "-DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}"
        ${_ff7_cxx_arg}
    BUILD_COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target psx-runtime
    INSTALL_COMMAND ""
    BUILD_ALWAYS ON
    USES_TERMINAL_CONFIGURE ON
    USES_TERMINAL_BUILD ON)

# The hub menu (hub/hub.c, ported from TwistedMetal1234Recomp): a cover-shaped
# window with Play (straight into the game) and Settings (the game's launcher).
# It lists the games in games.txt beside it: Title|Subtitle|exe|cover name.
# The cover is not shipped; the hub downloads it from libretro-thumbnails on
# first run, by that name.
file(WRITE "${CMAKE_BINARY_DIR}/games.txt"
     "# Title|Subtitle|executable relative to this file|cover name\n"
     "Final Fantasy VII|1997  -  Square|ff7/FinalFantasyVII_Recompiled.exe|Final Fantasy VII (USA) (Disc 1)\n")
if(WIN32)
    # No icon is built in: the hub downloads it on its first start (hub.c,
    # fetch_icon); it is not ours to redistribute.
    add_executable(FF7Recomp WIN32 hub/hub.c)
    target_compile_definitions(FF7Recomp PRIVATE UNICODE _UNICODE)
    target_link_options(FF7Recomp PRIVATE -municode -static)
    target_link_libraries(FF7Recomp PRIVATE gdiplus msimg32 urlmon)
else()
    message(STATUS "The hub menu is Windows-only; start the game from <build>/ff7.")
endif()
