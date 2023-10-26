import os
import platform
import subprocess
import warnings
from pathlib import Path
from typing import List

def verify_ffistan_path(path: str) -> None:
    folder = Path(path).resolve()
    if not folder.exists():
        raise ValueError(
            f"Ffistan folder '{folder}' does not exist!\n"
            "If you need to set a different location, call 'set_ffistan_path()'"
        )
    makefile = folder / "Makefile"
    if not makefile.exists():
        raise ValueError(
            f"Ffistan folder '{folder}' does not "
            "contain file 'Makefile', please ensure it is built properly!\n"
            "If you need to set a different location, call 'set_ffistan_path()'"
        )


IS_WINDOWS = platform.system() == "Windows"
WINDOWS_PATH_SET = False

PYTHON_FOLDER = Path(__file__).parent.parent

MAKE = os.getenv(
    "MAKE",
    "make" if not IS_WINDOWS else "mingw32-make",
)


def set_ffistan_path(path: str) -> None:
    """Set the path to Ffistan.

    This should point to the top-level folder of the repository.

    By default this is set to the value of the environment
    variable ``FFISTAN``, or to the folder above the location
    of this package (which, assuming a source installation, corresponds
    to the repository root).
    """
    path = os.path.abspath(path)
    verify_ffistan_path(path)
    os.environ["FFISTAN"] = path


def get_ffistan_path():
    path = os.getenv("FFISTAN", "")
    # todo downloading
    # if path == "":
    #     try:
    #         path = str(CURRENT_FFISTAN)
    #         verify_ffistan_path(path)
    #     except ValueError:
    #         print(
    #             "Ffistan not found at location specified by $FFISTAN "
    #             f"environment variable, downloading version {__version__} to {path}"
    #         )
    #         get_ffistan_src()
    #         num_files = len(list(HOME_FFISTAN.iterdir()))
    #         if num_files >= 5:
    #             warnings.warn(
    #                 f"Found {num_files} different versions of Ffistan in {HOME_FFISTAN}. "
    #                 "Consider deleting old versions to save space."
    #             )
    #         print("Done!")

    return path


def generate_so_name(model: Path):
    name = model.stem
    return model.with_stem(f"{name}_model").with_suffix(".so")


def compile_model(
    stan_file: str, *, stanc_args: List[str] = [], make_args: List[str] = []
) -> Path:
    """
    Run FFIStan's Makefile on a ``.stan`` file, creating the ``.so``
    used by the StanModel class.

    This function assumes that the path to FFIStan is valid.
    This can be set with :func:`set_ffistan_path`.

    :param stan_file: A path to a Stan model file.
    :param stanc_args: A list of arguments to pass to stanc3.
        For example, ``["--O1"]`` will enable compiler optimization level 1.
    :param make_args: A list of additional arguments to pass to Make.
        For example, ``["STAN_THREADS=True"]`` will enable
        threading for the compiled model. If the same flags are defined
        in ``make/local``, the versions passed here will take precedent.
    :raises FileNotFoundError or PermissionError: If `stan_file` does not exist
        or is not readable.
    :raises ValueError: If FFIStan cannot be located.
    :raises RuntimeError: If compilation fails.
    """
    verify_ffistan_path(get_ffistan_path())
    file_path = Path(stan_file).resolve()
    if file_path.suffix != ".stan":
        raise ValueError(f"File '{stan_file}' does not end in .stan")

    stanc_args
    output = generate_so_name(file_path)
    cmd = (
        [MAKE]
        + make_args
        + ["STANCFLAGS=" + " ".join(["--include-paths=."] + stanc_args)]
        + [str(output)]
    )
    proc = subprocess.run(
        cmd, cwd=get_ffistan_path(), capture_output=True, text=True, check=False
    )

    if proc.returncode:
        error = (
            f"Command {' '.join(cmd)} failed with code {proc.returncode}.\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

        raise RuntimeError(error)
    return output


def windows_dll_path_setup():
    """Add tbb.dll to %PATH% on Windows."""
    global WINDOWS_PATH_SET
    if IS_WINDOWS and not WINDOWS_PATH_SET:
        try:
            out = subprocess.run(
                ["where.exe", "tbb.dll"], check=True, capture_output=True
            )
            tbb_path = os.path.dirname(out.stdout.decode().splitlines()[0])
            os.add_dll_directory(tbb_path)
        except:
            try:
                tbb_path = os.path.abspath(
                    os.path.join(
                        get_ffistan_path(), "stan", "lib", "stan_math", "lib", "tbb"
                    )
                )
                os.environ["PATH"] = tbb_path + ";" + os.environ["PATH"]
                os.add_dll_directory(tbb_path)
                WINDOWS_PATH_SET = True
            except:
                warnings.warn(
                    "Unable to set path to TBB's DLL. Loading FFIStan models may fail. "
                    f"Tried path '{tbb_path}'",
                    RuntimeWarning,
                )
                WINDOWS_PATH_SET = False
        try:
            out = subprocess.run(
                [
                    "where.exe",
                    "libwinpthread-1.dll",
                    "libgcc_s_seh-1.dll",
                    "libstdc++-6.dll",
                ],
                check=True,
                capture_output=True,
            )
            mingw_dir = os.path.abspath(
                os.path.dirname(out.stdout.decode().splitlines()[0])
            )
            os.add_dll_directory(mingw_dir)
            WINDOWS_PATH_SET &= True
        except:
            # no default location
            warnings.warn(
                "Unable to find MinGW's DLL location. Loading FFIStan models may fail.",
                RuntimeWarning,
            )
            WINDOWS_PATH_SET = False
