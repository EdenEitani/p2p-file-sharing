import tkinter as tk
from tkinter import ttk
import threading

class PeerUI:
    def __init__(self, peer):
        self.peer = peer
        self.window = tk.Tk()
        self.window.title("P2P File Sharing")

        self.setup_ui()

    def setup_ui(self):
        # Frame for the list of available files
        frame = tk.Frame(self.window)
        frame.pack(pady=20)

        tk.Label(frame, text="Available Files for Download").pack()

        available_files = ["sample_file"]  # This should be fetched from the tracker or peers
        self.file_listbox = tk.Listbox(frame)
        self.file_listbox.pack(padx=10, pady=10)

        for file in available_files:
            self.file_listbox.insert(tk.END, file)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.window, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=20)

        self.status_label = tk.Label(self.window, text="Choose a file to download", pady=10)
        self.status_label.pack()

        # Download button
        download_button = tk.Button(self.window, text="Download File", command=self.start_download)
        download_button.pack(pady=10)

    def start_download(self):
        selected_file = self.file_listbox.get(tk.ACTIVE)
        if selected_file:
            self.progress_bar['value'] = 0
            self.peer.file_name = selected_file
            threading.Thread(target=self.peer.download_chunks, args=(self.progress_bar,)).start()
        else:
            tk.messagebox.showwarning("No file selected", "Please select a file to download.")

    def run(self):
        self.window.mainloop()