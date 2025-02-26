# archiver/gui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from archiver.core import WebsiteArchiver
import os

class ArchiverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Website Archiver")
        self.root.geometry("600x400")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # URL input
        ttk.Label(self.main_frame, text="Website URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.main_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Output directory
        ttk.Label(self.main_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W)
        self.output_var = tk.StringVar(value=os.path.expanduser("~/website_archives"))
        self.output_entry = ttk.Entry(self.main_frame, textvariable=self.output_var, width=40)
        self.output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(self.main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, pady=5)
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Progress", padding="5")
        self.progress_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(self.progress_frame, textvariable=self.progress_var).grid(row=0, column=0, sticky=tk.W)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Status
        self.status_var = tk.StringVar(value="Pages archived: 0")
        ttk.Label(self.progress_frame, textvariable=self.status_var).grid(row=2, column=0, sticky=tk.W)
        
        # Current file
        self.current_file_var = tk.StringVar(value="")
        self.current_file_label = ttk.Label(self.progress_frame, textvariable=self.current_file_var, wraplength=500)
        self.current_file_label.grid(row=3, column=0, sticky=tk.W)
        
        # Control buttons
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(self.button_frame, text="Start Archive", command=self.start_archive)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(self.button_frame, text="Stop", command=self.stop_archive, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Archive thread
        self.archive_thread = None
        self.archiver = None

    def browse_output(self):
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)

    def update_progress(self, count, current_url):
        self.status_var.set(f"Pages archived: {count}")
        self.current_file_var.set(f"Current: {current_url}")
        self.root.update_idletasks()

    def start_archive(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
            
        self.archiver = WebsiteArchiver(url, self.output_var.get())
        self.archive_thread = threading.Thread(target=self._run_archive)
        self.archive_thread.daemon = True
        
        self.progress_bar.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set("Archiving...")
        
        self.archive_thread.start()

    def stop_archive(self):
        if self.archiver:
            self.archiver.active = False
            self.progress_var.set("Stopping...")
            self.stop_button.config(state=tk.DISABLED)

    def _run_archive(self):
        try:
            success = self.archiver.start_archive(self.update_progress)
            
            self.root.after(0, self._archive_complete, success)
            
        except Exception as e:
            self.root.after(0, self._archive_error, str(e))

    def _archive_complete(self, success):
        self.progress_bar.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        if success:
            self.progress_var.set("Archive complete")
            messagebox.showinfo("Complete", "Website archive completed successfully")
        else:
            self.progress_var.set("Archive failed")
            messagebox.showerror("Error", "Archive failed. Check logs for details")

    def _archive_error(self, error_msg):
        self.progress_bar.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set("Error")
        messagebox.showerror("Error", f"An error occurred: {error_msg}")

def main():
    root = tk.Tk()
    app = ArchiverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()