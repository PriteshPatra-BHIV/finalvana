# Vana Project – 5-Group Deep Architectural Observation

## Executive Summary
The Vana project (incorporating the Manya/Niyantran ecosystems) operates as a heavily orchestrated, 5-tier pipeline encompassing spatial telemetric validation, decision governance, workflow execution, and machine learning visualization. Instead of a monolithic architecture, the system was divided across **5 Distinct Engineering Groups**, each owning a highly isolated step in the runtime execution chain. 

The architecture forms a sequential pipeline: `Group 1 -> Group 2 -> Group 3 -> Group 4 -> Group 5`.

---

## The 5-Group Breakdown

### **Group 1: Foundation & Canonical Records**
* **Repositories Maintained**: `vana-masterdb-foundation`, `bhiv-vana-masterdb-foundation`
* **Core Function**: Operates the `Observations API`. Group 1 forms the foundational data lake (MasterDB) that stores canonical records and external spatial datasets (like the FSI Forest Cover API). 
* **Runtime Contribution**: During live execution, Group 1 provides the base `canonical_record_id` and initial raw observation states. If the Group 1 API fails, the entire pipeline immediately halts.

### **Group 2: Context & Decision Brain (Niyantran)**
* **Repositories Maintained**: `bhiv-pravah` (Admin UI), Backend Context Brains
* **Core Function**: Group 2 serves as the governance authority. It takes the output from Group 1 and runs it through the *Niyantran* Context Brain. 
* **Runtime Contribution**: It issues cryptographic governance decisions based on available context. A major feature implemented recently is the **fail-closed ABSTAIN logic**. If certain required data is missing, Group 2 explicitly yields an `ABSTAIN` (noop) result with `action_eligibility: false`, preventing invalid state transitions. 

### **Group 3: Sensor Intake & Provenance Contracts**
* **Repositories Maintained**: `HECKAVERSE-GROUP-3` (Manya)
* **Core Function**: Defines the deterministic field observation contracts (e.g., Drone LIDAR captures, canopy parameters). It operates heavily in JSON schemas (`observation.schema.json`) and python semantic validator scripts (`validate_manya.py`).
* **Runtime Contribution**: This group enforces strict ID idempotency and provenance matching. Each field observation must cryptographically SHA-256 link back directly to its raw sensor logic, which guarantees that downstream groups never process spoofed or unverified spatial data.

### **Group 4: Intake Runtime & Governed Execution**
* **Repositories Maintained**: `bhiv-workflow-blackhole` (Infiverse BHL / Parikshak)
* **Core Function**: Group 4 is the effector system. Once Group 2 authorizes an action (or returns an abstention), Group 4 executes it via the Intake Runtime.
* **Runtime Contribution**: It physically operates the `vana/execute` engine. It handles workforce metrics, real-time live attendance (via Socket.IO), and idle-time processing based on the upstream deterministic contexts. It will explicitly register outcomes like `governed_abstention` if instructed by Group 2 without trying to calculate defaults.

### **Group 5: Lineage Visualization & ML Analytics**
* **Repositories Maintained**: `Vana_lineage_dashboard`, `Vana` (Cross-group Oversight)
* **Core Function**: Group 5 functions as the "Cross-group 5-tier lineage verification" and monitoring node. It runs the ML Bottleneck Analysis and frontend dashboards.
* **Runtime Contribution**: It utilizes a React-based Geospatial map and Admin Panel that sits on top of all 4 other groups. Group 5 fetches data concurrently from the live APIs (Group 1, Group 2, Group 4) via real-time proxy endpoints to display full lifecycle lineage to executive stakeholders.

---

## Conclusion
The architecture is intensely decoupled. The integration tests (such as `test_vana_cross_group_lineage.py`) prove that the Vana project behaves like a rigid state machine. Groups 1 through 4 pass tightly controlled JSON payloads across microservice boundaries, while Group 5 visually maps that exact cryptographical pipeline, ensuring full transparent observability over environmental observations and automated workforce actions.
