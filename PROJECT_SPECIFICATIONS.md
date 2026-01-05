# Database Access Simulation - Project Specifications

## Problem Statement

A database consists of **M tables** and is accessed concurrently by **N users** performing read or write operations. 

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
- **Queue length statistics** per table

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
