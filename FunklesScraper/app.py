import os
import json
import customtkinter as ctk
from paths import CACHE_DIR

# --- Load filings metadata ---
filings = []
for root, dirs, files in os.walk(CACHE_DIR):
    for file in files:
        if file.endswith(".meta.json"):
            with open(os.path.join(root, file), "r") as f:
                filings.append(json.load(f))

# --- GUI Setup ---
ctk.set_appearance_mode("dark")  # Set dark mode
ctk.set_default_color_theme("blue")  # Set blue theme

root = ctk.CTk()
root.title("📄 13D Filings Viewer")
root.geometry("950x650")

# --- Layout ---
frame = ctk.CTkFrame(root)
frame.pack(padx=20, pady=20, fill="both", expand=True)

# --- Label Filter ---
label_var = ctk.StringVar(value="All")
label_dropdown = ctk.CTkOptionMenu(frame, values=["All"] + sorted({f.get("label", "Unlabeled") for f in filings}),
                                   variable=label_var, command=lambda _: update_listbox())
label_dropdown.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

# --- Filings Listbox ---
listbox = ctk.CTkTextbox(frame, height=20, width=100)
listbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
listbox.bind("<ButtonRelease-1>", lambda e: show_summary())

# --- Summary Box ---
summary_box = ctk.CTkTextbox(frame, height=10, width=100)
summary_box.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

# --- Update Listbox ---
def update_listbox():
    listbox.delete(0, ctk.END)
    selected_label = label_var.get()
    for f in filings:
        if selected_label == "All" or f.get("label") == selected_label:
            listbox.insert(ctk.END, f["filename"])

# --- Show Summary ---
def show_summary():
    summary_box.delete(1.0, ctk.END)
    selection = listbox.curselection()
    if selection:
        idx = selection[0]
        filename = listbox.get(idx)
        for f in filings:
            if f["filename"] == filename:
                summary_box.insert(ctk.END, f.get("summary", "No summary available."))

# --- Initialize ---
update_listbox()

root.mainloop()
