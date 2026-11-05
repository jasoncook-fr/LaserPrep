# LaserPrep

LaserPrep is a Python application that prepares student PDF drawings for laser cutting.

It imports PDF files from individual projects or student folders, extracts vector geometry and text outlines, detects and removes common artifacts, analyses and cleans geometry, validates the results, and generates SVG files for inspection and production.

LaserPrep is designed for digital fabrication laboratories and educational workshops where multiple student projects need to be prepared consistently and efficiently.

---

## Features

### PDF processing
- Import PDF vector geometry.
- Extract text outlines.
- Detect and remove watermarks and unwanted artifacts.
- Analyse PDF and vector complexity.
- Detect suspiciously small or unusually dense drawings.
- Validate geometry against configured machine dimensions.

### Geometry processing
- Remove duplicate and near-duplicate lines.
- Remove zero-length geometry.
- Clean and reconstruct vector geometry.
- Normalize colours.
- Analyse geometry chains and topology.
- Detect potentially overlapping collinear geometry.
- Optionally optimize cutting order.

### Reporting and export
- Generate operator reports.
- Generate detailed developer reports.
- Export diagnostic geometry when enabled.
- Generate SVG files for inspection and laser cutting.
- Produce batch activity reports.

### Batch processing
- Process multiple student folders automatically.
- Detect new, modified, and removed PDFs.
- Skip unchanged projects.
- Maintain processing history independently of student folders.
- Send automatic email notifications to students through Nextcloud and SMTP.

---

## Tested Environment

LaserPrep is developed and tested on the following system.

### System

| Component | Version |
|---|---|
| Operating system | Debian GNU/Linux 13.7 (Trixie) |
| Python | 3.13.5 |
| Inkscape | 1.4 |
| Poppler | 25.03.0 |
| libxml2 | 2.12.7 |
| libxslt | 1.1.35 |

### Python dependencies

| Package | Version |
|---|---|
| PyMuPDF | 1.28.0 |
| pypdfium2 | 5.11.0 |
| lxml | 6.1.1 |
| Shapely | 2.1.2 |
| PyInstaller | 6.22.2 |\n| ReportLab | 4.x |

These versions describe the current development and testing environment. Other versions may work, but have not necessarily been tested.

Python package dependencies are maintained in `requirements.txt`.

---

## How It Works

LaserPrep processes each project through a sequence of import, analysis, cleanup, validation, and export operations.

```text
Project Folder
      |
      v
Read PDF files
      |
      v
Import vector geometry
      |
      v
Extract text outlines
      |
      v
Merge geometry
      |
      v
Detect and remove artifacts
      |
      v
Geometry cleanup
      |
      v
Colour normalization
      |
      v
Geometry analysis and validation
      |
      v
Generate reports
      |
      v
Export SVG
      |
      v
Inspect in Inkscape
      |
      v
Laser cutter
```

The processing pipeline generates reports even when a file contains warnings or rejected elements. The operator should always inspect the results before sending a job to the laser cutter.

---

## Project Organization

LaserPrep supports two folder arrangements.

### Individual project

A project folder contains one or more PDFs:

```text
Project_A/
├── drawing1.pdf
├── drawing2.pdf
└── drawing3.pdf
```

All PDFs in the folder are treated as part of the same project.

### Student folders and multiple projects

For batch processing, the configured `BATCH_ROOT` contains one folder per student.

```text
STUDENTS/
├── Student_A/
│   ├── drawing1.pdf
│   └── drawing2.pdf
│
├── Student_B/
│   ├── Project_1/
│   │   ├── drawing1.pdf
│   │   └── drawing2.pdf
│   │
│   └── Project_2/
│       └── drawing.pdf
│
└── Student_C/
    └── drawing.pdf
```

LaserPrep supports:
- PDFs placed directly inside a student's folder.
- Projects organized in immediate subfolders.

Only one level of project subfolders is scanned. Deeper folder structures are not processed.

---

## Batch Processing

Batch Mode processes the student folders found inside `BATCH_ROOT`.

For each student, LaserPrep identifies projects that need processing and skips projects whose PDFs have not changed.

A project can contain multiple PDFs. Changes to any PDF trigger processing of the project.

### Incremental processing

LaserPrep calculates SHA-256 fingerprints of PDF files and stores them in administrator-controlled state files.

Processing state is stored outside the student workspace:

```text
ADMIN/
└── state/
    ├── Student_A.json
    ├── Student_B__Project_1.json
    └── Student_B__Project_2.json
```

On subsequent batch runs:

- Unchanged projects are skipped.
- Modified PDFs trigger reprocessing.
- New PDFs trigger reprocessing.
- Removed PDFs trigger reprocessing.
- Failed processing attempts are not recorded as successful, allowing another attempt on a later run.

The comparison is based on PDF contents, not just filenames. Replacing a file with a revised version under the same filename therefore triggers reprocessing.

### Batch reports

Each batch run produces a current PDF report, which can be opened in a standard PDF viewer:

```text
ADMIN/
└── CURRENT_BATCH_REPORT.pdf
```

A timestamped historical PDF report is also created:

```text
ADMIN/
└── BATCH_REPORTS/
    ├── 2026-08-28_14-32-05.pdf
    └── 2026-08-28_17-06-41.pdf
```

LaserPrep also maintains a rolling activity log:

```text
ADMIN/
└── activity/
    └── BATCH_ACTIVITY.json
```

The rolling activity window is controlled by `REPORT_RETENTION_DAYS` in `config.py`.

### Notification history

Email notification state is maintained separately from processing state:

```text
ADMIN/
└── notifications/
    └── notification_state.json
```

This prevents notification history from being confused with PDF processing history.

---

## Email Notifications

LaserPrep can automatically notify students by email after their project has been processed.

The notification system uses:

- The school's SMTP server to send email.
- The Nextcloud OCS sharing API to retrieve student email addresses from shared student folders.
- A local configuration file to store credentials.
- An independent notification history to prevent duplicate messages and retry unsuccessful notifications.

### Configuration file

Email and Nextcloud credentials are stored outside the repository:

```text
~/.config/laserprep/email.env
```

Create the configuration directory:

```bash
mkdir -p ~/.config/laserprep
```

Copy the supplied template and edit it:

```bash
cp email.env.example ~/.config/laserprep/email.env
vim ~/.config/laserprep/email.env
```

The configuration requires the following values:

```text
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM

NEXTCLOUD_URL
NEXTCLOUD_USERNAME
NEXTCLOUD_APP_PASSWORD
```

Use an application password generated in Nextcloud rather than your normal account password.

Protect the configuration file:

```bash
chmod 600 ~/.config/laserprep/email.env
```

The configuration file contains credentials and must never be committed to Git.

### How notifications work

In Batch Mode, the **Send student email notifications** option is enabled by default.

When enabled:

1. LaserPrep retrieves student email addresses from Nextcloud.
2. A completed project is added to the notification queue.
3. LaserPrep sends an email to the address associated with the student's shared folder.
4. Successful notifications are recorded in `notification_state.json`.

Notifications are sent after completed processing runs, including runs that produce warnings or rejected elements. Students are asked to inspect the generated reports and results.

Projects with no PDFs do not generate notifications.

If an email cannot be sent, or no unambiguous student email address is found, the notification remains pending and can be retried during a later batch run.

A notification is not sent again for the same successfully notified version of a project. Changes to its PDFs create a new project version and can generate a new notification.

When the notification checkbox is disabled, LaserPrep does not perform the Nextcloud lookup or modify notification history. Existing pending notifications are left untouched.

Single Project mode does not send student notifications.

### Nextcloud SSL certificate configuration

Some Nextcloud servers may present an incomplete SSL certificate chain. If the required intermediate certificate is not available on the system, LaserPrep may fail to connect to Nextcloud and retrieve student email addresses.

If this occurs, the missing intermediate certificate can be installed locally:

```bash
mkdir -p ~/.config/laserprep/certs
```

Save the required intermediate certificate in this directory. LaserPrep will automatically load it alongside the system's trusted CA certificates, while retaining normal SSL verification.

This is an optional, site-specific workaround. The permanent solution is for the server administrator to configure the server to provide the complete certificate chain.

---

## Installation

LaserPrep is currently developed and packaged for Linux.

### System dependencies

On Debian, install the required system packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk poppler-utils
```

Inkscape is recommended for inspecting and preparing the generated SVG files:

```bash
sudo apt install inkscape
```

Poppler is required for PDF text conversion through `pdftocairo`.

### Clone the repository

```bash
git clone https://github.com/jasoncook-fr/LaserPrep.git
cd LaserPrep
```

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Run from source

```bash
python main.py
```

This opens the LaserPrep graphical launcher.

---

## Building the Standalone Application

LaserPrep includes a build script using PyInstaller.

With the virtual environment activated:

```bash
./build_app.sh
```

The script:

1. Uses the project's `.venv` environment.
2. Builds a standalone executable with PyInstaller.
3. Uses `rocket.png` as the application icon.
4. Creates a desktop launcher.
5. Configures the launcher to open LaserPrep in a terminal.
6. Keeps the terminal open after processing so output and errors can be reviewed.

The executable is created at:

```text
dist/LaserPrep
```

The desktop launcher is created at:

```text
~/Desktop/LaserPrep.desktop
```

The Python virtual environment is required for development and building, but not for running the packaged executable.

External system dependencies, including Poppler, may still be required at runtime.

---

## Production Workstation Installation

A separate installer is provided for the production workstation.

After building and testing the application, run:

```bash
sudo ./install_app.sh
```

The installer:

- Installs the application in `/opt/LaserPrep/`.
- Installs the application icon.
- Creates a desktop launcher for the `ATN` user.
- Makes the installed application owned by `root`.

The `ATN` user must already exist on the workstation.

The resulting installation is:

```text
/opt/LaserPrep/
├── LaserPrep
└── rocket.png
```

The desktop launcher is created at:

```text
/home/ATN/Desktop/LaserPrep.desktop
```

The production installer is currently configured specifically for the `ATN` Linux account and is not a generic installer for arbitrary users.

---

## Configuration

Machine dimensions, processing thresholds, batch directories, and diagnostic options are defined in `config.py`.

### Batch directories

The default directories are:

```python
BATCH_ROOT = HOME / "Nextcloud" / "LaserPrep" / "STUDENTS"
ADMIN_ROOT = HOME / "Nextcloud" / "LaserPrep" / "ADMIN"
```

`BATCH_ROOT` contains student folders and project PDFs.

`ADMIN_ROOT` contains processing state, batch reports, activity history, and notification history.

### Machine dimensions

The current configuration includes two laser bed sizes:

| Machine | Width | Height |
|---|---:|---:|
| Large laser | 1000 mm | 600 mm |
| Small laser | 700 mm | 500 mm |

Display offsets and usable dimensions are also configured in `config.py`.

### Geometry and diagnostics

`config.py` contains adjustable parameters for:

- Geometry complexity thresholds.
- Suspiciously small drawing detection.
- Colour normalization.
- Collinear overlap diagnostics.
- Diagnostic exports.
- Cutting-order optimization.

Changes to these values can affect processing and validation results. Adjust them carefully and test with representative PDF files.

---

## Repository Structure

```text
LaserPrep/
├── main.py
├── config.py
├── requirements.txt
├── build_app.sh
├── install_app.sh
├── rocket.png
│
├── PDF processing
│   ├── pdf_reader.py
│   ├── pdf_text.py
│   ├── poppler.py
│   └── project.py
│
├── Geometry
│   ├── drawing.py
│   ├── vector_path.py
│   ├── geometry_cleanup.py
│   ├── geometry_chains.py
│   ├── geometry_statistics.py
│   ├── topology.py
│   ├── svg_path_parser.py
│   ├── svg_transform.py
│   ├── svg_geometry_import.py
│   ├── svg_geometry_export.py
│   └── svg_writer.py
│
├── Text and artifacts
│   ├── text_import.py
│   ├── text_group_analysis.py
│   ├── svg_text_import.py
│   ├── svg_analysis.py
│   ├── artifact_detector.py
│   ├── watermark_detector.py
│   └── watermark_remover.py
│
├── Colour and complexity
│   ├── colour_normalization.py
│   ├── color_analysis.py
│   ├── black_engraving.py
│   └── complexity.py
│
├── Reporting and diagnostics
│   ├── report.py
│   ├── report_dev.py
│   ├── batch_alerts.py
│   ├── diagnostics.py
│   ├── debug_manager.py
│   ├── collinear_overlap_diagnostic.py
│   └── tools/
│
└── Notifications
    ├── email_notifications.py
    ├── nextcloud_lookup.py
    └── notification_manager.py
```

---

## Current Development

LaserPrep is actively maintained and used in a production educational workshop environment.

Development priorities include:

- Improving geometry detection and cleanup.
- Increasing reliability with complex student PDFs.
- Improving processing performance.
- Refining reports and diagnostics.
- Maintaining a reliable batch-processing workflow.
- Improving maintainability while preserving the existing production pipeline.

---

## License

MIT License
