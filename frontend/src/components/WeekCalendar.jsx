import {
  WEEKDAY_NAMES,
  eventOccursOnDate,
  formatTime,
  getDateKey,
  getEventPositionForDay,
  getWeekDates,
  isSameDay,
} from "../dateUtils";

const HOUR_HEIGHT = 56;

function formatMinutes(minutes) {
  if (minutes === 24 * 60) {
    return "24:00";
  }

  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
}

function WeekCalendar({
  events,
  tasks,
  selectedDate,
  onEventClick,
  onTaskClick,
  onTimeClick,
}) {
  const weekDates = getWeekDates(selectedDate);
  const today = new Date();

  return (
    <section aria-label="週間カレンダー">
      <div className="calendar-horizontal-scroll">
        <div className="week-calendar">
          <div className="week-header-row">
            <div className="week-corner" />
            {weekDates.map((date, index) => (
              <div className="week-date-heading" key={getDateKey(date)}>
                <span
                  className={
                    index === 0
                      ? "is-sunday"
                      : index === 6
                        ? "is-saturday"
                        : ""
                  }
                >
                  {WEEKDAY_NAMES[index]}
                </span>
                <time
                  className={isSameDay(date, today) ? "is-today" : ""}
                  dateTime={getDateKey(date)}
                >
                  {date.getDate()}
                </time>
              </div>
            ))}
          </div>

          <div className="week-due-row">
            <div aria-hidden="true" />
            {weekDates.map((date) => {
              const dateTasks = tasks
                .filter(
                  (task) =>
                    !task.completed &&
                    task.due_at?.slice(0, 10) === getDateKey(date),
                )
                .sort((firstTask, secondTask) =>
                  firstTask.due_at.localeCompare(secondTask.due_at),
                );

              return (
                <div className="week-due-cell" key={getDateKey(date)}>
                  {dateTasks.map((task) => (
                    <div
                      className="week-task"
                      title={task.title}
                      key={task.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => onTaskClick(task)}
                      onKeyDown={(keyEvent) => {
                        if (
                          keyEvent.key === "Enter" ||
                          keyEvent.key === " "
                        ) {
                          keyEvent.preventDefault();
                          onTaskClick(task);
                        }
                      }}
                    >
                      {formatTime(task.due_at)} {task.title}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>

          <div className="week-time-scroll">
            <div
              className="week-time-grid"
              style={{ height: `${24 * HOUR_HEIGHT}px` }}
            >
              <div className="week-hours" aria-hidden="true">
                {Array.from({ length: 24 }, (_, hour) => (
                  <span
                    style={{ top: `${hour * HOUR_HEIGHT}px` }}
                    key={hour}
                  >
                    {String(hour).padStart(2, "0")}:00
                  </span>
                ))}
              </div>

              {weekDates.map((date) => {
                const dateEvents = events
                  .filter((event) => eventOccursOnDate(event, date))
                  .sort((firstEvent, secondEvent) =>
                    (firstEvent.start_at ?? "").localeCompare(
                      secondEvent.start_at ?? "",
                    ),
                  );

                return (
                  <div
                    className="week-day-column"
                    style={{ "--hour-height": `${HOUR_HEIGHT}px` }}
                    key={getDateKey(date)}
                    onClick={(event) => {
                      const columnRectangle =
                        event.currentTarget.getBoundingClientRect();
                      const clickedMinutes =
                        ((event.clientY - columnRectangle.top) / HOUR_HEIGHT) *
                        60;
                      const roundedMinutes = Math.min(
                        Math.max(Math.floor(clickedMinutes / 30) * 30, 0),
                        23 * 60 + 30,
                      );
                      onTimeClick(date, roundedMinutes);
                    }}
                  >
                    {dateEvents.map((event) => {
                      const position = getEventPositionForDay(event, date);

                      return (
                        <div
                          className="week-event"
                          style={{
                            top: `${(position.startMinutes / 60) * HOUR_HEIGHT}px`,
                            height: `${Math.max(
                              (position.durationMinutes / 60) * HOUR_HEIGHT,
                              28,
                            )}px`,
                          }}
                          title={event.title}
                          key={event.id}
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
                          <strong>{event.title}</strong>
                          <span>
                            {formatMinutes(position.startMinutes)}–
                            {formatMinutes(
                              position.startMinutes + position.durationMinutes,
                            )}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default WeekCalendar;
