"""Tkinter launcher for LaserPrep."""

import json
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog

from config import ADMIN_ROOT, BATCH_ROOT


# ============================================================
# GUI Preferences
# ============================================================

UI_STATE_FILE = Path.home() / ".laserprep_ui.json"


def load_last_single_project_directory() -> Path | None:
    """Load the last directory used for Single Project selection."""

    if not UI_STATE_FILE.exists():
        return None

    try:
        with UI_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        directory = data.get("last_single_project_directory")

        if directory:
            path = Path(directory)
            if path.is_dir():
                return path

    except (OSError, json.JSONDecodeError):
        pass

    return None


def save_last_single_project_directory(directory: Path) -> None:
    """Remember the directory containing the last selected project."""

    try:
        with UI_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_single_project_directory": str(directory),
                },
                f,
                indent=2,
            )
    except OSError:
        # Failure to save a UI preference should never stop LaserPrep.
        pass


def launch_gui(
    process_project: Callable[..., str],
    process_batch: Callable[..., None],
    scan_batch_changes: Callable[..., list[dict]],
) -> None:
    """Launch the LaserPrep graphical launcher."""

    # Restrained colors give the two processing modes a clear visual identity.
    WINDOW_BG = "#F4F5F7"
    SINGLE_BG = "#EAF2FF"
    SINGLE_BUTTON = "#3B73C5"
    BATCH_BG = "#EAF7EF"
    BATCH_BUTTON = "#3F8F5B"
    BUTTON_TEXT = "#FFFFFF"
    TEXT = "#252525"
    SECONDARY_TEXT = "#666666"
    NEUTRAL_BUTTON = "#E2E4E7"

    root = tk.Tk()
    root.title("LaserPrep")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # --------------------------------------------------------
    # Appearance
    # --------------------------------------------------------

    root.configure(bg=WINDOW_BG)

    title_font = ("TkDefaultFont", 18, "bold")
    heading_font = ("TkDefaultFont", 11, "bold")
    body_font = ("TkDefaultFont", 9)

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------

    batch_root_var = tk.StringVar(value=str(BATCH_ROOT))
    status_var = tk.StringVar(value="Ready")
    email_notifications_var = tk.BooleanVar(value=True)
    single_expanded_var = tk.BooleanVar(value=False)
    new_changed_expanded_var = tk.BooleanVar(value=False)
    attention_expanded_var = tk.BooleanVar(value=False)
    new_changed_summary_var = tk.StringVar(value="Checking...")
    attention_summary_var = tk.StringVar(value="Checking...")

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def toggle_single_project() -> None:
        if single_expanded_var.get():
            single_expanded_var.set(False)
            single_body.pack_forget()
            single_toggle_button.configure(text="▶  TEST SINGLE PROJECT")
        else:
            single_expanded_var.set(True)
            single_body.pack(fill="x", pady=(4, 0))
            single_toggle_button.configure(text="▼  TEST SINGLE PROJECT")

    def select_single_project() -> None:
        last_directory = load_last_single_project_directory()

        kwargs = {
            "parent": root,
            "title": "Select the folder containing the PDF files",
        }

        if last_directory is not None:
            kwargs["initialdir"] = str(last_directory)

        folder = filedialog.askdirectory(**kwargs)

        if not folder:
            return

        selected_folder = Path(folder)

        # Remember the parent directory so the next dialog opens
        # alongside the other projects.
        save_last_single_project_directory(selected_folder.parent)

        root.destroy()
        process_project(selected_folder, use_state=False)

    def update_batch_preview() -> None:
        batch_root = Path(batch_root_var.get()).expanduser()

        new_changed_text.configure(state="normal")
        new_changed_text.delete("1.0", "end")
        attention_text.configure(state="normal")
        attention_text.delete("1.0", "end")

        if not batch_root.is_dir():
            new_changed_summary_var.set("Batch Root does not exist")
            attention_summary_var.set("Batch Root does not exist")
            new_changed_toggle_button.configure(
                text="▶  New / Changed — Batch Root does not exist"
            )
            attention_toggle_button.configure(
                text="▶  Needs Attention — Batch Root does not exist"
            )
            new_changed_text.insert("end", "Batch Root does not exist.\n")
            attention_text.insert("end", "Batch Root does not exist.\n")
            new_changed_text.configure(state="disabled")
            attention_text.configure(state="disabled")
            status_var.set("Invalid Batch Root")
            return

        changes = scan_batch_changes(batch_root)

        def set_preview_height(widget: tk.Text, line_count: int) -> None:
            widget.configure(height=max(2, min(7, line_count)))

        new_changed_projects = [
            item for item in changes
            if item["new"] or item["changed"]
        ]
        attention_projects = [
            item for item in changes
            if item.get("rejected") or item["removed"]
        ]

        new_changed_files = sum(
            len(item["new"]) + len(item["changed"])
            for item in new_changed_projects
        )
        attention_files = sum(
            len(item.get("rejected", [])) + len(item["removed"])
            for item in attention_projects
        )

        if new_changed_projects:
            new_changed_summary_var.set(
                f"{len(new_changed_projects)} project(s) / "
                f"{new_changed_files} PDF(s)"
            )
        else:
            new_changed_summary_var.set("nothing new")

        if attention_projects:
            attention_summary_var.set(
                f"{len(attention_projects)} project(s) / "
                f"{attention_files} PDF(s)"
            )
        else:
            attention_summary_var.set("nothing to review")

        new_changed_toggle_button.configure(
            text=(
                f"{'▼' if new_changed_expanded_var.get() else '▶'}  "
                f"New / Changed — {new_changed_summary_var.get()}"
            )
        )
        attention_toggle_button.configure(
            text=(
                f"{'▼' if attention_expanded_var.get() else '▶'}  "
                f"Needs Attention — {attention_summary_var.get()}"
            )
        )

        if new_changed_projects:
            for item in new_changed_projects:
                counts = []
                if item["new"]:
                    counts.append(f"{len(item['new'])} new")
                if item["changed"]:
                    counts.append(f"{len(item['changed'])} changed")

                new_changed_text.insert(
                    "end",
                    f"• {item['project']} — {', '.join(counts)}\n",
                )

                for name in item["new"]:
                    new_changed_text.insert("end", f"    + {name}\n")
                for name in item["changed"]:
                    new_changed_text.insert("end", f"    ↻ {name}\n")

                new_changed_text.insert("end", "\n")
        else:
            new_changed_text.insert("end", "No new or changed PDFs.\n")

        if attention_projects:
            for item in attention_projects:
                counts = []
                if item.get("rejected"):
                    counts.append(f"{len(item['rejected'])} previously rejected")
                if item["removed"]:
                    counts.append(f"{len(item['removed'])} removed")

                attention_text.insert(
                    "end",
                    f"• {item['project']} — {', '.join(counts)}\n",
                )

                for name in item.get("rejected", []):
                    attention_text.insert(
                        "end",
                        f"    ❌ {name}\n",
                        "rejected",
                    )
                for name in item["removed"]:
                    attention_text.insert(
                        "end",
                        f"    − {name}\n",
                        "removed",
                    )

                attention_text.insert("end", "\n")
        else:
            attention_text.insert("end", "No files need attention.\n")

        new_changed_line_count = 1
        if new_changed_projects:
            new_changed_line_count = sum(
                1
                + len(item["new"])
                + len(item["changed"])
                + 1
                for item in new_changed_projects
            )
        set_preview_height(new_changed_text, new_changed_line_count)

        attention_line_count = 1
        if attention_projects:
            attention_line_count = sum(
                1
                + len(item.get("rejected", []))
                + len(item["removed"])
                + 1
                for item in attention_projects
            )
        set_preview_height(attention_text, attention_line_count)

        new_changed_text.configure(state="disabled")
        attention_text.configure(state="disabled")

        total_projects = len(changes)
        if total_projects:
            status_var.set(f"{total_projects} project(s) need processing")
        else:
            status_var.set("Nothing new to process")

    def toggle_new_changed_preview() -> None:
        if new_changed_expanded_var.get():
            new_changed_expanded_var.set(False)
            new_changed_body.pack_forget()
            new_changed_toggle_button.configure(
                text=f"▶  New / Changed — {new_changed_summary_var.get()}"
            )
        else:
            new_changed_expanded_var.set(True)
            new_changed_body.pack(
                before=attention_toggle_button,
                fill="both",
                expand=True,
                pady=(4, 0),
            )
            new_changed_toggle_button.configure(
                text=f"▼  New / Changed — {new_changed_summary_var.get()}"
            )

    def toggle_attention_preview() -> None:
        if attention_expanded_var.get():
            attention_expanded_var.set(False)
            attention_body.pack_forget()
            attention_toggle_button.configure(
                text=f"▶  Needs Attention — {attention_summary_var.get()}"
            )
        else:
            attention_expanded_var.set(True)
            attention_body.pack(
                fill="both",
                expand=True,
                pady=(4, 0),
            )
            attention_toggle_button.configure(
                text=f"▼  Needs Attention — {attention_summary_var.get()}"
            )

    def browse_batch_root() -> None:
        folder = filedialog.askdirectory(
            parent=root,
            title="Select the Batch Root folder",
            initialdir=batch_root_var.get(),
        )

        if folder:
            batch_root_var.set(folder)
            update_batch_preview()

    def run_batch() -> None:
        batch_root = Path(batch_root_var.get()).expanduser()

        if not batch_root.is_dir():
            status_var.set("The selected Batch Root does not exist.")
            return

        send_notifications = email_notifications_var.get()

        root.destroy()
        process_batch(
            batch_root,
            send_notifications=send_notifications,
        )

    # --------------------------------------------------------
    # Main container
    # --------------------------------------------------------

    outer = tk.Frame(
        root,
        bg=WINDOW_BG,
        padx=28,
        pady=24,
    )
    outer.pack()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    tk.Label(
        outer,
        text="LaserPrep",
        font=title_font,
        bg=WINDOW_BG,
    ).pack()

    tk.Label(
        outer,
        text="PDF → laser preparation",
        font=body_font,
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
    ).pack(pady=(2, 22))

    # --------------------------------------------------------
    # Single Project section
    # --------------------------------------------------------

    single_frame = tk.LabelFrame(
        outer,
        text="  TEST SINGLE PROJECT  ",
        font=heading_font,
        bg=SINGLE_BG,
        padx=18,
        pady=8,
    )
    single_frame.pack(fill="x", pady=(0, 10))

    single_toggle_button = tk.Button(
        single_frame,
        text="▶  TEST SINGLE PROJECT",
        command=toggle_single_project,
        bg=SINGLE_BG,
        fg=TEXT,
        activebackground=SINGLE_BG,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        anchor="w",
        font=heading_font,
    )
    single_toggle_button.pack(fill="x")

    single_body = tk.Frame(single_frame, bg=SINGLE_BG)

    tk.Label(
        single_body,
        text="Process one project without state tracking.",
        font=body_font,
        bg=SINGLE_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x")

    tk.Button(
        single_body,
        text="Select Project",
        width=20,
        height=2,
        command=select_single_project,
        bg=SINGLE_BUTTON,
        fg=BUTTON_TEXT,
        activebackground=SINGLE_BUTTON,
        activeforeground=BUTTON_TEXT,
        relief="flat",
        bd=0,
    ).pack(pady=(10, 0))

    # --------------------------------------------------------
    # Batch section
    # --------------------------------------------------------

    batch_frame = tk.LabelFrame(
        outer,
        text="  BATCH PROCESSING  ",
        font=heading_font,
        bg=BATCH_BG,
        padx=18,
        pady=14,
    )
    batch_frame.pack(fill="x")

    tk.Label(
        batch_frame,
        text="Process all projects found under the Batch Root.",
        font=body_font,
        bg=BATCH_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x")

    tk.Label(
        batch_frame,
        text="Batch Root",
        font=heading_font,
        bg=BATCH_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x", pady=(14, 4))

    root_row = tk.Frame(batch_frame, bg=BATCH_BG)
    root_row.pack(fill="x")

    tk.Entry(
        root_row,
        textvariable=batch_root_var,
        width=43,
        relief="solid",
        bd=1,
    ).pack(side="left", fill="x", expand=True)

    tk.Button(
        root_row,
        text="Browse…",
        command=browse_batch_root,
        bg=NEUTRAL_BUTTON,
        fg=TEXT,
        activebackground=NEUTRAL_BUTTON,
        relief="flat",
        bd=0,
    ).pack(side="left", padx=(8, 0))

    preview_refresh_button = tk.Button(
        root_row,
        text="Refresh",
        command=update_batch_preview,
        bg=NEUTRAL_BUTTON,
        fg=TEXT,
        activebackground=NEUTRAL_BUTTON,
        relief="flat",
        bd=0,
    )
    preview_refresh_button.pack(side="left", padx=(6, 0))

    tk.Checkbutton(
        batch_frame,
        text="Send student email notifications",
        variable=email_notifications_var,
        bg=BATCH_BG,
        fg=TEXT,
        activebackground=BATCH_BG,
        activeforeground=TEXT,
        selectcolor=BATCH_BG,
        font=body_font,
        anchor="w",
    ).pack(fill="x", pady=(12, 0))

    preview_area = tk.Frame(batch_frame, bg=BATCH_BG)
    preview_area.pack(fill="both", expand=True, pady=(14, 0))

    # --------------------------------------------------------
    # New / Changed category
    # --------------------------------------------------------

    new_changed_toggle_button = tk.Button(
        preview_area,
        text="▶  New / Changed — Checking...",
        command=toggle_new_changed_preview,
        bg="#FFF4D6",
        fg=TEXT,
        activebackground="#FFF4D6",
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        anchor="w",
        font=heading_font,
    )
    new_changed_toggle_button.pack(fill="x")

    new_changed_body = tk.Frame(preview_area, bg="#FFF4D6")

    new_changed_text_frame = tk.Frame(new_changed_body, bg="#FFF4D6")
    new_changed_text_frame.pack(fill="both", expand=True)

    new_changed_scrollbar = tk.Scrollbar(new_changed_text_frame)
    new_changed_scrollbar.pack(side="right", fill="y")

    new_changed_text = tk.Text(
        new_changed_text_frame,
        height=7,
        width=55,
        wrap="none",
        bg="#FFFFFF",
        fg=TEXT,
        relief="solid",
        bd=1,
        yscrollcommand=new_changed_scrollbar.set,
    )
    new_changed_text.pack(side="left", fill="both", expand=True)
    new_changed_scrollbar.config(command=new_changed_text.yview)

    # --------------------------------------------------------
    # Needs Attention category
    # --------------------------------------------------------

    attention_toggle_button = tk.Button(
        preview_area,
        text="▶  Needs Attention — Checking...",
        command=toggle_attention_preview,
        bg="#FDECEC",
        fg="#8F1D1D",
        activebackground="#FDECEC",
        activeforeground="#8F1D1D",
        relief="flat",
        bd=0,
        anchor="w",
        font=heading_font,
    )
    attention_toggle_button.pack(fill="x", pady=(8, 0))

    attention_body = tk.Frame(preview_area, bg="#FDECEC")

    attention_text_frame = tk.Frame(attention_body, bg="#FDECEC")
    attention_text_frame.pack(fill="both", expand=True)

    attention_scrollbar = tk.Scrollbar(attention_text_frame)
    attention_scrollbar.pack(side="right", fill="y")

    attention_text = tk.Text(
        attention_text_frame,
        height=7,
        width=55,
        wrap="none",
        bg="#FFFFFF",
        fg=TEXT,
        relief="solid",
        bd=1,
        yscrollcommand=attention_scrollbar.set,
    )
    attention_text.pack(side="left", fill="both", expand=True)
    attention_scrollbar.config(command=attention_text.yview)
    attention_text.tag_configure("rejected", foreground="#B42318")
    attention_text.tag_configure("removed", foreground="#8F1D1D")

    tk.Button(
        batch_frame,
        text="Run Batch",
        width=20,
        height=2,
        command=run_batch,
        bg=BATCH_BUTTON,
        fg=BUTTON_TEXT,
        activebackground=BATCH_BUTTON,
        activeforeground=BUTTON_TEXT,
        relief="flat",
        bd=0,
    ).pack(pady=(14, 0))

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer = tk.Frame(outer, bg=WINDOW_BG)
    footer.pack(fill="x", pady=(16, 0))

    tk.Label(
        footer,
        textvariable=status_var,
        font=body_font,
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
        anchor="w",
    ).pack(side="left")

    # Quietly display the administrator folder location for reference.
    tk.Label(
        outer,
        text=f"Admin folder: {ADMIN_ROOT}",
        font=("TkDefaultFont", 8),
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
        anchor="w",
    ).pack(fill="x", pady=(8, 0))

    tk.Button(
        footer,
        text="Quit",
        width=10,
        command=root.destroy,
        bg=NEUTRAL_BUTTON,
        fg=TEXT,
        activebackground=NEUTRAL_BUTTON,
        relief="flat",
        bd=0,
    ).pack(side="right")

    update_batch_preview()

    # --------------------------------------------------------
    # Center the launcher on screen
    # --------------------------------------------------------

    root.update_idletasks()

    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2

    root.geometry(f"+{x}+{y}")
    root.mainloop()
