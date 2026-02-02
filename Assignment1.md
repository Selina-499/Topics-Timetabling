<style>
@import url('style.css');
</style>

## Project Plan

### Project Overview
The primary objective of this project is to determine the feasibility of consolidating the university estate by closing all Holyrood campus general teaching rooms. The project will investigate whether the existing Central campus general teaching rooms can absorb this teaching load, or if additional support from Lauriston or New College is required. 
Success of the project will be determined by whether we produce a feasible timetable that reallocates all Holyrood events while meeting the following criteria:
- Space Utilisation: Maintaining appropriate room-fill percentages (typically 50%-100%) and ensuring classes are matched to rooms with correct capacities.
- Student Travel: Adhering to pre-set travel time allowances between campuses to ensure students can reach consecutive events
- Timeslot Utilisation: Evaluating how consolidation affects the distribution of classes across the standard teaching week i.e Monday–Friday from 9 am to 6 pm.

Model scope will include room occupancy, course curricula, and travel time constraints between different campus locations while excluding staff assignments and accessibility requirements.

Modelling Approach???

### Responsibilities, deliverables and dependencies

|  Task ID |Task   | Deliverables  | Dependencies  |
|:---|:---|:---:|:---:|
|  1 |Data Extraction & Filtering: Isolate Holyrood, Central, Lauriston, and New College room data and relevant event data|  Cleaned Data Set | None  |   
|  2 |Model Formulation: Define hard constraints (no room clashes, curriculum conflicts) and soft constraints (travel time, room stability)| Optimisation Model  | T1  |
|  3 |Implementation: Code the model using solver| Codebase  | T2  |
|  4 | Scenario Testing: Run the solver specifically for the "Closure of Holyrood" scenario vs. the current baseline | Comparative Analysis  | T3  | 
|  5 | Analysis & Evaluation: Assess the impact on travel constraints and space utilisation | Final Results  | T4  |   



### Gannt Chart

```mermaid
gantt
    title University Estate Consolidation Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  W%V
    
    section Core Phases
    Data Extraction & Filtering (T1) :a1, 2024-02-05, 14d
    Model Formulation (T2)           :a2, after a1, 14d
    Implementation & Coding (T3)     :a3, after a2, 21d
    Scenario Testing (T4)            :a4, after a3, 7d
    Analysis & Evaluation (T5)       :a5, after a4, 7d

    section Key Deliverables
    Project Plan Submission          :milestone, m1, 2024-02-25, 0d
    Mid-project Report & Revised Plan :milestone, m2, 2024-03-17, 0d
    Final Report Delivery            :milestone, m3, 2024-04-14, 0d
    Final Presentation               :milestone, m4, 2024-04-16, 0d
```

### Risk Register

|  Risk Description |  Probability | Impact  | Mitigation |
|:---|:---:|:---:|:---|
| Infeasible Solution: The Central campus may not have enough capacity for all Holyrood events | Medium  | High  | Relax soft constraints. Expand the scope to include Lauriston or New College  |
|Model Complexity: Solver takes too long to reach an optimal solution | High  | Medium   | Use heuristics to find good feasible solutions quickly, or simplify the model   |  
| Data Uncertainty: Predictions for student enrollment or course choices may be inaccurate  | Medium  | Medium  | Build a robust model that can accommodate late changes or small fluctuations in student numbers  |  
| Team Coordination: Eventualities such as illness or a busier period due to other coursework  | Low  | High  |Use weekly workshop time for discussion and early check-ins with the course team. Set aside buffer week to cater for eventualities.  |

### What does success of the project look like

