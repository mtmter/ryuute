import {
  WEEKDAY_NAMES,
  eventOccursOnDate,
  formatTime,
  getDateKey,
  getEventPositionForDay,
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

function DayCalendar({
  events,
  tasks,
  selectedDate,
  onEventClick,
  onTaskClick,
  onTimeClick,
}) {
  const today = new Date();
  const weekdayIndex = selectedDate.getDay();
  const dateEvents = events
    .filter((event) => eventOccursOnDate(event, selectedDate))
    .sort((firstEvent, secondEvent) =>
      (firstEvent.start_at ?? "").localeCompare(secondEvent.start_at ?? ""),
    );
  const dateTasks = tasks
    .filter(
      (task) =>
        !task.completed &&
        task.due_at?.slice(0, 10) === getDateKey(selectedDate),
    )
    .sort((firstTask, secondTask) =>
      firstTask.due_at.localeCompare(secondTask.due_at),
    );

  return (
    <section aria-label="日間カレンダー">
      <div className="calendar-horizontal-scroll">
        <div className="day-calendar">
          <div className="week-header-row day-header-row">
            <div className="week-corner" />
            <div className="week-date-heading">
              <span
                className={
                  weekdayIndex === 0
                    ? "is-sunday"
                    : weekdayIndex === 6
                      ? "is-saturday"
                      : ""
                }
              >
                {WEEKDAY_NAMES[weekdayIndex]}
              </span>
              <time
                className={isSameDay(selectedDate, today) ? "is-today" : ""}
                dateTime={getDateKey(selectedDate)}
              >
                {selectedDate.getDate()}
              </time>
            </div>
          </div>

          <div className="week-due-row day-due-row">
            <div className="week-due-label">期限</div>
            <div className="week-due-cell">
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
          </div>

          <div className="week-time-scroll">
            <div
              className="week-time-grid day-time-grid"
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

              <div
                className="week-day-column"
                style={{ "--hour-height": `${HOUR_HEIGHT}px` }}
                onClick={(event) => {
                  const columnRectangle =
                    event.currentTarget.getBoundingClientRect();
                  const clickedMinutes =
                    ((event.clientY - columnRectangle.top) / HOUR_HEIGHT) * 60;
                  const roundedMinutes = Math.min(
                    Math.max(Math.floor(clickedMinutes / 30) * 30, 0),
                    23 * 60 + 30,
                  );
                  onTimeClick(selectedDate, roundedMinutes);
                }}
              >
                {dateEvents.map((event) => {
                  const position = getEventPositionForDay(event, selectedDate);

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
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default DayCalendar;
