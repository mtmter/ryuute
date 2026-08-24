export const WEEKDAY_NAMES = ["日", "月", "火", "水", "木", "金", "土"];

export function parseDateTime(value) {
  if (!value) {
    return null;
  }

  const [datePart, timePart = "00:00"] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);

  return new Date(year, month - 1, day, hour, minute);
}

export function getDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function toDateTimeInputValue(date) {
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${getDateKey(date)}T${hour}:${minute}`;
}

export function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function addDays(date, numberOfDays) {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + numberOfDays);
  return nextDate;
}

export function addMonths(date, numberOfMonths) {
  return new Date(date.getFullYear(), date.getMonth() + numberOfMonths, 1);
}

export function getMonthDates(selectedDate) {
  const firstDay = new Date(
    selectedDate.getFullYear(),
    selectedDate.getMonth(),
    1,
  );
  const lastDay = new Date(
    selectedDate.getFullYear(),
    selectedDate.getMonth() + 1,
    0,
  );
  const gridStart = addDays(firstDay, -firstDay.getDay());
  const daysNeeded = firstDay.getDay() + lastDay.getDate();
  const cellCount = daysNeeded <= 35 ? 35 : 42;

  return Array.from({ length: cellCount }, (_, index) =>
    addDays(gridStart, index),
  );
}

export function getWeekDates(selectedDate) {
  const weekStart = addDays(selectedDate, -selectedDate.getDay());
  return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
}

export function isSameDay(firstDate, secondDate) {
  return getDateKey(firstDate) === getDateKey(secondDate);
}

export function eventOccursOnDate(event, date) {
  const eventStart = parseDateTime(event.start_at);
  const eventEnd = parseDateTime(event.end_at) ?? eventStart;

  if (!eventStart) {
    return false;
  }

  const dayStart = startOfDay(date);
  const nextDayStart = addDays(dayStart, 1);
  const safeEventEnd =
    eventEnd <= eventStart
      ? new Date(eventStart.getTime() + 30 * 60 * 1000)
      : eventEnd;

  return eventStart < nextDayStart && safeEventEnd > dayStart;
}

export function getEventDaySegment(event, date) {
  const eventStart = parseDateTime(event.start_at);
  const eventEnd = parseDateTime(event.end_at) ?? eventStart;
  const dayStart = startOfDay(date);
  const nextDayStart = addDays(dayStart, 1);
  const safeEventEnd =
    eventEnd <= eventStart
      ? new Date(eventStart.getTime() + 30 * 60 * 1000)
      : eventEnd;

  return {
    continuesBefore: eventStart < dayStart,
    continuesAfter: safeEventEnd > nextDayStart,
  };
}

export function getEventPositionForDay(event, date) {
  const eventStart = parseDateTime(event.start_at);
  const eventEnd = parseDateTime(event.end_at) ?? eventStart;
  const dayStart = startOfDay(date);
  const nextDayStart = addDays(dayStart, 1);
  const visibleStart = eventStart < dayStart ? dayStart : eventStart;
  const safeEventEnd =
    eventEnd <= eventStart
      ? new Date(eventStart.getTime() + 30 * 60 * 1000)
      : eventEnd;
  const visibleEnd = safeEventEnd > nextDayStart ? nextDayStart : safeEventEnd;
  const startMinutes =
    visibleStart.getHours() * 60 + visibleStart.getMinutes();
  const endMinutes =
    visibleEnd >= nextDayStart
      ? 24 * 60
      : visibleEnd.getHours() * 60 + visibleEnd.getMinutes();

  return {
    startMinutes,
    durationMinutes: Math.max(endMinutes - startMinutes, 30),
  };
}

export function formatTime(value) {
  if (!value || !value.includes("T")) {
    return "";
  }

  return value.slice(11, 16);
}

export function formatMonthTitle(date) {
  return `${date.getFullYear()}年${date.getMonth() + 1}月`;
}

export function formatWeekTitle(weekDates) {
  const firstDate = weekDates[0];
  const lastDate = weekDates[6];

  if (firstDate.getFullYear() !== lastDate.getFullYear()) {
    return `${firstDate.getFullYear()}年${firstDate.getMonth() + 1}月${firstDate.getDate()}日 – ${lastDate.getFullYear()}年${lastDate.getMonth() + 1}月${lastDate.getDate()}日`;
  }

  if (firstDate.getMonth() !== lastDate.getMonth()) {
    return `${firstDate.getFullYear()}年${firstDate.getMonth() + 1}月${firstDate.getDate()}日 – ${lastDate.getMonth() + 1}月${lastDate.getDate()}日`;
  }

  return `${firstDate.getFullYear()}年${firstDate.getMonth() + 1}月${firstDate.getDate()}日 – ${lastDate.getDate()}日`;
}

export function formatDayTitle(date) {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日（${WEEKDAY_NAMES[date.getDay()]}）`;
}

export function formatTaskDue(value) {
  const date = parseDateTime(value);

  if (!date) {
    return "期限なし";
  }

  return `${date.getMonth() + 1}月${date.getDate()}日（${WEEKDAY_NAMES[date.getDay()]}） ${formatTime(value)}`;
}

export function sortTasksByDueDate(tasks) {
  return [...tasks].sort((firstTask, secondTask) => {
    if (!firstTask.due_at && !secondTask.due_at) {
      return firstTask.id - secondTask.id;
    }
    if (!firstTask.due_at) {
      return 1;
    }
    if (!secondTask.due_at) {
      return -1;
    }

    return firstTask.due_at.localeCompare(secondTask.due_at);
  });
}
