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

function MonthCalendar({
  events,
  tasks,
  selectedDate,
  onDateClick,
  onEventClick,
  onTaskClick,
}) {
  const calendarDates = getMonthDates(selectedDate);
  const today = new Date();

  return (
    <section aria-label="月間カレンダー">
      <div className="calendar-horizontal-scroll">
        <div className="month-calendar">
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
                    {dateEvents.map((event) => {
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

                    {dateTasks.map((task) => (
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
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

export default MonthCalendar;
