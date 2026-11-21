# NAGARPRANALI+ Phase 4: UX & Usability Walkthrough Specification
**Sprint:** 4-Hour Convergence & Proof Sprint  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushalendra Yadav)  
**Date:** 2026-11-21  
**Project Root:** `VANA/finalvana/`  
**Git Remote:** `https://github.com/PriteshPatra-BHIV/finalvana.git` (`origin/main`)  

---

## 1. Executive Persona & Design Principles (Section 5 Compliance)

### Target User Persona
* **Name:** Ramesh Kulkarni (Age 52)
* **Profile:** Resident living near the Thane Creek buffer zone. First-time user of government digital apps. Smartphone user, prefers plain Marathi / Hindi or simple English.
* **Core Need:** Wants to report illegal debris dumping blocking a drainage culvert near the mangrove edge without filling complex forms, deciphering GIS codes, or creating passwords.

### Core Design Principles
1. **One Primary Action Per Screen:** No cluttered menus or multi-column option paralysis.
2. **Plain Language (Zero Jargon):** Avoid database terms like `SRID=4326`, `canopy density 0.65`, or `CR-e95e9174`.
3. **Transparent System Feedback:** Clearly state **(a) What we understood**, **(b) What was found**, and **(c) What happens next**.
4. **Anti-Dark-Pattern Doctrine:** No streaks, no fake urgency timers ("expires in 5 mins"), no forced account registration, and zero manipulative notifications.

---

## 2. Screen-by-Screen Citizen Walkthrough

### Screen 1: The One-Tap Citizen Report
```text
+-------------------------------------------------------------+
|  VANA + Nagarpranali Citizen Portal                         |
+-------------------------------------------------------------+
|                                                             |
|  [!] Report an Area Hazard or Green Cover Concern          |
|                                                             |
|  Tap the button below to check your location:               |
|                                                             |
|  +-------------------------------------------------------+  |
|  |                                                       |  |
|  |     [  CHECK MY AREA & REPORT HAZARD  ]               |  |
|  |              (One-Touch Locate)                       |  |
|  |                                                       |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  Language: [ English | हिन्दी | मराठी ]                       |
+-------------------------------------------------------------+
```

### Screen 2: System Understanding & Environmental Finding
```text
+-------------------------------------------------------------+
|  Area Environmental Check                                   |
+-------------------------------------------------------------+
|  [BADGE: Protected Green Zone]                              |
|                                                             |
|  Your area is inside Thane Creek Mangrove Reserve           |
|                                                             |
|  What We Understood:                                        |
|  - Location: Thane Creek, Mumbai Suburban                   |
|  - Category: Flood / Drainage & Green Cover Hazard          |
|                                                             |
|  Plain Explanation:                                         |
|  "This zone is officially recognized as an Eco-Sensitive   |
|   Coastal Zone. It has 65% dense mangrove cover which       |
|   naturally protects neighboring homes from monsoon floods."|
|                                                             |
|  Receipt Number: #CR-e95e9174                               |
|                                                             |
|  +-------------------------------------------------------+  |
|  |             [ PROCEED TO CONFIRM REPORT ]             |  |
|  +-------------------------------------------------------+  |
|  [ Back ]                                                   |
+-------------------------------------------------------------+
```

### Screen 3: Clear Outcome & What Happens Next
```text
+-------------------------------------------------------------+
|  Report Successfully Submitted                              |
+-------------------------------------------------------------+
|  [✓] Verified & Action Dispatched                           |
|                                                             |
|  What Happens Next:                                         |
|  1. Your report has been shared directly with the local     |
|     Statutory Forest Officer and Municipal Ward Cell.       |
|  2. Joint inspection teams have received synchronized alert |
|     tokens to inspect the culvert and mangrove buffer.      |
|  3. You will receive an SMS update once verified on-site.   |
|                                                             |
|  Assistance Note:                                           |
|  "No technical knowledge was required. Your area's green    |
|   protection has been safely recorded."                     |
|                                                             |
|  +-------------------------------------------------------+  |
|  |                     [ DONE ]                          |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

---

## 3. Plain-Language Translation Dictionary

| Raw Database / Technical Term | Citizen-Facing Plain English | Hindi Equivalent | Marathi Equivalent |
| :--- | :--- | :--- | :--- |
| `TC-Z03-F02` | Thane Creek Mangrove Reserve | ठाणे क्रीक मैंग्रोव अभयारण्य | ठाणे खाडी खारफुटी राखीव क्षेत्र |
| `tree_canopy_density: 0.65` | 65% Dense Tree & Mangrove Cover | 65% घना हरा आवरण | 65% दाट हिरवे आच्छादन |
| `Eco-Sensitive Coastal Zone 1` | Critical Flood-Protection Zone | बाढ़ सुरक्षा क्षेत्र | पूर संरक्षण क्षेत्र |
| `status: ABSTAIN, action: noop` | Standard Municipal Area (No forest hazard) | सामान्य नगर निगम क्षेत्र | सर्वसाधारण महानगरपालिका क्षेत्र |
| `CR-e95e9174-969b-...` | Official Receipt #CR-e95e9174 | आधिकारिक रसीद संख्या | अधिकृत पावती क्रमांक |

---

## 4. Confusion Points & Design Solutions Audit

| Identified Confusion Point | Root Cause | Implemented Design Fix |
| :--- | :--- | :--- |
| **"Do I need to sign up or remember a password?"** | Traditional portals force citizen registration before reporting. | **Zero-login intake:** Citizens can check zones and report directly without an account. |
| **"What does 'canopy density 0.65' mean?"** | Technical remote-sensing index confuses ordinary citizens. | **Plain translation:** Converted to percentage (65%) and explained as *"natural barrier against coastal floods"*. |
| **"Is this going to police, forest, or municipality?"** | Citizens do not know which jurisdiction applies to mangroves. | **Joint Dispatch Disclosure:** Clear feedback stating that *both* the Municipal Ward Cell and Forest Guard are notified together. |
| **"Did my report get lost?"** | Cryptic spinner with no confirmation receipt. | **Immutable Receipt Badge:** Immediate display of official record receipt `#CR-e95e9174`. |

---

## 5. Anti-Dark-Pattern Compliance Checklist (Section 5)

- [x] **Zero manipulative urgency:** No fake countdown clocks or "report within 5 minutes" alerts.
- [x] **Zero streak mechanics:** No gamification, points, or badges encouraging unnecessary submissions.
- [x] **Zero infinite scroll:** Compact single-screen layout with dedicated next/back actions.
- [x] **Complete transparency:** Every status clearly explains who owns the land and what action is being taken.
- [x] **Human override:** Citizens can pause, go back, or dismiss the guidance drawer at any time.
