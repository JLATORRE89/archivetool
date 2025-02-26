import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

def check_container_exists(container_name):
    result = subprocess.run(
        f"podman ps -a --format '{{{{.Names}}}}' | grep '^{container_name}$'",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def deploy_archiver(port=8000, data_dir=None, rebuild=False, clean=False):
    # Get paths
    project_dir = Path(__file__).parent
    data_path = Path(data_dir).absolute() if data_dir else project_dir / "data"
    
    # Ensure data directory exists
    data_path.mkdir(parents=True, exist_ok=True)

    container_name = "website-archiver"

    # Check if container exists
    if check_container_exists(container_name):
        if clean:
            print(f"Removing existing container {container_name}...")
            run_command(f"podman rm -f {container_name}")
        else:
            print(f"Container {container_name} already exists. Use --clean to remove it.")
            return False

    # Build container if requested or if image doesn't exist
    if rebuild or not run_command(f"podman image exists {container_name}"):
        print("Building archiver container...")
        if not run_command(f"podman build -t {container_name} -f Containerfile ."):
            return False

    # Run the container
    cmd = f"podman run -d --name {container_name} -v {data_path}:/data:Z -p {port}:8000 {container_name} cli"
    
    if run_command(cmd):
        print(f"\nArchiver container deployed successfully!")
        print(f"\nData directory: {data_path}")
        print("\nTo archive a website:")
        print(f"podman exec {container_name} python -m archiver.cli URL -o /data/archive")
        print("\nExample:")
        print(f"podman exec {container_name} python -m archiver.cli https://example.com -o /data/archive")
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy CLI website archiver container")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--data-dir", help="Data directory (default: ./data)")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of container")
    parser.add_argument("--clean", action="store_true", help="Remove existing container if it exists")
    args = parser.parse_args()
    
    if not deploy_archiver(args.port, args.data_dir, args.rebuild, args.clean):
        sys.exit(1)