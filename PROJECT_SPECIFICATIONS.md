# Database Access Simulation - Project Specifications

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [System Model](#system-model)
3. [Evaluation Scenarios](#evaluation-scenarios)
4. [Performance Metrics](#performance-metrics)
5. [Implementation Architecture](#implementation-architecture)
6. [Project Deliverables](#project-deliverables)
7. [Getting Started](#getting-started)

---

## Problem Statement

A database consists of **M tables** and is accessed concurrently by **N users** performing read or write operations. The goal is to simulate and analyze the performance of this concurrent database access system under different load conditions and access patterns. 

### System Parameters

- **M**: Number of tables in the database
- **N**: Number of concurrent users
- **T**: Inter-arrival time between accesses (exponentially distributed random variable)
- **S**: Fixed duration of each operation (read or write)
- **p**: Probability that an access is a read operation (1-p is the probability of a write)
- **m**: Index of the accessed table (random variable with specified distribution)

### Access Pattern

Each user accesses one table of the database every **T seconds**, where T is an exponentially distributed random variable with rate parameter λ = 1/T.

The index of the accessed table **m** is an independent and identically distributed (IID) random variable whose distribution follows one of the scenarios described below.

### Operation Types

Each access is:
- A **read operation** with probability **p**
- A **write operation** with probability **(1 - p)**

Both operations have a fixed duration of **S seconds**.

### Concurrency Control

The system implements the following concurrency rules:

1. **Multiple read operations** on the same table can be performed **simultaneously**
2. **Write operations** on a table must be executed in **mutual exclusion**:
   - Other read or write operations on the same table must be **serialized** when a write operation is being executed
3. **Important**: If a read operation on a table arrives when there is at least one **pending write operation** for that table, the read operation must **wait anyway** (to maintain consistency)

### Queuing Policy

Waiting operations are inserted in **per-table queues** and served according to **First Come First Served (FCFS)** policy.

## Evaluation Scenarios

### Distribution of Table Access (m)

Evaluate the system under at least the following scenarios:

1. **Uniform distribution**: All tables have equal probability of being accessed
   - m ~ Uniform(0, M-1)

2. **Lognormal distribution**: Some tables are "hotspots" (frequently accessed), while others are rarely accessed
   - m ~ Lognormal(μ, σ)
   - Creates realistic access patterns where certain tables receive more traffic

### Parameters to Vary

Evaluate the system for various values of:
- **N**: Number of users (e.g., 50, 100, 200)
- **p**: Read probability (e.g., 0.5, 0.8)

## Performance Metrics

The primary metric to evaluate is:

- **Number of served accesses per unit time** (throughput)

Additional recommended metrics:
- **Average waiting time** per operation
- **Average waiting time** for read operations
- **Average waiting time** for write operations
- **Table utilization** (especially for lognormal distribution)
## Implementation Architecture

### Project Structure

```
exam/
├── src/
│   ├── progetto/
│   │   ├── DatabaseNetwork.ned    # Network topology definition
│   │   ├── User.ned                # User module interface
│   │   ├── User.h                  # User module header
│   │   ├── User.cc                 # User module implementation
│   │   ├── Table.ned               # Table module interface
│   │   ├── Table.h                 # Table module header
│   │   └── Table.cc                # Table module implementation
│   ├── Makefile                    # Build configuration
│   └── exam                        # Compiled executable
├── simulations/
│   ├── omnetpp.ini                 # Simulation configuration
│   ├── run                         # Execution script
│   ├── results/                    # Simulation output files
│   │   ├── *.sca                   # Scalar results (statistics)
│   │   └── *.vec                   # Vector results (time series)
│   └── analyze_results.py          # Results analysis script
├── PROJECT_SPECIFICATIONS.md       # This file
└── README.md                       # Project overview
```

### Module Descriptions

#### 1. DatabaseNetwork.ned

**Purpose**: Defines the network topology connecting users and tables.

**Key Components**:
- Creates N user modules and M table modules
- Establishes full connectivity: each user connects to all tables
- Configures gate arrays for bidirectional communication

**Parameters**:
```
network DatabaseNetwork {
    parameters:
        int numUsers = default(50);
        int numTables = default(20);
    
    submodules:
        user[numUsers]: User;
        table[numTables]: Table;
    
    connections:
        // Full mesh: each user connected to all tables
        for i=0..numUsers-1, for j=0..numTables-1 {
            user[i].tableOut[j] --> table[j].userIn[i];
            table[j].userOut[i] --> user[i].tableIn[j];
        }
}
```

#### 2. User Module (User.ned, User.h, User.cc)

**Purpose**: Simulates a database user generating read/write requests.

**Behavior**:
1. **Request Generation**: 
   - Schedules next access using exponential distribution (rate λ)
   - Selects target table based on configured distribution (uniform or lognormal)
   - Determines operation type (read/write) based on probability p

2. **Request Sending**:
   - Creates request message with operation type and service time
   - Sends to selected table via appropriate gate

3. **Response Handling**:
   - Receives response from table
   - Records statistics (wait time, throughput)
   - Schedules next access

**Key Parameters**:
```ned
simple User {
    parameters:
        int userId;                      // Unique user identifier
        double lambda;                   // Request rate (1/T)
        double readProbability;          // Probability of read (p)
        int numTables;                   // Total number of tables
        string tableDistribution;        // "uniform" or "lognormal"
        double serviceTime @unit(s);     // Operation duration (S)
        double lognormalM = default(1.5); // Lognormal μ parameter
        double lognormalS = default(1.0); // Lognormal σ parameter
    
    gates:
        output tableOut[];   // Requests to tables
        input tableIn[];     // Responses from tables
}
```

**Statistics Collected**:
- `totalAccesses`: Total number of operations
## Getting Started

### Prerequisites

- **OMNeT++ 6.x** installed and configured
- **C++ compiler** (g++ or clang++)
- **Python 3.x** (for results analysis)
- **Git** (for version control)

### Building the Project

```bash
cd exam/src
make clean
make

# Verify build
./exam --version
```

### Running Simulations

**Option 1: Run all configurations**
```bash
cd exam/simulations

# Execute all Uniform runs (30 simulations)
../out/clang-release/src/exam -n ../src:. -u Cmdenv -c Uniform

# Execute all Lognormal runs (30 simulations)
../out/clang-release/src/exam -n ../src:. -u Cmdenv -c Lognormal
```

**Option 2: Run specific configuration**
```bash
# Run only N=50, p=0.8 case (5 replications)
../out/clang-release/src/exam -n ../src:. -u Cmdenv -c Uniform \
    -r 0..4 --**.numUsers=50 --**.user[*].readProbability=0.8
```

**Option 3: Interactive GUI**
```bash
# Launch OMNeT++ IDE
omnetpp

# Or run with GUI from command line
../out/clang-release/src/exam -n ../src:. -u Qtenv -c Uniform
```

### Analyzing Results

```bash
cd exam/simulations

# Run analysis script
python3 analyze_results.py

# Results saved in results/ directory
# - *.sca files: scalar statistics
# - *.vec files: time series data
```

### Quick Test

To verify everything works:

```bash
cd exam/simulations

# Short 100-second test run
../out/clang-release/src/exam -n ../src:. -u Cmdenv -c Uniform \
    --sim-time-limit=100s --repeat=1 --**.numUsers=10

# Check results
ls -lh results/
python3 analyze_results.py
```

### Troubleshooting

**Issue**: `Network 'DatabaseNetwork' not found`
- **Solution**: Ensure NED path includes src directory: `-n ../src:.`

**Issue**: `Gate index out of range`
- **Solution**: Gate sizes must be specified in DatabaseNetwork.ned

**Issue**: Compilation errors
- **Solution**: Check OMNeT++ installation with `omnetpp --version`

**Issue**: Python script errors
- **Solution**: Verify Python 3 with `python3 --version`

### Project Timeline

Recommended phases:

1. **Week 1**: Implementation and testing
   - Implement User and Table modules
   - Verify concurrency control logic
   - Test with simple scenarios

2. **Week 2**: Calibration and experiments
   - Calibrate parameters (N, M, λ, S, p)
   - Run all 60 simulations
   - Analyze preliminary results

3. **Week 3**: Analysis and documentation
   - Complete statistical analysis
   - Generate graphs and charts
   - Write documentation

4. **Week 4**: Presentation preparation
   - Create slides (max 10)
   - Practice presentation
   - Final review

### Key References

- **OMNeT++ Manual**: https://omnetpp.org/doc/omnetpp/manual/
- **OMNeT++ TicToc Tutorial**: Excellent starting point
- **Database Concurrency Control**: Any standard database textbook
- **Queueing Theory**: For theoretical validation of results

---

## Appendix: Expected Results

### Typical Throughput Values

| Configuration | N   | p   | Expected Throughput |
|--------------|-----|-----|---------------------|
| Uniform      | 50  | 0.8 | ~2.5 req/s         |
| Uniform      | 100 | 0.8 | ~5.0 req/s         |
| Uniform      | 200 | 0.8 | ~9-10 req/s        |
| Lognormal    | 50  | 0.8 | ~2.3 req/s         |
| Lognormal    | 100 | 0.8 | ~4.5 req/s         |
| Lognormal    | 200 | 0.8 | ~8 req/s           |

*Note: Lognormal typically shows lower throughput due to hotspot contention*

### Expected Wait Times

- **Low load (N=50)**: ~100-110 ms (close to service time)
- **Medium load (N=100)**: ~120-150 ms
- **High load (N=200)**: ~200-300 ms (significant queuing)
- **Lognormal**: 10-30% higher than Uniform (hotspot effect)

### Key Findings to Expect

1. **Throughput increases with N** (more concurrent users)
2. **Lognormal shows lower throughput** (hotspot contention)
3. **Higher p (more reads) improves performance** (less serialization)
4. **Wait times increase with N** (queuing effects)
5. **Lognormal creates high variance** (hot tables vs cold tables)

---

## Contact and Support

For questions or issues:
- Check OMNeT++ documentation: https://omnetpp.org
- Review simulation logs in `results/` directory
- Use `EV_INFO` logging in code for debugging
- Consult with course instructors during office hours
1. **State Variables**:
   - `activeReads`: Counter of concurrent read operations
   - `isWriting`: Boolean flag indicating active write
   - `readQueue`: Queue for pending read requests
   - `writeQueue`: Queue for pending write requests

2. **Request Processing Logic**:

   ```
   When READ request arrives:
   ├─ If writeQueue is NOT empty:
   │  └─ Enqueue in readQueue (must wait for pending writes)
   └─ Else if NOT writing:
      ├─ Process immediately (increment activeReads)
      └─ Schedule service completion after S seconds
   
   When WRITE request arrives:
   ├─ Enqueue in writeQueue
   └─ If NOT writing AND activeReads == 0:
      └─ Start processing (set isWriting = true)
   
   When READ completes:
   ├─ Decrement activeReads
   ├─ Send response to user
   └─ If activeReads == 0 AND writeQueue NOT empty:
      └─ Start next write
   
   When WRITE completes:
   ├─ Set isWriting = false
   ├─ Send response to user
   ├─ If writeQueue NOT empty:
   │  └─ Start next write
   └─ Else if readQueue NOT empty:
      └─ Start all pending reads (concurrent execution)
   ```

3. **FCFS (First Come First Served)**:
   - Separate queues for reads and writes maintain arrival order
   - Operations processed in order of arrival within type constraints

**Key Parameters**:
```ned
simple Table {
    parameters:
        int tableId;  // Unique table identifier
    
    gates:
        input userIn[];   // Requests from users
        output userOut[]; // Responses to users
}
```

**Statistics Collected**:
- `totalOperations`: Total operations processed
- `totalReads`: Number of reads served
- `totalWrites`: Number of writes served
- `averageQueueLength`: Mean queue size
- `utilizationTime`: Percentage of time busy

### Configuration File (omnetpp.ini)

**Purpose**: Defines simulation parameters and experiment configurations.

**Structure**:

```ini
[General]
network = progetto.DatabaseNetwork
sim-time-limit = 10000s        # Simulation duration
cpu-time-limit = 3600s          # Real-time limit (1 hour)

# Multiple replications for statistical significance
repeat = 5
seed-set = ${repetition}

# Output configuration
result-dir = results
output-scalar-file = ${resultdir}/${configname}-${iterationvars}-${repetition}.sca
output-vector-file = ${resultdir}/${configname}-${iterationvars}-${repetition}.vec

# Global parameters
*.numTables = 20
*.user[*].lambda = 0.05         # 1 request every 20 seconds
*.user[*].serviceTime = 0.1s    # 100ms operation time

# Experiment: Uniform Distribution
[Config Uniform]
description = "Uniform table access distribution"
*.user[*].tableDistribution = "uniform"
*.numUsers = ${N=50, 100, 200}              # Vary N
*.user[*].readProbability = ${p=0.5, 0.8}   # Vary p
# Generates: 3×2×5 = 30 runs

# Experiment: Lognormal Distribution  
[Config Lognormal]
description = "Lognormal distribution with hotspots"
*.user[*].tableDistribution = "lognormal"
*.user[*].lognormalM = 1.5
*.user[*].lognormalS = 1.0
*.numUsers = ${N=50, 100, 200}
*.user[*].readProbability = ${p=0.5, 0.8}
# Generates: 3×2×5 = 30 runs
```

**Parameter Sweep Explanation**:
- `${N=50, 100, 200}`: Tests three different user loads
- `${p=0.5, 0.8}`: Tests 50% and 80% read ratios
- `repeat = 5`: Each configuration runs 5 times with different random seeds
- **Total runs**: 2 configs × 3 N values × 2 p values × 5 repetitions = **60 simulations**

### Results Analysis (analyze_results.py)

**Purpose**: Parses OMNeT++ output files and generates statistical summaries.

**Functionality**:
1. Reads `.sca` (scalar statistics) files from `results/` directory
2. Extracts metrics for each user and table
3. Aggregates statistics across users and repetitions
4. Computes means, standard deviations, and confidence intervals
5. Compares Uniform vs Lognormal distributions
6. Generates text reports and (optionally) graphs

**Usage**:
```bash
cd simulations
python3 analyze_results.py
```

**Output Example**:
```
Uniform_50u_p0.8
  N=50 users, p=0.8 (prob. read)
  Repetitions: 5
  ─────────────────────────────────
  Accesses total: 24,850 ± 125
  Reads: 19,880 (80.0%)
  Writes: 4,970 (20.0%)
  System throughput: 2.485 ± 0.012 req/s
  Average wait time: 100.2 ± 0.5 ms
```

## Validation

### Correctness Checks

1. **Concurrent Reads Validation**:
   - Monitor `activeReads` counter in Table module
   - Verify multiple reads execute simultaneously
   - Check: Max `activeReads` > 1 for high-load scenarios

2. **Write Exclusion Validation**:
   - Verify `isWriting` flag prevents concurrent operations
   - Check: Only one write at a time per table
   - Validate: Reads blocked when `writeQueue` not empty

3. **FCFS Verification**:
   - Log timestamps of request arrival and service start
   - Verify operations processed in arrival order (within type)
   - Check queue ordering is maintained

4. **Statistical Validation**:
   - **Exponential inter-arrivals**: Plot and fit histogram
   - **Distribution of m**: Verify uniform/lognormal shape
   - **Read/Write ratio**: Should match configured p value

### Performance Validation

1. **Sanity Checks**:
   - Wait time ≥ service time (S)
   - Throughput ≤ theoretical maximum
   - Under low load: wait time ≈ service time

2. **Load Scaling**:
   - As N increases → throughput increases (until saturation)
   - As N increases → wait time increases (queuing delays)

3. **Distribution Effects**:
   - Lognormal should show higher wait times (hotspot contention)
   - Few tables in lognormal should have high utilization

## Project Deliverablestics** per table

## Calibration Requirements

The team must calibrate the scenarios to obtain **meaningful results**:

- Choose appropriate values for M, S, and λ
- Ensure the system operates in interesting regimes (not over-saturated, not under-utilized)
- Select lognormal parameters (μ, σ) that create realistic hotspot behavior
- Run multiple replications with different random seeds for statistical significance

## Project Deliverables

### a) Documentation

Following the standards set during the lectures, the documentation must include:

1. **System Model Description**
   - Detailed description of the implemented model
   - State diagrams or flowcharts
   - Assumptions and simplifications

2. **Implementation Details**
   - Architecture and key design decisions
   - Concurrency control mechanism
   - Queue management implementation

3. **Experimental Setup**
   - Parameter calibration rationale
   - Chosen values for M, N, S, T, p
   - Lognormal distribution parameters
   - Number of replications and simulation length

4. **Results and Analysis**
   - Performance metrics for all scenarios
   - Comparison between uniform and lognormal distributions
   - Impact of varying N and p
   - Statistical analysis (mean, standard deviation, confidence intervals)
   - Graphs and charts

5. **Conclusions**
   - Key findings
   - System behavior insights
   - Limitations and future work

### b) Simulator Code

Provide well-documented source code including:
- Network description (.ned files)
- Module implementation (.cc, .h files)
- Configuration file (omnetpp.ini)
- Build instructions

### c) Presentation

Maximum **10 slides** covering:
1. Problem description
2. System model
3. Implementation approach
4. Experimental methodology
5. Key results
6. Conclusions

## Implementation Notes

### Suggested Parameter Values

Based on realistic database systems:

- **M = 20** tables
- **N = 50, 100, 200** users (to vary)
- **S = 0.1 seconds** (100ms, typical for simple queries)
- **λ = 0.05** (mean inter-arrival time T = 20 seconds per user)
- **p = 0.5, 0.8** (50% or 80% reads)

### Lognormal Parameters

For creating hotspot behavior:
- **μ = 1.5**
- **σ = 1.0**

This configuration ensures most accesses concentrate on a few tables (indices 0-10) while others are rarely accessed.

### Simulation Length

- **Simulation time**: 10,000 seconds (sufficient for steady-state analysis)
- **Replications**: At least 5 runs with different seeds per configuration
- **Warm-up period**: Consider discarding initial transient if necessary

## Validation

Ensure the implementation correctly handles:

1. **Concurrent reads**: Multiple users can read the same table simultaneously
2. **Write exclusion**: Only one write at a time per table
3. **Read blocking**: Reads must wait if writes are pending
4. **FCFS ordering**: Operations served in arrival order per table
5. **Statistical correctness**: Exponential inter-arrivals, correct distribution of table indices

## Success Criteria

The project is successful if:

1. All concurrency rules are correctly implemented
2. Results show meaningful differences between scenarios
3. Lognormal distribution clearly shows hotspot effects
4. Statistical analysis is rigorous (multiple replications, confidence intervals)
5. Documentation is complete and clear
6. Code is well-structured and documented
7. Presentation effectively communicates key findings
