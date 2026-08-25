function CalendarToolbar({ title, onPrevious, onToday, onNext }) {
  return (
    <div className="calendar-toolbar">
      <div className="calendar-actions">
        <button type="button" onClick={onToday}>
          今日
        </button>
        <button
          className="icon-button"
          type="button"
          aria-label="前の期間"
          onClick={onPrevious}
        >
          ‹
        </button>
        <button
          className="icon-button"
          type="button"
          aria-label="次の期間"
          onClick={onNext}
        >
          ›
        </button>
      </div>
      <h2>{title}</h2>
    </div>
  );
}

export default CalendarToolbar;
