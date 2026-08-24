import {
  WEEKDAY_NAMES,
  addMonths,
  formatMonthTitle,
  getDateKey,
  getMonthDates,
  getWeekDates,
  isSameDay,
} from "../dateUtils";

function MiniCalendar({
  activeView,
  displayedMonth,
  selectedDate,
  onDateSelect,
  onDisplayedMonthChange,
}) {
  const calendarDates = getMonthDates(displayedMonth);
  const visibleWeekDateKeys = new Set(
    activeView === "week"
      ? getWeekDates(selectedDate).map((date) => getDateKey(date))
      : [],
  );
  const today = new Date();

  return (
    <section className="mini-calendar" aria-label="ミニカレンダー">
      <div className="mini-calendar-header">
        <h2>{formatMonthTitle(displayedMonth)}</h2>
        <div>
          <button
            type="button"
            aria-label="ミニカレンダーを前の月へ移動"
            onClick={() =>
              onDisplayedMonthChange(addMonths(displayedMonth, -1))
            }
          >
            ‹
          </button>
          <button
            type="button"
            aria-label="ミニカレンダーを次の月へ移動"
            onClick={() => onDisplayedMonthChange(addMonths(displayedMonth, 1))}
          >
            ›
          </button>
        </div>
      </div>

      <div className="mini-calendar-weekdays" aria-hidden="true">
        {WEEKDAY_NAMES.map((weekday, index) => (
          <span
            className={
              index === 0 ? "is-sunday" : index === 6 ? "is-saturday" : ""
            }
            key={weekday}
          >
            {weekday}
          </span>
        ))}
      </div>

      <div className="mini-calendar-days">
        {calendarDates.map((date) => {
          const dateKey = getDateKey(date);
          const isOutsideMonth = date.getMonth() !== displayedMonth.getMonth();
          const isSelected = isSameDay(date, selectedDate);
          const isVisibleWeek = visibleWeekDateKeys.has(dateKey);

          return (
            <button
              className={`${isOutsideMonth ? "is-outside-month " : ""}${isVisibleWeek ? "is-visible-week " : ""}${isSelected ? "is-selected " : ""}${isSameDay(date, today) ? "is-today" : ""}`.trim()}
              type="button"
              aria-label={`${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日を表示`}
              aria-pressed={isSelected}
              key={dateKey}
              onClick={() => onDateSelect(date)}
            >
              {date.getDate()}
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default MiniCalendar;
