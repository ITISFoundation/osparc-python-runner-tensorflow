import logging
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("osparc-python-main")


ENVIRONS = ["INPUT_FOLDER", "OUTPUT_FOLDER"]
input_dir, output_dir = [Path(os.environ.get(v, None)) for v in ENVIRONS]

# TODO: sync with schema in metadata!!
OUTPUT_FILE = "output_data.zip"

FILE_DIR = os.path.realpath(__file__)


def copy(src, dest):
    try:
        src, dest = str(src), str(dest)
        shutil.copytree(
            src, dest, ignore=shutil.ignore_patterns("*.zip", "__pycache__", ".*")
        )
    except OSError as err:
        # If the error was caused because the source wasn't a directory
        if err.errno == shutil.errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            logger.error("Directory not copied. Error: %s", err)


def clean_dir(dirpath: Path):
    for root, dirs, files in os.walk(dirpath):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


def run_cmd(cmd: str):
    subprocess.run(cmd.split(), shell=False, check=True, cwd=input_dir)
    # TODO: deal with stdout, log? and error??


def unzip_dir(parent: Path):
    for filepath in list(parent.rglob("*.zip")):
        if zipfile.is_zipfile(filepath):
            with zipfile.ZipFile(filepath) as zf:
                zf.extractall(filepath.parent)


def zipdir(dirpath: Path, ziph: zipfile.ZipFile):
    """Zips directory and archives files relative to dirpath"""
    for root, dirs, files in os.walk(dirpath):
        for filename in files:
            filepath = os.path.join(root, filename)
            ziph.write(filepath, arcname=os.path.relpath(filepath, dirpath))
        dirs[:] = [name for name in dirs if not name.startswith(".")]


def ensure_main_entrypoint(code_dir: Path) -> Path:
    code_files = list(code_dir.rglob("*.py"))

    if not code_files:
        raise ValueError("No python code found")

    if len(code_files) > 1:
        code_files = list(code_dir.rglob("main.py"))
        if not code_files:
            raise ValueError("No entrypoint found (e.g. main.py)")
        if len(code_files) > 1:
            raise ValueError(f"Many entrypoints found: {code_files}")

    main_py = code_files[0]
    return main_py


def ensure_requirements(code_dir: Path) -> Path:
    requirements = list(code_dir.rglob("requirements.txt"))
    if len(requirements) > 1:
        raise ValueError(f"Many requirements found: {requirements}")

    elif not requirements:
        # deduce requirements using pipreqs
        logger.info("Not found. Recreating requirements ...")
        requirements = code_dir / "requirements.txt"
        run_cmd(f"pipreqs --savepath={requirements} --force {code_dir}")

    else:
        requirements = requirements[0]

    # we want to make sure that no already installed libraries are being touched

    # the requirements file of this service
    runner_requirements = Path(FILE_DIR).parent / "requirements.txt"

    # this will be the one from the user augmented by a constraint to the runner one
    requirements_in = code_dir / "requirements.in"

    # tmp file for creating the new one
    tmp_requirements = code_dir / "requirements.tmp"

    with open(requirements, "r") as f:
        with open(tmp_requirements, "w") as f2:
            f2.write(f"-c {runner_requirements}\n")
            f2.write(f.read())

    os.rename(tmp_requirements, requirements_in)

    return Path(requirements_in)


def setup():
    logger.info("Cleaning output ...")
    clean_dir(output_dir)

    # TODO: snapshot_before = list(input_dir.rglob("*"))

    # NOTE The inputs defined in ${INPUT_FOLDER}/inputs.json are available as env variables by their key in capital letters
    # For example: input_1 -> $INPUT_1
    #

    logger.info("Processing input ...")
    unzip_dir(input_dir)

    # logger.info("Copying input to output ...")
    # copy(input_dir, code_dir)

    logger.info("Searching main entrypoint ...")
    main_py = ensure_main_entrypoint(input_dir)
    logger.info("Found %s as main entrypoint", main_py)

    logger.info("Searching requirements ...")
    logger.info(input_dir)
    requirements_in = ensure_requirements(input_dir)

    requirements = requirements_in.parent / "requirements.compiled"

    logger.info("Preparing launch script ...")
    venv_dir = Path.home() / ".venv"
    script = [
        "#!/bin/sh",
        "set -o errexit",
        "set -o nounset",
        "IFS=$(printf '\\n\\t')",
        f"echo compiling {requirements_in} into {requirements} ...",
        f"pip-compile --upgrade --build-isolation --output-file {requirements} {requirements_in}",
        'echo "Creating virtual environment ..."',
        f"python3 -m venv --system-site-packages --symlinks --upgrade {venv_dir}",
        f"{venv_dir}/bin/pip install -U pip wheel setuptools",
        f"{venv_dir}/bin/pip install -r {requirements}",
        f'echo "Executing code {main_py.name}..."',
        f"{venv_dir}/bin/python3 {main_py}",
        'echo "DONE ..."',
    ]
    main_script_path = Path("main.sh")
    with main_script_path.open("w") as fp:
        for line in script:
            print(f"{line}\n", file=fp)

    # # TODO: take snapshot
    # logger.info("Creating virtual environment ...")
    # run_cmd("python3 -m venv --system-site-packages --symlinks --upgrade .venv")
    # run_cmd(".venv/bin/pip install -U pip wheel setuptools")
    # run_cmd(f".venv/bin/pip install -r {requirements}")

    # # TODO: take snapshot
    # logger.info("Executing code ...")
    # run_cmd(f".venv/bin/python3 {main_py}")


def teardown():
    logger.info("Zipping output ....")

    # TODO: sync zipped name with docker/labels/outputs.json
    with tempfile.TemporaryDirectory() as tmpdir:
        zipped_file = Path(f"{tmpdir}/{OUTPUT_FILE}")
        with zipfile.ZipFile(str(zipped_file), "w", zipfile.ZIP_DEFLATED) as zh:
            zipdir(output_dir, zh)

        logger.info("Cleaning output")
        clean_dir(output_dir)

        logger.info("Moving %s", zipped_file.name)
        shutil.move(str(zipped_file), str(output_dir))


if __name__ == "__main__":
    action = "setup" if len(sys.argv) == 1 else sys.argv[1]
    try:
        if action == "setup":
            setup()
        else:
            teardown()
    except Exception as err:  # pylint: disable=broad-except
        logger.error("%s . Stopping %s", err, action)
