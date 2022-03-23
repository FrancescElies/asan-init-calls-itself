from pathlib import Path
import sys
from subprocess import check_output, run
import os

file_path = Path(__file__).absolute()
file_directory = file_path.parent
cwd = file_directory

def get_visualstudio_path():
    program_files = os.getenv("ProgramFiles(x86)")
    vswhere = fr"{program_files}\Microsoft Visual Studio\Installer\vswhere.exe"
    result = check_output((f'"{vswhere}" -latest -property installationPath'))
    return Path( result.decode(errors="ignore").strip())

visualstudio_path = get_visualstudio_path()

def find_msvc_clang_rt(libname):
    libpaths = list(visualstudio_path.rglob(libname))
    libpath = next(x for x in libpaths if "MSVC" in str(x))
    print(f"Selected {libpath=}")
    return libpath

clang_rt_libs = {x.name: x for x in visualstudio_path.rglob("*clang*.lib")}
llvm_path = Path(
    check_output("where clang").decode().splitlines()[0].strip()).parent.parent

def find_llvm_clang_rt(libname):
    libpath = next((llvm_path / "lib/clang/13.0.0/lib/windows").rglob(libname))
    assert libpath.exists(), f"{libpath} not found"
    print(f"Found {libpath}")
    return libpath

clang_rt_asan_thunk_lib = find_msvc_clang_rt("clang_rt.asan_dll_thunk-x86_64.lib")
clang_rt_asan_x86_64_lib = find_msvc_clang_rt("clang_rt.asan-x86_64.lib")
clang_rt_asan_cxx_x86_64_lib = find_msvc_clang_rt("clang_rt.asan_cxx-x86_64.lib")

cflags_base = " ".join((
    "--target=x86_64-pc-windows-msvc",
    # "-fuse-ld=lld",
    # "-Wno-cast-align",
    # "-fcomment-block-commands=retval",
    # "-ferror-limit=200",
    # "-fmessage-length=0",
    # "-fno-short-enums",
    # "-ffunction-sections",
    # "-fdata-sections",
    # "-std=c99",
))
strict_flags = "-Weverything -Werror -pedantic-errors"

cflags_windows = "-DWIN32 -D_WINDLL"

lib_cflags = " ".join((cflags_base, cflags_windows))

cc = llvm_path / 'bin/clang.exe'

 # Intentionally no using -fsanitize=address we link asan .lib manually
assan_flags = " ".join(("-g", "-gdwarf-4", "-O0", "-fno-omit-frame-pointer",
                        "-fno-optimize-sibling-calls"))

link_flags = ",".join([
    "-Wl",  # -Wl,<arg>               Pass the comma separated arguments in <arg> to the linker
    # lld-link --help to see possibilities
    # "/ignore:longsections",
    "/WX",  # Treat warnings as errors
])
sources = "mylib.c"
includes = f"-I{file_directory}"

def execute(cmd, cwd):
    print(f"{cwd=} running  {cmd=}")
    cmd_result = run(cmd, cwd=cwd, capture_output=True)
    if (cmd_result.returncode != 0):
        print(cmd_result.stdout)
        print(cmd_result.stderr)


cmd = (
    f'"{cc}" {lib_cflags} {strict_flags} {assan_flags} {includes} '
    f'-c {sources} -o mylib.o'
)
execute(cmd, cwd)


cmd = (
    f'"{cc}" {lib_cflags} {assan_flags} "{clang_rt_asan_thunk_lib}" mylib.o '
    '-shared -o mylib.dll')
execute(cmd, cwd)

py_file_run_c = "py_file_run.c"

clang_rt_asan_libs = (
    clang_rt_asan_x86_64_lib,
    clang_rt_asan_cxx_x86_64_lib,
)
assert all(x.exists() for x in clang_rt_asan_libs), (
    f"{[x for x in clang_rt_asan_libs if not x.exists()]} not found")

clang_rt_asan_libs_str = [f'"{x}"' for x in clang_rt_asan_libs]

python_dir = Path(sys.base_prefix)
python_include_dir = python_dir / "include"
print(f"Python include directory {python_include_dir}")
python_libs_dir = python_dir / "libs"
print(f"Python libs directory {python_libs_dir}")
py_file_run_link_flags = f"{link_flags},/wholearchive"

cmd = " ".join((
    f'"{cc}" {cflags_base} {cflags_windows} -Wno-everything '
    f'{assan_flags} ',
    f'{py_file_run_link_flags} ',
    f'-I{python_include_dir} ',
    f'-L {python_libs_dir} ',
    # The EXE needs to have clang_rt.asan-x86_64.lib linked
    f' {" ".join([x for x in clang_rt_asan_libs_str])} '
    ' py_file_run.c -o py_file_run.exe',

))
execute(cmd, cwd)
