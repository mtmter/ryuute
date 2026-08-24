function PreparationReminderList({ reminders, onEventClick }) {
  if (reminders.length === 0) {
    return null;
  }

  return (
    <section className="preparation-reminders" aria-labelledby="reminder-heading">
      <div className="preparation-reminder-heading">
        <div>
          <p>準備が残っています</p>
          <h2 id="reminder-heading">開始前の予定</h2>
        </div>
        <span>{reminders.length}件</span>
      </div>

      <div className="preparation-reminder-list">
        {reminders.map((reminder) => (
          <button
            type="button"
            key={reminder.event.id}
            onClick={() => onEventClick(reminder.event)}
          >
            <strong>{reminder.event.title}</strong>
            <span>
              あと{reminder.remainingText}です。未完了の準備が
              {reminder.incompleteCount}件あります。
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default PreparationReminderList;
