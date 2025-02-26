# nginx/deploy.py
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

def deploy_archive(port=8080, rebuild=False):
    # Get paths relative to this script
    nginx_dir = Path(__file__).parent
    archive_path = (nginx_dir.parent / "archive").absolute()
    
    # Check if archive exists
    if not archive_path.exists():
        print("Error: 'archive' directory not found")
        return False

    container_name = "archived-site"

    # Stop and remove existing container if it exists
    run_command(f"podman rm -f {container_name} 2>/dev/null")

    # Build container if requested or if image doesn't exist
    if rebuild or not run_command(f"podman image exists {container_name}"):
        print("Building NGINX container...")
        if not run_command(f"podman build -t {container_name} -f {nginx_dir}/Containerfile {nginx_dir}"):
            return False

    # Run new container with volume mount
    cmd = f"podman run -d --name {container_name} -p {port}:80 -v {archive_path}:/usr/share/nginx/html:Z {container_name}"
    if run_command(cmd):
        print(f"\nWebsite deployed successfully!")
        print(f"Access at: http://localhost:{port}")
        print(f"\nArchive directory mounted: {archive_path}")
        print("You can update the archive contents without rebuilding the container")
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy archived website")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on (default: 8080)")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of container")
    args = parser.parse_args()
    
    if not deploy_archive(args.port, args.rebuild):
        sys.exit(1)