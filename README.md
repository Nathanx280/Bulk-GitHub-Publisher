Here’s a **clean, full copy-paste README** for that script based on the actual file you sent 

---

# Bulk GitHub Publisher

Bulk GitHub Publisher is a Python automation script that scans a folder of local projects, creates GitHub repositories for them, initializes Git if needed, commits files, and pushes everything to GitHub automatically.

It is designed for quickly uploading large collections of projects with minimal manual work.

---

## 🧠 Core Concept

Automate publishing multiple projects:

1. Scan a parent folder
2. Detect valid project subfolders
3. Create GitHub repositories
4. Initialize Git (if needed)
5. Commit files
6. Push to GitHub

---

## 🔥 Features

### 📂 Project Scanner

* Scans a parent directory for subfolders
* Skips:

  * empty folders
  * ignored system folders
  * folders without meaningful files

---

### 🚫 Smart Filtering

Automatically ignores:

* `.git`, `node_modules`, `venv`, `dist`, etc.
* system files like `.DS_Store`, `Thumbs.db`
* large binary-heavy folders (optional size limit)

---

### 🧹 Auto `.gitignore`

* Creates a default `.gitignore` if missing
* Covers:

  * Python
  * Node
  * build outputs
  * logs
  * environment files

---

### 🧠 Repo Name Sanitization

* Cleans folder names into valid GitHub repo names
* Removes invalid characters
* Converts spaces → hyphens

---

### 🔐 GitHub API Integration

* Authenticates using:

  * `GITHUB_USER`
  * `GITHUB_TOKEN`
* Creates repos automatically
* Supports:

  * private repos
  * public repos

---

### 🧾 Git Automation

Handles:

* `git init` (if missing)
* branch setup (`main` by default)
* staging files
* committing changes
* pushing to GitHub

---

### 🔁 Smart Commit Logic

* Only commits if changes exist
* Skips empty repos
* Handles first commit correctly

---

### 🔗 Remote Management

* Adds or updates remote (`origin` by default)
* Ensures correct GitHub URL
* Sets upstream branch automatically

---

### 📊 Folder Analysis

Before processing, shows:

* folder size (MB)
* file count
* detects large binaries

---

### ⚠️ Large File Protection

* Skips folders exceeding size limit (default: 500MB)
* Warns about large file types:

  * `.zip`, `.exe`, `.mp4`, `.psd`, etc.

---

### 🧪 Dry Run Mode

* Preview what will happen without pushing

---

## 🧱 Tech Stack

* Python
* Git CLI
* GitHub REST API
* Requests library

---

## 📁 File

```bash
bulk_github_publish.py
```

---

## ⚙️ Setup

### Install dependency

```bash
pip install requests
```

---

### Set environment variables

```bash
set GITHUB_USER=your_username
set GITHUB_TOKEN=your_token
```

---

## 🚀 Usage

### Basic usage

```bash
python bulk_github_publish.py "C:\Path\To\Projects"
```

---

### Create private repos

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --private
```

---

### Create public repos

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --public
```

---

### Dry run (no push)

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --dry-run
```

---

### Custom branch

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --branch main
```

---

### Custom commit message

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --commit-message "Initial upload"
```

---

### Limit folder size

```bash
python bulk_github_publish.py "C:\Path\To\Projects" --max-folder-mb 300
```

---

## 🔄 Workflow

```text
Scan Folder
    ↓
Filter Valid Projects
    ↓
Create GitHub Repo
    ↓
Init Git (if needed)
    ↓
Commit Files
    ↓
Push to GitHub
```

---

## 🎯 Use Cases

* Upload entire project collections
* Backup local projects to GitHub
* Quickly publish multiple repos
* Organize large code archives
* Automate development workflows

---

## ⚠️ Requirements

* Git installed and in PATH
* GitHub account + token
* Internet connection

---

## ⚠️ Limitations

* Relies on Git CLI being installed
* Large repos may fail without Git LFS
* API rate limits possible
* No GUI (CLI only)

---

## 🔮 Future Improvements

* GUI interface
* Git LFS support
* parallel processing
* repo description customization
* tagging/versioning system
* exclude/include patterns via config

---

## 🧑‍💻 Author

Nathanx280

---

## 💀 Real talk

This script is actually:

✔ very practical
✔ automation-heavy
✔ saves tons of time
✔ closest thing you’ve built to a real dev tool

---

If you want next:
I can upgrade this into a **GUI bulk uploader tool (like a real desktop app with buttons + progress + logs)**
