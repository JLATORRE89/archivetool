# archiver/cli.py
import argparse
import sys
import time
from archiver.core import WebsiteArchiver
import signal
import os

def signal_handler(signum, frame):
    print("\nStopping archive...")
    global archiver
    if archiver:
        archiver.active = False

def progress_callback(count, current_url):
    sys.stdout.write(f"\rPages archived: {count} | Current: {current_url[:50]}{'...' if len(current_url) > 50 else ''}")
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Website Archiver CLI")
    parser.add_argument("url", help="URL of the website to archive")
    parser.add_argument("-o", "--output", help="Output directory for the archive", default=None)
    parser.add_argument("-t", "--threads", help="Number of download threads", type=int, default=5)
    parser.add_argument("-q", "--quiet", help="Suppress progress output", action="store_true")
    parser.add_argument("--verify-ssl", help="Verify SSL certificates", action="store_true", default=True)
    parser.add_argument("--no-verify-ssl", help="Don't verify SSL certificates", action="store_false", dest="verify_ssl")
    
    args = parser.parse_args()
    
    # Setup signal handler for graceful exit
    global archiver
    archiver = None
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print(f"Starting archive of {args.url}")
        print(f"Output directory: {args.output or os.path.expanduser('~/website_archives')}")
        print(f"Using {args.threads} threads")
        
        archiver = WebsiteArchiver(
            args.url,
            args.output,
            args.threads
        )
        
        success = archiver.start_archive(
            None if args.quiet else progress_callback
        )
        
        if success:
            print("\nArchive completed successfully!")
            print(f"Output directory: {archiver.output_dir}")
            print(f"Total pages archived: {len(archiver.visited_urls)}")
            print(f"Log file location: {os.path.join(archiver.output_dir, 'logs', 'archiver.log')}")
            return 0
        else:
            print("\nArchive failed. Check logs for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\nArchive stopped by user.")
        return 1
    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())