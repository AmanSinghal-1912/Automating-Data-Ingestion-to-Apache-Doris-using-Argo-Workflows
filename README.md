# Project Documentation 

## 📘 Table of Contents
1. [Project Overview - Simple Explanation](#project-overview---simple-explanation)
2. [What Technologies We Use & Why](#what-technologies-we-use--why)
3. [Installation Guide](#installation-guide)
4. [Project Setup Step-by-Step](#project-setup-step-by-step)
5. [How Everything Works Together](#how-everything-works-together)
6. [Common Commands Reference](#common-commands-reference)

---

## 🎯 Project Overview - Simple Explanation

### **What is this project?**

Imagine you have a folder on your computer with CSV files (like Excel files). Every 5 minutes, we want to:
1. **Find all CSV files** in that folder
2. **Clean the data** (fix column names, remove duplicates)
3. **Automatically detect** what type of data is in each column (numbers, text, dates)
4. **Load the data** into a database
5. **Filter out bad data** (like finding "twenty" instead of 20 in an age column)
6. **Save the bad data** to error files so you can fix it later

**The Problem We're Solving:**
- ❌ Manually copying CSV data to database is boring and error-prone
- ❌ Different CSV files have different columns - how to handle this?
- ❌ Sometimes data has mistakes (text in number columns)
- ❌ We want this to happen automatically, not manually

**Our Solution:**
- ✅ Automated pipeline that runs every 5 minutes
- ✅ Smart schema detection (figures out data types automatically)
- ✅ Error handling (bad rows go to error files, good rows go to database)
- ✅ All happening in Kubernetes (professional-grade automation)

### **Real-World Example**

Let's say you have these files:

**a.csv** (Employee data):
```csv
name,age
John,25
Sarah,30
Bob,twenty  ← This is wrong! Age should be a number
```

**b.csv** (Different structure):
```csv
name,salary
John,50000
Sarah,60000
```

**What happens automatically every 5 minutes:**

1. **a.csv processing**:
   - ✓ Detects "age" should be a number (TINYINT type)
   - ✓ Loads John (25) and Sarah (30) to database
   - ✗ Finds Bob's "twenty" is invalid
   - → Saves Bob's row to `error_files/error_a.csv`

2. **b.csv processing**:
   - ✗ Different columns (name/salary vs name/age)
   - → Saves entire file to `error_files/error_b.csv`
   - → You can decide what to do with it later

**Result:**
- Database has clean data: John and Sarah with valid ages
- Error files have problematic data for you to review
- Everything happens automatically!

---

## 🛠️ What Technologies We Use & Why

### **1. Minikube**

**What is it?**
Think of Minikube as a "mini cloud" running on your laptop. It's Kubernetes in a box.

**Simple Analogy:**
Imagine you want to practice being a chef, but you don't have access to a full restaurant kitchen. Minikube is like having a mini kitchen in your home - same tools, same concepts, but smaller scale and perfect for learning.

**Why do we use it?**
- ✅ Learn Kubernetes without paying for cloud (AWS, Google Cloud)
- ✅ Test automation locally before deploying to production
- ✅ Professional-grade container orchestration on your laptop
- ✅ Runs on Windows, Mac, Linux

**What does it do for us?**
- Runs our Python pipeline in isolated containers
- Manages scheduling (every 5 minutes)
- Mounts our local Windows folder into containers
- Provides networking so containers can talk to our database

**Real-world use:**
- Companies use Kubernetes in production
- Minikube lets you learn/test the same technology locally
- Your skills transfer directly to real cloud environments

---

### **2. Apache Doris**

**What is it?**
Doris is a super-fast database designed for analytics (asking questions about your data).

**Simple Analogy:**
Think of a regular database (like MySQL) as a filing cabinet where you store and retrieve individual documents. Doris is like a smart library that's optimized for counting, averaging, and analyzing millions of documents at once.

**Why do we use it?**
- ✅ Handles large amounts of data efficiently
- ✅ Fast for analytics queries (COUNT, SUM, AVG)
- ✅ Compatible with MySQL protocol (easy to connect)
- ✅ Open source and free

**What does it do for us?**
- Stores our CSV data in tables
- Supports different data types (TINYINT, VARCHAR, BIGINT, etc.)
- Allows SQL queries to analyze the data
- DUPLICATE KEY model allows fast inserts

**In our project:**
- IP: `192.168.29.181`
- Port: `9030` (MySQL protocol)
- Database: `updated_test2`
- Table: `main_data_table`

**Example Query:**
```sql
-- After pipeline runs, you can ask questions like:
SELECT AVG(age) FROM main_data_table;  -- What's the average age?
SELECT COUNT(*) FROM main_data_table WHERE age > 50;  -- How many people over 50?
```

---

### **3. Kubernetes (K8s)**

**What is it?**
Kubernetes is like an operating system for containers. It manages, schedules, and monitors containerized applications.

**Simple Analogy:**
Imagine you run a restaurant:
- **Without Kubernetes**: You manually tell each chef when to start cooking, where to work, what ingredients to use, and when to take breaks.
- **With Kubernetes**: You write a recipe (YAML file) once, and a manager (Kubernetes) automatically assigns chefs, schedules work, replaces sick chefs, and ensures everything runs smoothly.

**Key Concepts:**

**Pod:**
- Smallest unit in Kubernetes
- Think of it as a "container with a job to do"
- In our project: One pod runs our Python pipeline, then disappears

**Namespace:**
- Like a folder to organize resources
- We use namespace `argo` for our workflows

**Volume:**
- Shared storage that pods can access
- We mount `C:\Users\singh\Desktop\Minikube-Doris` into pods

**Why do we use it?**
- ✅ Automatic scheduling (runs our pipeline every 5 minutes)
- ✅ Self-healing (if pipeline fails, Kubernetes retries)
- ✅ Resource management (CPU, memory limits)
- ✅ Industry standard (used by Google, Netflix, Uber)

---

### **4. Argo Workflows**

**What is it?**
Argo Workflows is a Kubernetes-native workflow engine. It lets you define multi-step jobs that run in Kubernetes.

**Simple Analogy:**
Think of a recipe with multiple steps:
1. Preheat oven
2. Mix ingredients
3. Bake for 30 minutes
4. Let cool

Argo Workflows is like a smart cooking assistant that:
- Follows your recipe (YAML file)
- Executes each step in order
- Checks if each step succeeded before moving to the next
- Logs what happened
- Can schedule the recipe to run repeatedly (e.g., bake cookies every 5 minutes)

**Why do we use it?**
- ✅ Designed for Kubernetes (native integration)
- ✅ Supports cron schedules (every 5 minutes)
- ✅ Beautiful web UI to see workflows
- ✅ Handles errors and retries gracefully

**In our project:**
- Creates a new "workflow" every 5 minutes
- Each workflow spawns a pod
- Pod runs our Python pipeline
- After completion, pod is deleted
- Workflow history is preserved

---

### **5. CronWorkflow**

**What is it?**
A CronWorkflow is a specific type of Argo Workflow that runs on a schedule (like cron jobs in Linux).

**Simple Analogy:**
It's like setting an alarm clock, but instead of waking you up, it wakes up a Kubernetes pod to do work.

**Cron Schedule Syntax:**
```
*/5  *  *  *  *
 │   │  │  │  │
 │   │  │  │  └─ Day of week (0-6, 0=Sunday)
 │   │  │  └──── Month (1-12)
 │   │  └─────── Day of month (1-31)
 │   └────────── Hour (0-23)
 └────────────── Minute (0-59)

*/5 means "every 5 minutes"
```

**Examples:**
```
*/5 * * * *     → Every 5 minutes
0 * * * *       → Every hour (on the hour)
0 9 * * *       → Every day at 9:00 AM
0 0 * * 0       → Every Sunday at midnight
0 0 1 * *       → First day of every month at midnight
```

**In our project:**
```yaml
schedule: "*/5 * * * *"  # Every 5 minutes
timezone: "America/New_York"
```

This means:
- 6:00:00 AM → Run workflow
- 6:05:00 AM → Run workflow
- 6:10:00 AM → Run workflow
- (continues every 5 minutes...)

---

### **6. Helm**

**What is it?**
Helm is a package manager for Kubernetes. Think of it like an app store for Kubernetes applications.

**Simple Analogy:**
- **Without Helm**: Installing software = downloading files, copying them to folders, editing configuration files manually, running multiple commands
- **With Helm**: Installing software = one command `helm install`, like clicking "Install" in an app store

**Why do we use it?**
- ✅ Install complex applications with one command
- ✅ Manages dependencies automatically
- ✅ Easy to upgrade/rollback
- ✅ Community-maintained "charts" (packages)

**In our project:**
We use Helm to install Argo Workflows:
```bash
helm install argo-workflows argo/argo-workflows -n argo --create-namespace
```

This single command:
- Creates namespace `argo`
- Installs Argo Workflows controller
- Sets up web UI
- Configures permissions
- Would take 50+ manual steps without Helm!

---

### **7. kubectl**

**What is it?**
`kubectl` (kube-control) is the command-line tool to interact with Kubernetes.

**Simple Analogy:**
If Kubernetes is a car, `kubectl` is the steering wheel, gas pedal, and brake - it's how you control the car.

**Why do we use it?**
- ✅ View what's running in Kubernetes
- ✅ Create/delete resources
- ✅ View logs from containers
- ✅ Debug issues

**Common Commands We Use:**

```bash
# View all pods in argo namespace
kubectl get pods -n argo

# View logs from a specific pod
kubectl logs -n argo <pod-name>

# View workflows
kubectl get workflows -n argo

# View CronWorkflows
kubectl get cronworkflows -n argo

# Describe a resource (detailed info)
kubectl describe cronwf csv-doris-cron -n argo

# Delete a resource
kubectl delete cronwf csv-doris-cron -n argo
```

**In our project:**
We use `kubectl` to:
- Check if our CronWorkflow is running
- View pod logs to debug issues
- Apply our YAML configuration files
- Monitor workflow status

---

## 📥 Installation Guide

### **Prerequisites**
- Windows 10/11
- Administrator access
- Internet connection
- At least 8GB RAM (16GB recommended)

---

### **Step 1: Install Docker Desktop**

**What is Docker?**
Docker creates isolated containers (like lightweight virtual machines) that package your application with all its dependencies.

**Installation:**

1. **Download Docker Desktop:**
   - Go to: https://www.docker.com/products/docker-desktop
   - Click "Download for Windows"
   - File: `Docker Desktop Installer.exe`

2. **Install:**
   ```powershell
   # Run the installer (double-click)
   # During installation:
   # ✓ Enable WSL 2 (Windows Subsystem for Linux)
   # ✓ Enable Hyper-V (if prompted)
   ```

3. **Verify Installation:**
   ```powershell
   docker --version
   # Output: Docker version 24.0.6, build ed223bc
   
   docker ps
   # Output: CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
   # (empty list is fine)
   ```

4. **Configure Docker:**
   - Open Docker Desktop
   - Go to Settings → Resources
   - Allocate at least 4GB RAM to Docker
   - Apply & Restart

---

### **Step 2: Install Minikube**

**Installation:**

1. **Download Minikube:**
   ```powershell
   # Using PowerShell (run as Administrator)
   
   # Download installer
   Invoke-WebRequest -Uri "https://github.com/kubernetes/minikube/releases/latest/download/minikube-installer.exe" -OutFile "minikube-installer.exe"
   
   # Install
   .\minikube-installer.exe
   ```

2. **Verify Installation:**
   ```powershell
   minikube version
   # Output: minikube version: v1.32.0
   ```

3. **Start Minikube:**
   ```powershell
   # Start Minikube cluster with Docker driver
   minikube start --driver=docker
   
   # This command:
   # - Creates a Kubernetes cluster
   # - Pulls necessary images
   # - Configures kubectl
   # - Takes 2-5 minutes
   
   # Output:
   # 😄  minikube v1.32.0 on Windows 10
   # ✨  Using the docker driver based on user configuration
   # 👍  Starting control plane node minikube in cluster minikube
   # 🚜  Pulling base image ...
   # 🔥  Creating docker container (CPUs=2, Memory=4000MB) ...
   # 🐳  Preparing Kubernetes v1.28.3 on Docker 24.0.7 ...
   # 🔗  Configuring bridge CNI (Container Networking Interface) ...
   # 🔎  Verifying Kubernetes components...
   # 🌟  Enabled addons: storage-provisioner, default-storageclass
   # 🏄  Done! kubectl is now configured to use "minikube" cluster
   ```

4. **Verify Cluster:**
   ```powershell
   kubectl get nodes
   # Output:
   # NAME       STATUS   ROLES           AGE   VERSION
   # minikube   Ready    control-plane   2m    v1.28.3
   
   kubectl cluster-info
   # Output:
   # Kubernetes control plane is running at https://127.0.0.1:xxxxx
   # CoreDNS is running at https://127.0.0.1:xxxxx/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
   ```

---

### **Step 3: Install kubectl**

**Note:** Minikube installs kubectl automatically, but you can install it separately:

**Installation:**

```powershell
# Download kubectl
curl.exe -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"

# Move to system path
Move-Item .\kubectl.exe C:\Windows\System32\kubectl.exe

# Verify
kubectl version --client
# Output: Client Version: v1.28.0
```

**Configure kubectl for Minikube:**
```powershell
# This is done automatically by minikube start
# But you can manually switch contexts:

kubectl config use-context minikube
# Output: Switched to context "minikube".

kubectl config current-context
# Output: minikube
```

---

### **Step 4: Install Helm**

**Installation:**

1. **Download Helm:**
   ```powershell
   # Using PowerShell (run as Administrator)
   
   # Download
   Invoke-WebRequest -Uri "https://get.helm.sh/helm-v3.13.0-windows-amd64.zip" -OutFile "helm.zip"
   
   # Extract
   Expand-Archive -Path helm.zip -DestinationPath C:\helm
   
   # Move to system path
   Move-Item C:\helm\windows-amd64\helm.exe C:\Windows\System32\helm.exe
   
   # Clean up
   Remove-Item helm.zip
   Remove-Item -Recurse C:\helm
   ```

2. **Verify Installation:**
   ```powershell
   helm version
   # Output: version.BuildInfo{Version:"v3.13.0", GitCommit:"..."}
   ```

3. **Add Helm Repositories:**
   ```powershell
   # Add Argo Workflows repository
   helm repo add argo https://argoproj.github.io/argo-helm
   
   # Update repositories
   helm repo update
   # Output:
   # Hang tight while we grab the latest from your chart repositories...
   # ...Successfully got an update from the "argo" chart repository
   # Update Complete. ⎈Happy Helming!⎈
   ```

---

### **Step 5: Install Argo Workflows**

**Installation:**

1. **Create Namespace:**
   ```powershell
   kubectl create namespace argo
   # Output: namespace/argo created
   ```

2. **Install Argo Workflows using Helm:**
   ```powershell
   helm install argo-workflows argo/argo-workflows -n argo
   
   # Output:
   # NAME: argo-workflows
   # LAST DEPLOYED: Wed Nov 6 10:30:00 2025
   # NAMESPACE: argo
   # STATUS: deployed
   # REVISION: 1
   # TEST SUITE: None
   ```

3. **Verify Installation:**
   ```powershell
   kubectl get pods -n argo
   # Output:
   # NAME                                                  READY   STATUS    RESTARTS   AGE
   # argo-workflows-server-xxxxxxxxxx-xxxxx               1/1     Running   0          2m
   # argo-workflows-workflow-controller-xxxxxxxx-xxxxx    1/1     Running   0          2m
   ```

4. **Wait for pods to be Ready:**
   ```powershell
   kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argo-workflows-server -n argo --timeout=300s
   # Output: pod/argo-workflows-server-xxxxxxxxxx-xxxxx condition met
   ```

---

### **Step 6: Install Argo CLI**

**Installation:**

```powershell
# Download Argo CLI
Invoke-WebRequest -Uri "https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/argo-windows-amd64.gz" -OutFile "argo.gz"

# Extract (you may need 7-Zip or similar)
# After extraction, move to system path
Move-Item argo.exe C:\Windows\System32\argo.exe

# Verify
argo version
# Output: argo: v3.5.0
```

**Configure Argo CLI:**
```powershell
# Argo CLI automatically uses kubectl context
argo list -n argo
# Output: (empty list - no workflows yet)
```

---

### **Step 7: Access Argo Web UI**

**Method 1: Port Forward (Easiest):**

```powershell
# Port forward Argo server to localhost
kubectl port-forward -n argo svc/argo-workflows-server 2746:2746

# Output:
# Forwarding from 127.0.0.1:2746 -> 2746
# Forwarding from [::1]:2746 -> 2746

# Open browser to: http://localhost:2746
```

**Method 2: Minikube Service:**

```powershell
minikube service argo-workflows-server -n argo

# This automatically opens browser to Argo UI
```

**What you'll see in the UI:**
- Workflows (list of all workflow runs)
- Workflow Templates
- Cron Workflows
- Logs and status for each workflow

---

### **Step 8: Install Apache Doris** (Optional - if not already installed)

**Note:** In your project, Doris is already installed on `192.168.29.181`. If you need to install it:

**Installation on Linux/Ubuntu:**

```bash
# Download Doris
wget https://downloads.apache.org/doris/2.1.0/apache-doris-2.1.0-bin-x64.tar.gz

# Extract
tar -xzf apache-doris-2.1.0-bin-x64.tar.gz

# Start FE (Frontend)
cd apache-doris-2.1.0/fe
./bin/start_fe.sh --daemon

# Start BE (Backend)
cd ../be
./bin/start_be.sh --daemon

# Connect using MySQL client
mysql -h 127.0.0.1 -P 9030 -u root
```

**In your project:**
Doris is already running at:
- Host: `192.168.29.181`
- Port: `9030` (MySQL protocol)
- Port: `8030` (HTTP/FE)

**Test Connection:**
```powershell
# From Windows (using MySQL client)
mysql -h 192.168.29.181 -P 9030 -u root

# Or using Python
python -c "import pymysql; conn = pymysql.connect(host='192.168.29.181', port=9030, user='root'); print('Connected!')"
```

---

### **Step 9: Install Python Dependencies** (For local testing)

**Installation:**

```powershell
# Navigate to project directory
cd C:\Users\singh\Desktop\Minikube-Doris

# Install Python packages
pip install pandas pymysql requests numpy

# Verify
python -c "import pandas; import pymysql; import requests; print('All packages installed!')"
```

**Packages we use:**
- **pandas**: Data manipulation (reading CSV, cleaning data)
- **pymysql**: Connect to Doris database
- **requests**: HTTP requests (for Doris HTTP API)
- **numpy**: Numerical operations

---

## 🚀 Project Setup Step-by-Step

Now that all tools are installed, let's set up our project!

### **Step 1: Create Project Structure**

```powershell
# Create main directory
mkdir C:\Users\singh\Desktop\Minikube-Doris
cd C:\Users\singh\Desktop\Minikube-Doris

# Create subdirectories
mkdir data
mkdir scripts
mkdir stage_test
mkdir error_files
mkdir pipeline_logs

# Create empty files
New-Item -Path checkpoint.txt -ItemType File
New-Item -Path table_map.json -ItemType File
```

**Directory Structure:**
```
Minikube-Doris/
├── data/                  # Source CSV files
│   ├── a.csv
│   ├── b.csv
│   └── ...
├── scripts/               # Python pipeline scripts
│   ├── pipeline_local.py
│   ├── 0_ingest.py
│   ├── discover_next_1.py
│   ├── 2_validate.py
│   ├── 3_transform.py
│   ├── 4_load_to_doris.py
│   ├── 6_checkpoint.py
│   └── local_config.py
├── stage_test/            # Staged/cleaned CSV files
├── error_files/           # Bad rows and schema mismatches
├── pipeline_logs/         # Log files
├── checkpoint.txt         # Tracks processed files
├── table_map.json         # Maps schemas to table names
└── argo-cron-pipeline.yaml  # Kubernetes CronWorkflow definition
```

---

### **Step 2: Mount Directory in Minikube**

**Why?**
We need Minikube to access our Windows folder so pods can read CSV files and write outputs.

**Command:**
```powershell
# Mount Windows directory to Minikube
minikube mount C:\Users\singh\Desktop\Minikube-Doris:/Minikube-Doris

# Output:
# 📁  Mounting host path C:\Users\singh\Desktop\Minikube-Doris into VM as /Minikube-Doris ...
#     ▪ Mount type:
#     ▪ User ID:      docker
#     ▪ Group ID:     docker
#     ▪ Version:      9p2000.L
#     ▪ Message Size: 262144
#     ▪ Options:      map[]
#     ▪ Bind Address: 127.0.0.1:xxxxx
# 🚀  Userspace file server: ufs starting
# ✅  Successfully mounted C:\Users\singh\Desktop\Minikube-Doris to /Minikube-Doris
```

**Important:**
- Keep this PowerShell window **open**
- If you close it, mount will disconnect
- Pods won't be able to access files

**Verify Mount:**
```powershell
# In a NEW PowerShell window
minikube ssh

# Inside Minikube VM
ls /Minikube-Doris
# Output: data  scripts  checkpoint.txt  table_map.json ...

exit
```

---

### **Step 3: Create Kubernetes CronWorkflow**

**File:** `argo-cron-pipeline.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: csv-doris-cron
  namespace: argo
spec:
  schedule: "*/5 * * * *"
  timezone: "America/New_York"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  workflowSpec:
    entrypoint: csv-to-doris
    volumes:
      - name: data-volume
        hostPath:
          path: /Minikube-Doris
          type: Directory
    templates:
      - name: csv-to-doris
        container:
          image: python:3.11-slim
          command: ["/bin/bash", "-c"]
          args:
            - |
              set -e
              echo "=== Installing dependencies ==="
              pip install --quiet pandas pymysql requests numpy
              
              echo "=== Running CSV to Doris Pipeline ==="
              cd /app/scripts
              python3 pipeline_local.py
              
              echo "=== Pipeline Complete ==="
          env:
            - name: DORIS_HOST
              value: "host.docker.internal"
            - name: DORIS_PORT
              value: "9030"
            - name: DORIS_USER
              value: "root"
            - name: DORIS_PASS
              value: ""
            - name: DORIS_DB
              value: "updated_test2"
            - name: DORIS_FE_HTTP_PORT
              value: "8030"
          volumeMounts:
            - name: data-volume
              mountPath: /app
```

**Apply the CronWorkflow:**
```powershell
kubectl apply -f argo-cron-pipeline.yaml

# Output:
# cronworkflow.argoproj.io/csv-doris-cron created
```

**Verify:**
```powershell
kubectl get cronwf -n argo

# Output:
# NAME              AGE
# csv-doris-cron    10s

argo cron list -n argo

# Output:
# NAME              AGE   LAST RUN   SCHEDULE       TIMEZONE
# csv-doris-cron    20s   N/A        */5 * * * *    America/New_York
```

---

### **Step 4: Test Manual Run** (Before waiting 5 minutes)

```powershell
# Trigger workflow manually
argo submit --from cronwf/csv-doris-cron -n argo --watch

# Output:
# Name:                csv-doris-cron-xxxxx
# Namespace:           argo
# ServiceAccount:      unset
# Status:              Pending
# Created:             Wed Nov 06 10:45:00 +0000 (now)
# Started:             Wed Nov 06 10:45:00 +0000 (now)
# Duration:            0 seconds
# Progress:            0/1
# 
# STEP                          TEMPLATE       PODNAME                      DURATION  MESSAGE
#  ● csv-doris-cron-xxxxx       csv-to-doris
#  └─◷ csv-to-doris             csv-to-doris   csv-doris-cron-xxxxx         0s
# 
# ... (logs streaming)
# 
# STEP                          TEMPLATE       PODNAME                      DURATION  MESSAGE
#  ✓ csv-doris-cron-xxxxx       csv-to-doris
#  └─✓ csv-to-doris             csv-to-doris   csv-doris-cron-xxxxx         45s
# 
# ✓ csv-doris-cron-xxxxx Succeeded
```

---

### **Step 5: View Logs**

**Method 1: Using argo CLI:**
```powershell
# List workflows
argo list -n argo

# View logs of latest workflow
argo logs -n argo @latest

# View logs with follow (live)
argo logs -n argo @latest -f
```

**Method 2: Using kubectl:**
```powershell
# Get pod name
kubectl get pods -n argo

# View logs
kubectl logs -n argo <pod-name>

# Follow logs (live)
kubectl logs -n argo <pod-name> -f
```

**Method 3: Argo Web UI:**
```powershell
# Port forward (in separate window)
kubectl port-forward -n argo svc/argo-workflows-server 2746:2746

# Open browser: http://localhost:2746
# Click on workflow → Click on pod → View logs
```

---

### **Step 6: Monitor Scheduled Runs**

**View CronWorkflow status:**
```powershell
kubectl get cronwf csv-doris-cron -n argo -o yaml

# Look for:
# status:
#   lastScheduledTime: "2025-11-06T10:45:00Z"
```

**View all workflow runs:**
```powershell
argo list -n argo

# Output:
# NAME                      STATUS      AGE   DURATION   PRIORITY   MESSAGE
# csv-doris-cron-1762411500 Succeeded   2m    45s        0
# csv-doris-cron-1762411200 Succeeded   7m    42s        0
# csv-doris-cron-1762410900 Succeeded   12m   48s        0
```

**View workflow details:**
```powershell
argo get csv-doris-cron-1762411500 -n argo

# Shows:
# - Status (Succeeded/Failed)
# - Duration
# - Parameters
# - Logs
```

---

## 🔧 How Everything Works Together

### **The Big Picture**

```
┌──────────────────────────────────────────────────────────────┐
│                    YOUR WINDOWS COMPUTER                      │
│                                                                │
│  C:\Users\singh\Desktop\Minikube-Doris\                      │
│  ├── data/                                                    │
│  │   ├── a.csv  ← You add new CSV files here                │
│  │   └── b.csv                                               │
│  └── scripts/                                                 │
│      └── pipeline_local.py  ← You edit Python code here     │
└─────────────────┬────────────────────────────────────────────┘
                  │
                  │ minikube mount (file sharing)
                  ↓
┌──────────────────────────────────────────────────────────────┐
│                    MINIKUBE (Mini Kubernetes)                 │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Namespace: argo                                         │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────┐          │  │
│  │  │ CronWorkflow: csv-doris-cron             │          │  │
│  │  │ Schedule: Every 5 minutes                │          │  │
│  │  └──────────┬───────────────────────────────┘          │  │
│  │             │ Triggers                                  │  │
│  │             ↓                                            │  │
│  │  ┌──────────────────────────────────────────┐          │  │
│  │  │ Workflow: csv-doris-cron-1762411500      │          │  │
│  │  │ (Created every 5 minutes)                │          │  │
│  │  └──────────┬───────────────────────────────┘          │  │
│  │             │ Spawns                                    │  │
│  │             ↓                                            │  │
│  │  ┌──────────────────────────────────────────┐          │  │
│  │  │ Pod: csv-doris-cron-1762411500           │          │  │
│  │  │ Image: python:3.11-slim                  │          │  │
│  │  │                                            │          │  │
│  │  │ 1. Install: pandas, pymysql               │          │  │
│  │  │ 2. Run: pipeline_local.py                 │          │  │
│  │  │ 3. Access: /app (mounted from Windows)    │          │  │
│  │  └──────────┬───────────────────────────────┘          │  │
│  │             │ Connects to                               │  │
│  └─────────────┼──────────────────────────────────────────┘  │
└────────────────┼─────────────────────────────────────────────┘
                 │
                 │ MySQL Protocol (port 9030)
                 ↓
┌──────────────────────────────────────────────────────────────┐
│                    APACHE DORIS DATABASE                      │
│                    192.168.29.181:9030                        │
│                                                                │
│  Database: updated_test2                                      │
│  Table: main_data_table                                       │
│  Data: Cleaned CSV rows with intelligent types                │
└──────────────────────────────────────────────────────────────┘
```

### **What Happens Every 5 Minutes**

**Time: 10:00:00**
1. Argo Workflow Controller: "It's time to run!"
2. Creates Workflow: `csv-doris-cron-1762411500`
3. Workflow creates Pod
4. Pod starts, pulls Python image
5. Pod runs `pipeline_local.py`:
   - Discovers CSV files in `/app/data/`
   - Reads `checkpoint.txt` to see what's already processed
   - FOR EACH unprocessed file:
     - Validate
     - Transform (clean data)
     - Load to Doris (with type detection & error handling)
     - Checkpoint
6. Pod finishes, exits
7. Workflow marked as "Succeeded"
8. Pod deleted (logs preserved)

**Time: 10:05:00**
- Process repeats with a new workflow ID

---

## 📚 Common Commands Reference

### **Minikube Commands**

```powershell
# Start Minikube
minikube start

# Stop Minikube
minikube stop

# Delete Minikube cluster (fresh start)
minikube delete

# Check status
minikube status

# SSH into Minikube VM
minikube ssh

# View Minikube IP
minikube ip

# Mount directory
minikube mount C:\path\to\folder:/mount-path

# Access service
minikube service <service-name> -n <namespace>

# Enable/disable addons
minikube addons list
minikube addons enable dashboard
```

---

### **kubectl Commands**

```powershell
# Cluster info
kubectl cluster-info
kubectl get nodes

# Namespaces
kubectl get namespaces
kubectl create namespace <name>

# Pods
kubectl get pods -n <namespace>
kubectl get pods -n argo
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> -f  # Follow logs
kubectl delete pod <pod-name> -n <namespace>

# Deployments
kubectl get deployments -n <namespace>
kubectl describe deployment <name> -n <namespace>

# Services
kubectl get svc -n <namespace>
kubectl port-forward -n <namespace> svc/<service-name> <local-port>:<service-port>

# CronWorkflows
kubectl get cronwf -n argo
kubectl describe cronwf <name> -n argo
kubectl delete cronwf <name> -n argo

# Workflows
kubectl get workflows -n argo
kubectl delete workflow <name> -n argo

# Apply YAML
kubectl apply -f <file.yaml>

# Get YAML of resource
kubectl get <resource> <name> -n <namespace> -o yaml

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

---

### **Argo Commands**

```powershell
# List workflows
argo list -n argo

# List cron workflows
argo cron list -n argo

# Submit workflow from CronWorkflow
argo submit --from cronwf/<cronwf-name> -n argo

# Submit workflow from file
argo submit -n argo workflow.yaml

# Get workflow details
argo get <workflow-name> -n argo

# View logs
argo logs <workflow-name> -n argo
argo logs @latest -n argo  # Latest workflow
argo logs -n argo @latest -f  # Follow latest

# Delete workflow
argo delete <workflow-name> -n argo

# Watch workflow (live updates)
argo submit --from cronwf/<name> -n argo --watch

# Suspend/resume CronWorkflow
argo cron suspend <cronwf-name> -n argo
argo cron resume <cronwf-name> -n argo
```

---

### **Helm Commands**

```powershell
# Add repository
helm repo add <repo-name> <repo-url>

# Update repositories
helm repo update

# Search charts
helm search repo <chart-name>

# Install chart
helm install <release-name> <repo/chart> -n <namespace>

# List installed releases
helm list -n <namespace>

# Upgrade release
helm upgrade <release-name> <repo/chart> -n <namespace>

# Uninstall release
helm uninstall <release-name> -n <namespace>

# Get values
helm get values <release-name> -n <namespace>

# Show chart info
helm show chart <repo/chart>
helm show values <repo/chart>
```

---

### **Docker Commands**

```powershell
# List containers
docker ps

# List all containers (including stopped)
docker ps -a

# List images
docker images

# Remove container
docker rm <container-id>

# Remove image
docker rmi <image-id>

# View logs
docker logs <container-id>

# Execute command
docker exec -it <container-id> /bin/bash

# Clean up
docker system prune  # Remove unused containers/images
```

---

### **Project-Specific Commands**

```powershell
# Clear checkpoint (reprocess all files)
Set-Content -Path "C:\Users\singh\Desktop\Minikube-Doris\checkpoint.txt" -Value "" -Encoding ASCII -NoNewline

# Delete table map (create fresh table)
Remove-Item "C:\Users\singh\Desktop\Minikube-Doris\table_map.json" -Force

# Clean error files
Get-ChildItem "C:\Users\singh\Desktop\Minikube-Doris\error_files" -Filter "error_*.csv" | Remove-Item -Force

# Clean staged files
Get-ChildItem "C:\Users\singh\Desktop\Minikube-Doris\stage_test" -Filter "staged_*.csv" | Remove-Item -Force

# View checkpoint
Get-Content "C:\Users\singh\Desktop\Minikube-Doris\checkpoint.txt"

# View table map
Get-Content "C:\Users\singh\Desktop\Minikube-Doris\table_map.json"

# Trigger manual workflow run
argo submit --from cronwf/csv-doris-cron -n argo --watch

# View live logs
kubectl logs -n argo -l workflows.argoproj.io/workflow --tail=200 -f

# Connect to Doris
mysql -h 192.168.29.181 -P 9030 -u root

# Query data
mysql -h 192.168.29.181 -P 9030 -u root -e "SELECT * FROM updated_test2.main_data_table LIMIT 10;"
```

---

## 🎓 Summary

**You now have:**
1. ✅ Understanding of what the project does
2. ✅ Knowledge of all technologies (Minikube, Kubernetes, Argo, Doris, Helm, kubectl)
3. ✅ Complete installation guide for all tools
4. ✅ Step-by-step project setup
5. ✅ Command reference for daily operations

**Next Steps:**
1. Add CSV files to `data/` folder
2. Wait 5 minutes (or trigger manually)
3. Check logs in Argo UI
4. Query database to see results
5. Review error files if any

**Key Takeaways:**
- Kubernetes = Container orchestration platform
- Minikube = Kubernetes on your laptop
- Argo Workflows = Kubernetes-native workflow engine
- CronWorkflow = Scheduled workflows (like cron jobs)
- Helm = Kubernetes package manager
- kubectl = Command-line tool for Kubernetes
- Doris = Analytics database

**The Magic:**
Every 5 minutes, your CSV files are automatically processed, cleaned, validated, and loaded into a production-grade database - all running in Kubernetes on your laptop! 🚀

---

*End of Documentation*
