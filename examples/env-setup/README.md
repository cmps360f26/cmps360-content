# Data Science Python Environment Setup

The recommended way to run notebooks for this course is using **Google Colab in VS Code**.

## Option 1: Google Colab in VS Code (Recommended)

This option gives you the power of cloud computing ☁️ with the convenience of your local editor 💻.

1.  **Install Extensions:** In VS Code, install the following extensions:
    *   **Python** (by Microsoft)
    *   **Jupyter** (by Microsoft)
    *   **Google Colab** (by Google)
    *   **Marimo** (by Marimo)
    *   **ty** (by Astral)
2.  **Open Notebook:** Open your `.ipynb` file.
3.  **Connect:** Click **Select Kernel** (top-right of the notebook editor) > **Colab** > **Select Google Account** (sign in if prompted).

---

## Option 2: Google Colab on the Web

You can also run notebooks directly in your browser without VS Code.

1.  Go to [colab.research.google.com](https://colab.research.google.com).
2.  **Upload** your notebook (`.ipynb` file).
3.  **Install Libraries:** Libraries are pre-installed in Colab. 

---

## Option 3: Local Python Installation

If you prefer running everything locally on your machine, follow these steps:

### 1. Install Python
Download and install the latest Python from [python.org](https://www.python.org/downloads/).
*   **Important:** Check the box **"Add Python to path"** during installation.

### 2. Setup Environment

## Prerequisites (All Platforms)

- Python **3.14+** installed
- `requirements.txt` file available
- Setup scripts included in the project:
  - `setup-env.ps1` for Windows
  - `setup-env.sh` for macOS / Linux

## Windows Setup

### Step 1: Open the terminal
- Navigate to the folder containing cmps360-content\examples\env-setup
- Open a terminal in that folder

### Step 2: Allow script execution
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

### Step 3: Windows PowerShell - Run the setup script
.\setup-env.ps1

- Virtual environment is created at:
C:\Users<username>.venvs\py-env

## macOS / Linux Setup

### Step 1: Open the terminal
- Navigate to the folder containing cmps360-content\examples\env-setup

### Step 2: Make the script executable (one time only)
chmod +x setup-env.sh

### Step 3: Run the setup script
./setup-env.sh

- Virtual environment is created at:
~/.venvs/py-env


### 3. Run Notebooks
*   **VS Code:** Install the **Jupyter** extension. Open a `.ipynb` file, click **Select Kernel** > **Python Environments** > `py-env`.
*   **Browser:** Run `jupyter lab` in your activated terminal.

---

## Updating Libraries
To update your environment with the latest requirements, first activate the virtual environment and then upgrade the packages:
- Navigate to the folder containing cmps360-content\examples\env-setup
- Windows (PowerShell)
```bash
# Replace py-env with your environment name
$envName = "py-env"

& "$HOME\.venvs\$envName\Scripts\Activate.ps1"

pip install --upgrade -r requirements.txt
```
- Linux / macOS
```bash
# Replace py-env with your environment name
ENV_NAME="py-env"

source ~/.venvs/$ENV_NAME/bin/activate

pip install --upgrade -r requirements.txt
```
