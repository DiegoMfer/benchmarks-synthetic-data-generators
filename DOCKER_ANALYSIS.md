# Docker Dependency Analysis - RDF Synthetic Data Generators

**Analysis Date:** January 22, 2026  
**Status:** Docker daemon is NOT running / Not accessible  
**Result:** 4/10 generators succeeded, 6/10 failed

---

## Summary

The `generate_all_datasets.py` script attempted to run all 10 generator variants. **Only 4 succeeded** because they do NOT require Docker. The **6 that failed** all depend on Docker, which is not running or not accessible to the current user.

### Docker Access Issue
```
Error: permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

---

## Detailed Generator Status

### ✅ SUCCESSFUL GENERATORS (4/10)
These do **NOT** require Docker and run locally with Java/Python:

| Generator | Type | Method | Status |
|-----------|------|--------|--------|
| **BSBM** | Java JAR | Direct Java execution | ✅ Working |
| **LUBM** | Java JAR | Direct Java execution | ✅ Working |
| **GAIA** | Java JAR | Direct Java execution | ✅ Working |
| **LINKGEN** | Java JAR | Direct Java execution | ✅ Working |

**Output Location:** `1-Datasets/{GENERATOR}/run_2/`

---

### ❌ FAILED GENERATORS (6/10)
These **REQUIRE Docker** and failed due to Docker not being accessible:

#### 1. **PYGRAFT** 
- **Error:** `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`
- **Reason:** Uses Docker container execution
- **How it runs:** `docker run --rm -v <output>:/app/output pygraft-benchmark:latest ...`
- **Location in code:** [generate_all_datasets.py#L253-L276](generate_all_datasets.py#L253-L276)

#### 2. **RDFGRAPHGEN** 
- **Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'rdfgen'`
- **Reason:** Requires external binary `rdfgen` which is either:
  - Not installed on the system, OR
  - Only available inside Docker container
- **Location in code:** [RDFGRAPHGEN/execute_benchmark.py](RDFGRAPHGEN/execute_benchmark.py)

#### 3. **RDFGRAPHGEN_LUBM** 
- **Error:** Same as RDFGRAPHGEN (missing `rdfgen` binary)
- **Reason:** Uses LUBM shape file variant, but same binary dependency issue

#### 4. **RUDOFGENERATE** 
- **Error:** `permission denied while trying to connect to the Docker daemon socket`
- **Reason:** Uses `docker compose` to build and run
- **How it runs:** `docker compose build` → `docker compose run rudofgenerate`
- **Location in code:** [generate_all_datasets.py#L328-L355](generate_all_datasets.py#L328-L355)

#### 5. **RUDOFGENERATE_LUBM_SHEX** 
- **Error:** Same as RUDOFGENERATE (Docker permission denied)
- **Reason:** Docker compose variant with different schema

#### 6. **RUDOFGENERATE_LUBM_SHACL** 
- **Error:** Same as RUDOFGENERATE (Docker permission denied)
- **Reason:** Docker compose variant with SHACL schema

---

## Root Causes

### Primary Issue: Docker Daemon Not Running
```bash
$ docker ps
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

**Why this happens:**
1. Docker daemon (`dockerd`) is not running
2. OR current user (`benchmark`) lacks permissions to access `/var/run/docker.sock`

### Secondary Issue: Missing Binary in RDFGRAPHGEN
The `rdfgen` binary is not on the system PATH. This generator needs either:
- The binary installed locally, OR
- Docker container to provide it

---

## How Generators Are Implemented

### Type 1: Pure Java/Python (No Docker)
```
BSBM, LUBM, GAIA, LINKGEN
├── Invoke: subprocess.run(['java', '-cp', 'jar-file', ...])
└── Dependency: Java 8+ only
```

### Type 2: Docker Container Execution
```
PYGRAFT
├── Invoke: docker run --rm -v <output>:/app/output <image> <command>
└── Dependency: Docker daemon running + built image
```

### Type 3: Docker Compose
```
RUDOFGENERATE (all variants)
├── Build: docker compose build
├── Run: docker compose run --rm <service>
└── Dependency: Docker daemon running + docker-compose
```

### Type 4: External Binary (Docker-compatible)
```
RDFGRAPHGEN (all variants)
├── Invoke: rdfgen <args>
└── Dependency: Either local binary or Docker container
```

---

## Solutions

### Option 1: Start Docker Daemon (Recommended)
```bash
# Start Docker daemon
sudo systemctl start docker

# OR if Docker is installed but daemon needs activation
docker-machine start default

# Verify it's running
docker ps
```

### Option 2: Add User to Docker Group (Avoid sudo requirement)
```bash
# Add current user to docker group
sudo usermod -aG docker benchmark

# Apply new group (logout/login OR)
newgrp docker

# Verify access
docker ps
```

### Option 3: Run Generate Script with Sudo
```bash
sudo python3 generate_all_datasets.py
```

### Option 4: Install Missing Binaries Locally
For RDFGRAPHGEN, install `rdfgen`:
```bash
# Option A: Build from source
# (Check RDFGraphGen GitHub repository)

# Option B: Use binary release
# (Download and add to PATH)
```

### Option 5: Selective Generation (Skip Docker Generators)
```bash
# Run only generators that don't need Docker
python3 generate_all_datasets.py --generators BSBM LUBM GAIA LINKGEN
```

---

## Generator Matrix

| Generator | Java | Python | Docker | Binary | Status |
|-----------|------|--------|--------|--------|--------|
| BSBM | ✅ | - | - | - | ✅ Works |
| LUBM | ✅ | - | - | - | ✅ Works |
| GAIA | ✅ | - | - | - | ✅ Works |
| LINKGEN | ✅ | - | - | - | ✅ Works |
| PYGRAFT | - | ✅ | ✅ | - | ❌ Docker needed |
| RDFGRAPHGEN | - | ✅ | ? | ✅ (rdfgen) | ❌ Binary not found |
| RDFGRAPHGEN_LUBM | - | ✅ | ? | ✅ (rdfgen) | ❌ Binary not found |
| RUDOFGENERATE | - | ✅ | ✅ | - | ❌ Docker needed |
| RUDOFGENERATE_LUBM_SHEX | - | ✅ | ✅ | - | ❌ Docker needed |
| RUDOFGENERATE_LUBM_SHACL | - | ✅ | ✅ | - | ❌ Docker needed |

---

## Generated Datasets

```
1-Datasets/
├── BSBM/run_2/
│   ├── dataset.ttl
│   ├── benchmark_report.json
│   └── metadata.json
├── LUBM/run_2/
│   ├── University*.owl (many files)
│   ├── benchmark_report.json
│   └── metadata.json
├── GAIA/run_2/
│   ├── gaia_instances.owl
│   ├── benchmark_report.json
│   └── metadata.json
├── LINKGEN/run_2/
│   ├── data_T*.owl (multiple files)
│   ├── void.ttl
│   ├── benchmark_report.json
│   └── metadata.json
└── INDEX.md
```

---

## Next Steps

1. **Check Docker Status:** `sudo systemctl status docker`
2. **Start Docker:** `sudo systemctl start docker` or `docker-machine start`
3. **Verify Access:** `docker ps` should list containers (even if empty)
4. **Re-run Generator:** `python3 generate_all_datasets.py`
5. **Monitor Failures:** Check stderr for any remaining issues

---

## Files Modified/Created

- ✅ Generated: `1-Datasets/` directory with 4 successful generator outputs
- ✅ Generated: `1-Datasets/INDEX.md` index file
- ℹ️ This analysis: `DOCKER_ANALYSIS.md`
