# To-Do List App

A clean, dependency-free task manager written in pure Python. It shows how to
model a real problem with **object-oriented programming**, apply the
**SOLID principles**, validate input, and expose a small, well-documented API
for **CRUD operations**, filtering, sorting and statistics.

## Features

- **Task management (CRUD)**: add, view, edit and delete tasks
- **Priorities**: `low`, `medium`, `high`
- **Due dates**: as a `date` object or an ISO string (`YYYY-MM-DD`)
- **Status workflow**: `pending` → `in progress` → `completed`
- **Overdue detection** and **upcoming tasks** (due within N days)
- **Filtering** by status, priority, overdue, due window or keyword, and
  filters can be combined
- **Sorting** by id, title, priority, due date, status or creation time
- **Statistics**: totals by status and priority, overdue count, completion rate
- **Validation and clear errors** through a custom exception hierarchy
- **No external libraries**: standard library only

## Requirements

- Python 3.8 or newer
- No third-party packages (see `requirements.txt`)

## Installation

```bash
git clone https://github.com/khaledkamel1818/todo-list-app.git
cd todo-list-app/todo_app
```

## Usage

Run the built-in demo, which walks through every feature:

```bash
python todo.py
```

Or use it as a module:

```python
from todo import TaskManager, Priority, Status, by_priority, by_status

manager = TaskManager()

# Create
task = manager.add_task(
    "Write project README",
    description="Usage, examples, OOP notes",
    priority="high",            # or Priority.HIGH
    due_date="2024-06-11",      # or a datetime.date
)

# Read
manager.get_task(task.task_id)

# Update
manager.edit_task(task.task_id, title="Write a great README", priority="medium")
manager.start_task(task.task_id)      # pending -> in progress
manager.complete_task(task.task_id)   # -> completed

# Filter and sort
high_open = manager.list_tasks(
    filters=[by_priority("high"), by_status(Status.PENDING)],
    sort_by="due_date",
)
manager.overdue_tasks()
manager.upcoming_tasks(days=7)
manager.search_tasks("readme")

# Statistics
print(manager.statistics())

# Delete
manager.delete_task(task.task_id)
manager.clear_completed()
```

## Project Structure

```
todo_app/
├── todo.py            # All classes plus a runnable demo
├── README.md          # This file
└── requirements.txt   # No external dependencies
```

## Classes and Functions

### `Priority` (Enum)
`LOW`, `MEDIUM`, `HIGH`. The value is the sort weight.
`Priority.parse("high")` accepts a name (case-insensitive) or a member.

### `Status` (Enum)
`PENDING`, `IN_PROGRESS`, `COMPLETED`.

### `Task`
A single to-do item that validates its own data and controls its state.

| Member | Description |
|---|---|
| `task_id`, `title`, `description`, `priority`, `due_date`, `status`, `created_at`, `completed_at` | Read-only properties |
| `update(title=, description=, priority=, due_date=, clear_due_date=)` | Edit fields; validated all at once, so a failed edit changes nothing |
| `start()` | `pending` → `in progress` |
| `complete()` | Mark as completed and record the time |
| `is_overdue(today=None)` | True if open and past its due date |
| `days_until_due(today=None)` | Days left (negative when overdue) |
| `to_dict()` | JSON-friendly dictionary |

### `TaskRepository` (abstract) and `InMemoryTaskRepository`
The storage interface (`add`, `get`, `remove`, `all`, `next_id`) and a
dictionary-based implementation. IDs are never reused.

### `TaskManager`
The service layer used by applications.

| Method | Description |
|---|---|
| `add_task(title, description=None, priority="medium", due_date=None)` | Create a task |
| `get_task(task_id)` | Fetch a task |
| `edit_task(task_id, **changes)` | Edit a task |
| `start_task(task_id)` / `complete_task(task_id)` | Change status |
| `delete_task(task_id)` / `clear_completed()` | Remove tasks |
| `list_tasks(filters=(), sort_by="id", reverse=False)` | Filter and sort |
| `overdue_tasks()` / `upcoming_tasks(days=7)` / `search_tasks(keyword)` | Shortcuts |
| `statistics()` | Summary dictionary |
| `display_tasks(tasks=None, heading="All tasks")` | Print a table |

### Filter factories
`by_status(status)`, `by_priority(priority)`, `overdue(today)`,
`due_within(days, today)`, `search(keyword)`. Each returns a
`Callable[[Task], bool]`; pass several to `list_tasks` to combine them.

### Exceptions

```
TodoError
├── ValidationError     (also a ValueError)
├── TaskNotFoundError   (also a KeyError)
└── InvalidStateError
```

## OOP Concepts Used

- **Encapsulation**: `Task` keeps its fields private and exposes read-only
  properties; changes go through methods that validate input and enforce the
  status workflow.
- **Abstraction**: `TaskRepository` defines *what* storage does, not *how*.
- **Inheritance**: the exception hierarchy, and `InMemoryTaskRepository`
  extending `TaskRepository`.
- **Polymorphism**: any `TaskRepository` implementation works with
  `TaskManager`; any filter function works with `list_tasks`.
- **Composition**: `TaskManager` *has a* repository rather than *being* one.

### SOLID

| Principle | Where |
|---|---|
| **S**ingle Responsibility | `Task` models one task, the repository stores, `TaskManager` coordinates |
| **O**pen/Closed | New filters and sort keys are added without editing `TaskManager` |
| **L**iskov Substitution | Any `TaskRepository` subclass can replace the in-memory one |
| **I**nterface Segregation | The repository interface has only the five operations the manager needs |
| **D**ependency Inversion | `TaskManager` depends on the `TaskRepository` abstraction and an injected clock |

## Expected Output

Running `python todo.py` prints (abridged):

```
========================================================================
 TO-DO LIST APP - DEMO
========================================================================

All tasks (6)
------------------------------------------------------------------------
  [ ] #1   Write project README            HIGH   pending     2024-06-11
  [ ] #2   Fix login bug                   HIGH   pending     2024-06-08  ! OVERDUE
  [ ] #3   Buy groceries                   LOW    pending     2024-06-13
  [ ] #4   Prepare interview notes         MEDIUM pending     2024-06-15
  [ ] #5   Read Clean Code chapter 3       LOW    pending     no due date
  [ ] #6   Refactor task module            MEDIUM pending     2024-06-09  ! OVERDUE

After editing, starting and completing (6)
------------------------------------------------------------------------
  [ ] #1   Write project README            HIGH   in progress 2024-06-11
  [ ] #2   Fix login bug                   HIGH   pending     2024-06-08  ! OVERDUE
  [x] #3   Buy groceries                   LOW    completed   2024-06-13
  [ ] #4   Prepare Python interview notes  HIGH   pending     2024-06-15
  [ ] #5   Read Clean Code chapter 3       LOW    pending     no due date
  [x] #6   Refactor task module            MEDIUM completed   2024-06-09

Overdue tasks (1)
------------------------------------------------------------------------
  [ ] #2   Fix login bug                   HIGH   pending     2024-06-08  ! OVERDUE

...

Statistics
------------------------------------------------------------------------
  Total tasks      : 6
  By status        : {'pending': 3, 'in progress': 1, 'completed': 2}
  By priority      : {'low': 2, 'medium': 1, 'high': 3}
  Overdue          : 1
  Completion rate  : 33.3%

Deleted: 'Read Clean Code chapter 3'
Cleared 2 completed task(s); 3 task(s) left.

Error handling
------------------------------------------------------------------------
  Empty title            -> ValidationError: Title must be a non-empty string.
  Unknown priority       -> ValidationError: Priority must be one of: low, medium, high.
  Missing task           -> TaskNotFoundError: Task #99 not found.
  Start a started task   -> InvalidStateError: Only pending tasks can be started; task #1 is in progress.
  ...
```

The demo uses a fixed date (2024-06-10), so its output is the same on every run.

## Possible Extensions

- A JSON or SQLite `TaskRepository` for persistence
- A command-line interface with `argparse`
- Unit tests with `unittest` or `pytest`
- Tags and recurring tasks

## Author

**Khaled Kamel** · [GitHub](https://github.com/khaledkamel1818)

## License

This project is open source and available for learning purposes.
