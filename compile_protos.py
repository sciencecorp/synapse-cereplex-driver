import os
import subprocess
import glob
import shutil

PROJECT_NAME = "synapsectl"
PROTOC = "python -m grpc_tools.protoc"
PROTO_DIR = os.path.abspath("./synapse-api")
PROTO_OUT = os.path.abspath("./synapse/generated")
BIN_DIR = os.path.abspath("./bin")
DESCRIPTOR_FILE = os.path.join(BIN_DIR, "descriptors.binpb")

def run_command(command):
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    print("Command executed successfully")
    return True

def get_proto_files():
    return [os.path.relpath(p, PROTO_DIR).replace("\\", "/") 
            for p in glob.glob(os.path.join(PROTO_DIR, "**", "*.proto"), recursive=True)]

def clean():
    print(f"Cleaning {BIN_DIR} and {PROTO_OUT}")
    shutil.rmtree(BIN_DIR, ignore_errors=True)
    shutil.rmtree(PROTO_OUT, ignore_errors=True)

def generate():
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(PROTO_OUT, exist_ok=True)

    proto_files = get_proto_files()
    if not proto_files:
        print(f"No .proto files found in {PROTO_DIR}")
        return False

    proto_files_str = " ".join(proto_files)

    commands = [
        f"{PROTOC} -I={PROTO_DIR.replace('\\', '/')} --descriptor_set_out={DESCRIPTOR_FILE.replace('\\', '/')} {proto_files_str}",
        f"{PROTOC} -I={PROTO_DIR.replace('\\', '/')} --python_out={PROTO_OUT.replace('\\', '/')} {proto_files_str}",
        f"{PROTOC} -I={PROTO_DIR.replace('\\', '/')} --grpc_python_out={PROTO_OUT.replace('\\', '/')} api/synapse.proto",
        f"protol --create-package --in-place --python-out {PROTO_OUT.replace('\\', '/')} raw {DESCRIPTOR_FILE.replace('\\', '/')}"
    ]

    for command in commands:
        if not run_command(command):
            return False

    return True

def main():
    print(f"Project: {PROJECT_NAME}")
    print(f"Proto directory: {PROTO_DIR}")
    print(f"Output directory: {PROTO_OUT}")

    clean()
    if generate():
        print("All proto compilation steps completed successfully.")
    else:
        print("Proto compilation failed.")

if __name__ == "__main__":
    main()