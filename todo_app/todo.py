"""
To-Do List Application.

A small, dependency-free task manager written in pure Python. It
demonstrates object-oriented design and the SOLID principles:

* ``Priority`` / ``Status``  - enumerations describing a task.
* ``Task``                   - a single task with its own validation and
                               state transitions (pending -> in progress ->
                               completed).
* ``TaskRepository``         - an abstract storage interface.
* ``InMemoryTaskRepository`` - a dictionary-backed implementation.
* ``TaskManager``            - the service layer: CRUD, filtering, sorting
                               and statistics.

Run this file directly to see a full demonstration::

    python todo.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Iterable, List, Optional, Union


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

class TodoError(Exception):
    """Base class for every error raised by this module."""


class ValidationError(TodoError, ValueError):
    """Raised when input data is invalid (empty title, bad date...)."""


class TaskNotFoundError(TodoError, KeyError):
    """Raised when a task ID does not exist."""

    def __str__(self) -> str:  # KeyError would otherwise wrap it in quotes
        return str(self.args[0]) if self.args else ""


class InvalidStateError(TodoError):
    """Raised when a state transition is not allowed (e.g. editing a
    completed task)."""


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------

class Priority(Enum):
    """How important a task is. The value doubles as its sort weight."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, value: Union["Priority", str]) -> "Priority":
        """Accept a ``Priority`` or its name (case-insensitive)."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls[value.strip().upper()]
            except KeyError:
                pass
        names = ", ".join(p.name.lower() for p in cls)
        raise ValidationError(f"Priority must be one of: {names}.")


class Status(Enum):
    """The lifecycle state of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

MAX_TITLE_LENGTH = 100
DATE_FORMAT = "%Y-%m-%d"


def _validate_title(title: str) -> str:
    """Return ``title`` stripped, or raise if it is empty or too long."""
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("Title must be a non-empty string.")
    title = title.strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(
            f"Title must be at most {MAX_TITLE_LENGTH} characters."
        )
    return title


def _validate_description(description: Optional[str]) -> str:
    """Return the description stripped (``None`` becomes an empty string)."""
    if description is None:
        return ""
    if not isinstance(description, str):
        raise ValidationError("Description must be a string.")
    return description.strip()


def _parse_due_date(value: Union[date, str, None]) -> Optional[date]:
    """Accept a ``date``, an ISO string ``YYYY-MM-DD`` or ``None``."""
    if value is None:
        return None
    # datetime is a subclass of date; keep only the calendar day.
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), DATE_FORMAT).date()
        except ValueError:
            pass
    raise ValidationError(
        f"Due date must be a date or a string formatted as YYYY-MM-DD, "
        f"got {value!r}."
    )


# --------------------------------------------------------------------------
# Task entity
# --------------------------------------------------------------------------

class Task:
    """A single to-do item.

    The task owns its own validation and state transitions, so it can never
    be put into an invalid state from the outside (encapsulation).
    """

    def __init__(
        self,
        task_id: int,
        title: str,
        description: Optional[str] = None,
        priority: Union[Priority, str] = Priority.MEDIUM,
        due_date: Union[date, str, None] = None,
    ) -> None:
        if isinstance(task_id, bool) or not isinstance(task_id, int) \
                or task_id < 1:
            raise ValidationError("Task ID must be a positive integer.")
        self._task_id = task_id
        self._title = _validate_title(title)
        self._description = _validate_description(description)
        self._priority = Priority.parse(priority)
        self._due_date = _parse_due_date(due_date)
        self._status = Status.PENDING
        self._created_at = datetime.now()
        self._completed_at: Optional[datetime] = None

    # ----- read-only properties -------------------------------------------

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def due_date(self) -> Optional[date]:
        return self._due_date

    @property
    def status(self) -> Status:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def is_completed(self) -> bool:
        return self._status is Status.COMPLETED

    # ----- behaviour ------------------------------------------------------

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Union[Priority, str, None] = None,
        due_date: Union[date, str, None] = None,
        clear_due_date: bool = False,
    ) -> None:
        """Edit one or more fields. Only the given fields change.

        All values are validated before anything is written, so a failed
        update leaves the task untouched.
        """
        if self.is_completed:
            raise InvalidStateError(
                f"Task #{self._task_id} is completed and cannot be edited."
            )
        new_title = self._title if title is None else _validate_title(title)
        new_description = (self._description if description is None
                           else _validate_description(description))
        new_priority = (self._priority if priority is None
                        else Priority.parse(priority))
        if clear_due_date:
            new_due_date = None
        elif due_date is None:
            new_due_date = self._due_date
        else:
            new_due_date = _parse_due_date(due_date)

        self._title = new_title
        self._description = new_description
        self._priority = new_priority
        self._due_date = new_due_date

    def start(self) -> None:
        """Move a pending task to *in progress*."""
        if self._status is not Status.PENDING:
            raise InvalidStateError(
                f"Only pending tasks can be started; task #{self._task_id} "
                f"is {self._status.value}."
            )
        self._status = Status.IN_PROGRESS

    def complete(self) -> None:
        """Mark the task as completed and record when."""
        if self.is_completed:
            raise InvalidStateError(
                f"Task #{self._task_id} is already completed."
            )
        self._status = Status.COMPLETED
        self._completed_at = datetime.now()

    def is_overdue(self, today: Optional[date] = None) -> bool:
        """True if the task is not completed and its due date has passed."""
        if self.is_completed or self._due_date is None:
            return False
        return self._due_date < (today or date.today())

    def days_until_due(self, today: Optional[date] = None) -> Optional[int]:
        """Days left until the due date (negative if overdue)."""
        if self._due_date is None:
            return None
        return (self._due_date - (today or date.today())).days

    def to_dict(self) -> Dict[str, object]:
        """Return a plain, JSON-friendly representation of the task."""
        return {
            "id": self._task_id,
            "title": self._title,
            "description": self._description,
            "priority": self._priority.name.lower(),
            "status": self._status.value,
            "due_date": (self._due_date.isoformat()
                         if self._due_date else None),
            "created_at": self._created_at.isoformat(timespec="seconds"),
            "completed_at": (
                self._completed_at.isoformat(timespec="seconds")
                if self._completed_at else None
            ),
        }

    def __str__(self) -> str:
        mark = "x" if self.is_completed else " "
        due = self._due_date.isoformat() if self._due_date else "no due date"
        return (f"[{mark}] #{self._task_id:<3} {self._title:<31} "
                f"{self._priority.name:<6} {self._status.value:<11} {due}")

    def __repr__(self) -> str:
        return (f"Task(task_id={self._task_id}, title={self._title!r}, "
                f"priority={self._priority.name}, "
                f"status={self._status.name})")


# --------------------------------------------------------------------------
# Storage (Dependency Inversion: TaskManager depends on this abstraction)
# --------------------------------------------------------------------------

class TaskRepository(ABC):
    """Abstract storage for tasks. Swap in a file or database backend
    without touching ``TaskManager``."""

    @abstractmethod
    def add(self, task: Task) -> None:
        """Store a new task."""

    @abstractmethod
    def get(self, task_id: int) -> Task:
        """Return a task or raise ``TaskNotFoundError``."""

    @abstractmethod
    def remove(self, task_id: int) -> Task:
        """Delete a task and return it, or raise ``TaskNotFoundError``."""

    @abstractmethod
    def all(self) -> List[Task]:
        """Return every stored task."""

    @abstractmethod
    def next_id(self) -> int:
        """Return a fresh, unused task ID."""


class InMemoryTaskRepository(TaskRepository):
    """Dictionary-backed repository; IDs are never reused."""

    def __init__(self) -> None:
        self._tasks: Dict[int, Task] = {}
        self._last_id = 0

    def add(self, task: Task) -> None:
        if task.task_id in self._tasks:
            raise ValidationError(f"Task #{task.task_id} already exists.")
        self._tasks[task.task_id] = task
        self._last_id = max(self._last_id, task.task_id)

    def get(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(f"Task #{task_id} not found.") from None

    def remove(self, task_id: int) -> Task:
        task = self.get(task_id)
        del self._tasks[task_id]
        return task

    def all(self) -> List[Task]:
        return list(self._tasks.values())

    def next_id(self) -> int:
        return self._last_id + 1


# --------------------------------------------------------------------------
# Filtering and sorting (Open/Closed: add new ones without editing the
# manager)
# --------------------------------------------------------------------------

TaskFilter = Callable[[Task], bool]


def by_status(status: Status) -> TaskFilter:
    """Keep tasks with the given status."""
    return lambda task: task.status is status


def by_priority(priority: Union[Priority, str]) -> TaskFilter:
    """Keep tasks with the given priority."""
    wanted = Priority.parse(priority)
    return lambda task: task.priority is wanted


def overdue(today: Optional[date] = None) -> TaskFilter:
    """Keep tasks that are past their due date and not completed."""
    return lambda task: task.is_overdue(today)


def due_within(days: int, today: Optional[date] = None) -> TaskFilter:
    """Keep open tasks due between today and ``days`` days from today."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ValidationError("Days must be a non-negative integer.")

    def _filter(task: Task) -> bool:
        remaining = task.days_until_due(today)
        return (not task.is_completed and remaining is not None
                and 0 <= remaining <= days)
    return _filter


def search(keyword: str) -> TaskFilter:
    """Keep tasks whose title or description contains ``keyword``."""
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValidationError("Search keyword must be a non-empty string.")
    needle = keyword.strip().lower()
    return lambda task: (needle in task.title.lower()
                         or needle in task.description.lower())


# Each key returns a sortable value. Tasks without a due date sort last.
SORT_KEYS: Dict[str, Callable[[Task], object]] = {
    "id": lambda task: task.task_id,
    "title": lambda task: task.title.lower(),
    "priority": lambda task: (-task.priority.value, task.task_id),
    "due_date": lambda task: (task.due_date is None,
                              task.due_date or date.max, task.task_id),
    "status": lambda task: (list(Status).index(task.status), task.task_id),
    "created": lambda task: (task.created_at, task.task_id),
}


# --------------------------------------------------------------------------
# Service layer
# --------------------------------------------------------------------------

class TaskManager:
    """High-level API for managing tasks.

    The repository and the clock are injected, which keeps the class easy
    to test and independent of any storage technology.
    """

    def __init__(
        self,
        repository: Optional[TaskRepository] = None,
        clock: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository or InMemoryTaskRepository()
        self._clock = clock

    # ----- CRUD -----------------------------------------------------------

    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: Union[Priority, str] = Priority.MEDIUM,
        due_date: Union[date, str, None] = None,
    ) -> Task:
        """Create, store and return a new task."""
        task = Task(self._repository.next_id(), title, description,
                    priority, due_date)
        self._repository.add(task)
        return task

    def get_task(self, task_id: int) -> Task:
        """Return the task with ``task_id``."""
        return self._repository.get(task_id)

    def edit_task(self, task_id: int, **changes: object) -> Task:
        """Edit a task's title, description, priority or due date."""
        task = self.get_task(task_id)
        task.update(**changes)  # type: ignore[arg-type]
        return task

    def start_task(self, task_id: int) -> Task:
        """Move a task to *in progress*."""
        task = self.get_task(task_id)
        task.start()
        return task

    def complete_task(self, task_id: int) -> Task:
        """Mark a task as completed."""
        task = self.get_task(task_id)
        task.complete()
        return task

    def delete_task(self, task_id: int) -> Task:
        """Delete a task and return it."""
        return self._repository.remove(task_id)

    def clear_completed(self) -> int:
        """Delete every completed task and return how many were removed."""
        done = [t.task_id for t in self._repository.all() if t.is_completed]
        for task_id in done:
            self._repository.remove(task_id)
        return len(done)

    # ----- querying -------------------------------------------------------

    def list_tasks(
        self,
        filters: Iterable[TaskFilter] = (),
        sort_by: str = "id",
        reverse: bool = False,
    ) -> List[Task]:
        """Return tasks matching *all* filters, sorted by ``sort_by``.

        ``sort_by`` is one of: id, title, priority, due_date, status,
        created.
        """
        if sort_by not in SORT_KEYS:
            options = ", ".join(SORT_KEYS)
            raise ValidationError(f"sort_by must be one of: {options}.")
        filters = list(filters)
        tasks = [task for task in self._repository.all()
                 if all(check(task) for check in filters)]
        return sorted(tasks, key=SORT_KEYS[sort_by], reverse=reverse)

    def overdue_tasks(self) -> List[Task]:
        """Open tasks past their due date, most urgent first."""
        return self.list_tasks([overdue(self._clock())], sort_by="due_date")

    def upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Open tasks due within the next ``days`` days."""
        return self.list_tasks([due_within(days, self._clock())],
                               sort_by="due_date")

    def search_tasks(self, keyword: str) -> List[Task]:
        """Tasks whose title or description contains ``keyword``."""
        return self.list_tasks([search(keyword)])

    # ----- statistics -----------------------------------------------------

    def statistics(self) -> Dict[str, object]:
        """Return a summary of all tasks."""
        tasks = self._repository.all()
        today = self._clock()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        return {
            "total": total,
            "by_status": {s.value: sum(1 for t in tasks if t.status is s)
                          for s in Status},
            "by_priority": {p.name.lower():
                            sum(1 for t in tasks if t.priority is p)
                            for p in Priority},
            "overdue": sum(1 for t in tasks if t.is_overdue(today)),
            "completion_rate": (round(completed / total * 100, 1)
                                if total else 0.0),
        }

    # ----- display --------------------------------------------------------

    def display_tasks(self, tasks: Optional[List[Task]] = None,
                      heading: str = "All tasks") -> None:
        """Print a formatted table of tasks (all tasks by default)."""
        tasks = self.list_tasks() if tasks is None else tasks
        print(f"\n{heading} ({len(tasks)})")
        print("-" * 72)
        if not tasks:
            print("  (no tasks)")
        for task in tasks:
            flag = "  ! OVERDUE" if task.is_overdue(self._clock()) else ""
            print(f"  {task}{flag}")

    def __len__(self) -> int:
        return len(self._repository.all())


# --------------------------------------------------------------------------
# Demonstration
# --------------------------------------------------------------------------

def main() -> None:
    """Walk through every feature of the to-do app."""
    # A fixed "today" keeps the demo output identical on every run.
    today = date(2024, 6, 10)
    manager = TaskManager(clock=lambda: today)

    print("=" * 72)
    print(" TO-DO LIST APP - DEMO")
    print("=" * 72)

    # 1. Adding tasks
    manager.add_task("Write project README", "Usage, examples, OOP notes",
                     priority="high", due_date=today + timedelta(days=1))
    manager.add_task("Fix login bug", "Users logged out after refresh",
                     priority=Priority.HIGH, due_date="2024-06-08")
    manager.add_task("Buy groceries", "Milk, eggs, bread", priority="low",
                     due_date=today + timedelta(days=3))
    manager.add_task("Prepare interview notes", priority="medium",
                     due_date=today + timedelta(days=5))
    manager.add_task("Read Clean Code chapter 3", priority="low")
    manager.add_task("Refactor task module", "Apply SOLID principles",
                     priority="medium", due_date="2024-06-09")
    manager.display_tasks()

    # 2. Editing and changing status
    manager.edit_task(4, title="Prepare Python interview notes",
                      priority="high")
    manager.start_task(1)
    manager.start_task(6)
    manager.complete_task(3)
    manager.complete_task(6)
    manager.display_tasks(heading="After editing, starting and completing")

    # 3. Filtering
    manager.display_tasks(manager.list_tasks([by_priority("high")]),
                          heading="High-priority tasks")
    manager.display_tasks(manager.list_tasks([by_status(Status.PENDING)]),
                          heading="Pending tasks")
    manager.display_tasks(manager.overdue_tasks(), heading="Overdue tasks")
    manager.display_tasks(manager.upcoming_tasks(days=3),
                          heading="Due in the next 3 days")
    manager.display_tasks(manager.search_tasks("interview"),
                          heading="Search: 'interview'")

    # 4. Sorting
    manager.display_tasks(manager.list_tasks(sort_by="priority"),
                          heading="Sorted by priority")
    manager.display_tasks(manager.list_tasks(sort_by="due_date"),
                          heading="Sorted by due date")

    # 5. Statistics
    stats = manager.statistics()
    print("\nStatistics")
    print("-" * 72)
    print(f"  Total tasks      : {stats['total']}")
    print(f"  By status        : {stats['by_status']}")
    print(f"  By priority      : {stats['by_priority']}")
    print(f"  Overdue          : {stats['overdue']}")
    print(f"  Completion rate  : {stats['completion_rate']}%")

    # 6. Deleting
    removed = manager.delete_task(5)
    print(f"\nDeleted: {removed.title!r}")
    print(f"Cleared {manager.clear_completed()} completed task(s); "
          f"{len(manager)} task(s) left.")

    # 7. Error handling
    print("\nError handling")
    print("-" * 72)
    attempts = [
        ("Empty title", lambda: manager.add_task("   ")),
        ("Unknown priority", lambda: manager.add_task("X", priority="urgent")),
        ("Bad due date", lambda: manager.add_task("X", due_date="10/06/2024")),
        ("Missing task", lambda: manager.get_task(99)),
        ("Start a started task", lambda: manager.start_task(1)),
        ("Unknown sort key", lambda: manager.list_tasks(sort_by="colour")),
    ]
    for label, action in attempts:
        try:
            action()
        except TodoError as error:
            print(f"  {label:<22} -> {type(error).__name__}: {error}")

    print("\nDone.")


if __name__ == "__main__":
    main()
