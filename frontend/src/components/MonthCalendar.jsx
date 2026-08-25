import { useEffect, useState } from "react";
import {
  WEEKDAY_NAMES,
  eventOccursOnDate,
  formatTime,
  getDateKey,
  getEventDaySegment,
  getMonthDates,
  isSameDay,
  parseDateTime,
} from "../dateUtils";

const MAX_ITEMS_WITHOUT_SUMMARY_IN_FIVE_WEEK_MONTH = 4;
const VISIBLE_ITEMS_WITH_SUMMARY_IN_FIVE_WEEK_MONTH = 3;
const MAX_ITEMS_WITHOUT_SUMMARY_IN_SIX_WEEK_MONTH = 3;
const VISIBLE_ITEMS_WITH_SUMMARY_IN_SIX_WEEK_MONTH = 2;

function MonthCalendar({
  events,
  tasks,
  selectedDate,
  onDateClick,
  onEventClick,
  onTaskClick,
}) {
  const calendarDates = getMonthDates(selectedDate);
  const hasSixWeeks = calendarDates.length === 42;
  const [dayItemsPopup, setDayItemsPopup] = useState(null);
  const today = new Date();

  useEffect(() => {
    if (!dayItemsPopup) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setDayItemsPopup(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [dayItemsPopup]);

  return (
    <section aria-label="月間カレンダー">
      <div className="calendar-horizontal-scroll">
        <div
          className={`month-calendar${hasSixWeeks ? " has-six-weeks" : ""}`}
        >
          <div className="month-weekdays" aria-hidden="true">
            {WEEKDAY_NAMES.map((weekday, index) => (
              <div
                className={
                  index === 0
                    ? "is-sunday"
                    : index === 6
                      ? "is-saturday"
                      : ""
                }
                key={weekday}
              >
                {weekday}
              </div>
            ))}
          </div>

          <div className="month-grid">
            {calendarDates.map((date) => {
              const dateEvents = events
                .filter((event) => eventOccursOnDate(event, date))
                .sort((firstEvent, secondEvent) =>
                  (firstEvent.start_at ?? "").localeCompare(
                    secondEvent.start_at ?? "",
                  ),
                );
              const dateTasks = tasks
                .filter(
                  (task) =>
                    !task.completed &&
                    task.due_at?.slice(0, 10) === getDateKey(date),
                )
                .sort((firstTask, secondTask) =>
                  firstTask.due_at.localeCompare(secondTask.due_at),
                );
              const maxItemsWithoutSummary = hasSixWeeks
                ? MAX_ITEMS_WITHOUT_SUMMARY_IN_SIX_WEEK_MONTH
                : MAX_ITEMS_WITHOUT_SUMMARY_IN_FIVE_WEEK_MONTH;
              const visibleItemsWithSummary = hasSixWeeks
                ? VISIBLE_ITEMS_WITH_SUMMARY_IN_SIX_WEEK_MONTH
                : VISIBLE_ITEMS_WITH_SUMMARY_IN_FIVE_WEEK_MONTH;
              const totalItemCount = dateEvents.length + dateTasks.length;
              const visibleItemCount =
                totalItemCount > maxItemsWithoutSummary
                  ? visibleItemsWithSummary
                  : totalItemCount;
              const visibleEvents = dateEvents.slice(0, visibleItemCount);
              const visibleTaskCount = Math.max(
                visibleItemCount - visibleEvents.length,
                0,
              );
              const visibleTasks = dateTasks.slice(0, visibleTaskCount);
              const hiddenItemCount =
                totalItemCount - visibleEvents.length - visibleTasks.length;
              const isOutsideMonth =
                date.getMonth() !== selectedDate.getMonth();

              return (
                <div
                  className={`month-day${isOutsideMonth ? " is-outside-month" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日に追加`}
                  key={getDateKey(date)}
                  onClick={() => onDateClick(date)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onDateClick(date);
                    }
                  }}
                >
                  <time
                    className={`month-date${isSameDay(date, today) ? " is-today" : ""}`}
                    dateTime={getDateKey(date)}
                  >
                    {date.getDate()}
                  </time>

                  <div className="month-day-items">
                    {visibleEvents.map((event) => {
                      const segment = getEventDaySegment(event, date);
                      const eventStart = parseDateTime(event.start_at);
                      const showStartTime =
                        eventStart && isSameDay(eventStart, date);
                      const connectsFromPreviousDay =
                        segment.continuesBefore && date.getDay() !== 0;
                      const connectsToNextDay =
                        segment.continuesAfter && date.getDay() !== 6;

                      return (
                        <div
                          className={`month-event${connectsFromPreviousDay ? " continues-before" : ""}${connectsToNextDay ? " continues-after" : ""}`}
                          title={event.title}
                          key={`event-${event.id}`}
                          role="button"
                          tabIndex={0}
                          onClick={(clickEvent) => {
                            clickEvent.stopPropagation();
                            onEventClick(event);
                          }}
                          onKeyDown={(keyEvent) => {
                            if (
                              keyEvent.key === "Enter" ||
                              keyEvent.key === " "
                            ) {
                              keyEvent.preventDefault();
                              keyEvent.stopPropagation();
                              onEventClick(event);
                            }
                          }}
                        >
                          {showStartTime && (
                            <span className="month-item-time">
                              {formatTime(event.start_at)}
                            </span>
                          )}
                          <span>{event.title}</span>
                        </div>
                      );
                    })}

                    {visibleTasks.map((task) => (
                      <div
                        className="month-task"
                        title={`タスク: ${task.title}`}
                        key={`task-${task.id}`}
                        role="button"
                        tabIndex={0}
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          onTaskClick(task);
                        }}
                        onKeyDown={(keyEvent) => {
                          if (
                            keyEvent.key === "Enter" ||
                            keyEvent.key === " "
                          ) {
                            keyEvent.preventDefault();
                            keyEvent.stopPropagation();
                            onTaskClick(task);
                          }
                        }}
                      >
                        <span className="task-dot" aria-hidden="true" />
                        <span className="month-item-time">
                          {formatTime(task.due_at)}
                        </span>
                        <span>{task.title}</span>
                      </div>
                    ))}

                    {hiddenItemCount > 0 && (
                      <button
                        type="button"
                        className="month-more-events"
                        title={`他${hiddenItemCount}件の予定とタスクを表示`}
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          setDayItemsPopup({
                            date,
                            events: dateEvents,
                            tasks: dateTasks,
                          });
                        }}
                        onKeyDown={(keyEvent) => keyEvent.stopPropagation()}
                      >
                        他{hiddenItemCount}件
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {dayItemsPopup && (
        <div
          className="month-events-popover-backdrop"
          onClick={() => setDayItemsPopup(null)}
        >
          <section
            aria-labelledby={`month-events-title-${getDateKey(dayItemsPopup.date)}`}
            aria-modal="true"
            className="month-events-popover"
            role="dialog"
            onClick={(clickEvent) => clickEvent.stopPropagation()}
          >
            <header className="month-events-popover-header">
              <span aria-hidden="true" />
              <div>
                <span>{WEEKDAY_NAMES[dayItemsPopup.date.getDay()]}</span>
                <time
                  dateTime={getDateKey(dayItemsPopup.date)}
                  id={`month-events-title-${getDateKey(dayItemsPopup.date)}`}
                >
                  {dayItemsPopup.date.getDate()}
                </time>
              </div>
              <button
                autoFocus
                aria-label="予定とタスクの一覧を閉じる"
                className="modal-close-button"
                type="button"
                onClick={() => setDayItemsPopup(null)}
              >
                ×
              </button>
            </header>

            <div className="month-events-popover-list">
              {dayItemsPopup.events.map((event) => {
                const eventStart = parseDateTime(event.start_at);
                const showStartTime =
                  eventStart && isSameDay(eventStart, dayItemsPopup.date);

                return (
                  <button
                    type="button"
                    className="month-events-popover-event"
                    key={`popup-event-${event.id}`}
                    title={event.title}
                    onClick={() => {
                      setDayItemsPopup(null);
                      onEventClick(event);
                    }}
                  >
                    {showStartTime && (
                      <span className="month-item-time">
                        {formatTime(event.start_at)}
                      </span>
                    )}
                    <span>{event.title}</span>
                  </button>
                );
              })}

              {dayItemsPopup.tasks.map((task) => (
                <button
                  type="button"
                  className="month-events-popover-task"
                  key={`popup-task-${task.id}`}
                  title={`タスク: ${task.title}`}
                  onClick={() => {
                    setDayItemsPopup(null);
                    onTaskClick(task);
                  }}
                >
                  <span className="task-dot" aria-hidden="true" />
                  <span className="month-item-time">
                    {formatTime(task.due_at)}
                  </span>
                  <span>{task.title}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

export default MonthCalendar;
