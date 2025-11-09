import os
import shutil
import subprocess
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop

SERVER_REPO = "https://github.com/dkmaker/mcp-rest-api.git"
SERVER_DIR = "mcp-rest-api"
PACKAGE_DIR = "deepagents_cli"
BIN_DIR = os.path.join(PACKAGE_DIR, "bin")

def build_and_copy_server():
    """Clone, build, and copy the mcp-rest-api server."""
    print("Cloning mcp-rest-api server...")
    if not os.path.exists(SERVER_DIR):
        subprocess.check_call(["git", "clone", SERVER_REPO, SERVER_DIR])

    print("Building mcp-rest-api server...")
    subprocess.check_call(["make", "build"], cwd=SERVER_DIR)

    print("Copying server executable...")
    os.makedirs(BIN_DIR, exist_ok=True)
    src = os.path.join(SERVER_DIR, "mcp_server")
    dst = os.path.join(BIN_DIR, "mcp_server")
    shutil.copy(src, dst)
    os.chmod(dst, 0o755)

class CustomBuildPy(build_py):
    def run(self):
        if not self.dry_run:
            build_and_copy_server()
        super().run()

class CustomDevelop(develop):
    def run(self):
        build_and_copy_server()
        super().run()

setup(
    cmdclass={
        'build_py': CustomBuildPy,
        'develop': CustomDevelop,
    }
)
