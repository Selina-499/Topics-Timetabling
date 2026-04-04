# University Timetabling Optimisation – README

## 1. Project Overview

This project investigates the university timetabling problem through four distinct computational modelling approaches:

- **`heuristic.py`** – A heuristic-based timetabling model
- **`MILP.py`** – A Mixed-Integer Linear Programming (MILP) formulation
- **`GA.py`** – A Genetic Algorithm (GA) implementation
- **`Finalest Model.ipynb`** – An extended MILP formulation incorporating inter-campus travel time constraints

All four models operate on the same four pre-processed CSV datasets as input. The notebook `main.ipynb` serves exclusively as a data preprocessing pipeline and does not need to be executed in order to run the optimisation models.

---

## 2. Required Files

All files must reside in the same working directory unless file paths are explicitly modified within the source code.

### Code Files
| File | Description |
|---|---|
| `heuristic.py` | Heuristic-based timetabling model |
| `MILP.py` | Mixed-Integer Linear Programming model |
| `GA.py` | Genetic Algorithm model |
| `Finalest Model.ipynb` | Extended MILP model with travel time constraints |

### Input Data Files
| File | Description |
|---|---|
| `Event_data.csv` | Teaching event definitions |
| `Rooms_data.csv` | Available room specifications |
| `Semester1_data.csv` | Academic calendar structure |
| `Student_data.csv` | Student–event enrolment relationships |

### Optional
| File | Description |
|---|---|
| `main.ipynb` | Data preparation notebook (not required for model execution) |

---

## 3. Data Preparation

The datasets were extracted and filtered from a university timetabling database. All preprocessing steps are implemented in `main.ipynb` and include:

- Filtering the room dataset to retain only General Teaching Rooms
- Cleaning and preparing event information
- Extracting week structures from the semester calendar
- Constructing student–event enrolment relationships used for conflict detection

The outputs of this preprocessing pipeline are the four CSV files listed above. These files are ready-to-use and do not require re-generation prior to running the models.

---

## 4. Running the Models

Ensure all required files are present in the same directory before execution. Each model is run independently via the command line.

### Heuristic Model

```bash
python heuristic.py
```

### MILP Model

```bash
python MILP.py
```

### Genetic Algorithm Model

```bash
python GA.py
```

### Extended MILP Model with Travel Time (Finalest Model)

```bash
jupyter notebook "Finalest Model.ipynb"
```

Open the notebook in Jupyter and execute all cells sequentially. Note that this model incorporates inter-campus travel time constraints into the MILP formulation, which results in substantially longer computational runtimes compared to the other models.

---

## 5. Data File Descriptions

### `Event_data.csv`
Defines all teaching events to be scheduled.

| Attribute | Description |
|---|---|
| Event ID | Unique event identifier |
| Event Name | Name of the teaching activity |
| Event Size | Number of enrolled students |
| Campus | Campus location (if pre-assigned) |
| Number of Weeks | Number of weeks the event runs |
| Weeks | Week pattern string |
| Week List | List of specific week numbers |
| Room | Pre-assigned room (if applicable) |
| Building | Pre-assigned building (if applicable) |
| Timeslot | Pre-assigned timeslot (if applicable) |
| Duration (minutes) | Duration of the event in minutes |

### `Rooms_data.csv`
Defines the available teaching rooms.

| Attribute | Description |
|---|---|
| Id | Unique room identifier |
| Room_Number | Room code |
| Room_Type | Classification of teaching room type |
| Capacity | Maximum seating capacity |
| Campus | Campus location |
| Building_Code | Building identifier |
| Building_Name | Full building name |
| Capacity_Category | Size-based classification |

### `Semester1_data.csv`
Defines the academic calendar for the semester.

| Attribute | Description |
|---|---|
| Week Number | Sequential week index |
| Date Commencing | Start date of the week |
| Week Label | Descriptive label for the week |
| Week Type | Classification (e.g., Teaching Week, Exam Week) |
| Date Ending | End date of the week |
| Academic Year | Academic year identifier |

### `Student_data.csv`
Defines the relationship between students and the events they are enrolled in. This dataset is used to detect scheduling conflicts between events.

| Attribute | Description |
|---|---|
| AnonID | Anonymised student identifier |
| Department | Student's department |
| Programme | Degree programme |
| Event ID | Enrolled event identifier |
| Course Name | Course or module name |

---

## 6. Notes

- All model files and input data files must remain in the same directory unless file paths are manually updated within the source code.
- `main.ipynb` is provided for transparency regarding the data preparation process and does not need to be re-executed prior to running any of the models.
- `Finalest Model.ipynb` extends the MILP formulation by incorporating inter-campus travel time as an additional scheduling constraint. Due to the increased problem complexity introduced by this constraint, this model requires significantly longer computational time to solve than the other implementations.
- **`heuristic.py` is the preferred model for this project.** While `Finalest Model.ipynb` represents a more comprehensive formulation, its computational overhead makes it less practical. The heuristic approach was selected as the primary implementation on the basis of its efficiency and suitability for the problem at scale.
