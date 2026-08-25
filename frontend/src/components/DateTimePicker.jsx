import { useEffect, useRef, useState } from "react";
import {
  WEEKDAY_NAMES,
  addMonths,
  getDateKey,
  getMonthDates,
  isSameDay,
  parseDateTime,
} from "../dateUtils";

const TIME_OPTIONS = Array.from({ length: 24 * 4 }, (_, index) => {
  const minutes = index * 15;
  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
});

function formatDateLabel(date) {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日（${WEEKDAY_NAMES[date.getDay()]}）`;
}

function normalizeTimeInput(inputValue) {
  const match = inputValue.match(/^(\d{1,2}):(\d{2})$/);

  if (!match) {
    return null;
  }

  const hour = Number(match[1]);
  const minute = Number(match[2]);

  if (hour > 23 || minute > 59) {
    return null;
  }

  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function DateTimePicker({
  defaultTime = "09:00",
  id,
  label,
  min,
  onChange,
  optional = false,
  value,
}) {
  const pickerRef = useRef(null);
  const timeInputRef = useRef(null);
  const timePickerRef = useRef(null);
  const selectedDate = parseDateTime(value) ?? new Date();
  const selectedDateKey = getDateKey(selectedDate);
  const selectedTime = value?.slice(11, 16) || "09:00";
  const minimumDateKey = min?.slice(0, 10) || "";
  const minimumTime = min?.slice(11, 16) || "";
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [isTimeOptionsOpen, setIsTimeOptionsOpen] = useState(false);
  const [displayedMonth, setDisplayedMonth] = useState(
    new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1),
  );

  // 入力途中の文字列はDOM側に保持し、完成した時刻だけ親へ渡します。
  useEffect(() => {
    if (timeInputRef.current) {
      timeInputRef.current.value = selectedTime;
    }
  }, [selectedTime]);

  useEffect(() => {
    if (!isCalendarOpen && !isTimeOptionsOpen) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!pickerRef.current?.contains(event.target)) {
        setIsCalendarOpen(false);
      }
      if (!timePickerRef.current?.contains(event.target)) {
        setIsTimeOptionsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [isCalendarOpen, isTimeOptionsOpen]);

  function openCalendar() {
    setIsTimeOptionsOpen(false);
    setDisplayedMonth(
      new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1),
    );
    setIsCalendarOpen((currentValue) => !currentValue);
  }

  function handleDateChange(date) {
    const nextDateKey = getDateKey(date);
    const nextTime =
      nextDateKey === minimumDateKey && selectedTime < minimumTime
        ? minimumTime
        : selectedTime;

    onChange(`${nextDateKey}T${nextTime}`);
    setIsCalendarOpen(false);
  }

  function handleTimeInputChange(event) {
    const nextInputValue = event.target.value;
    const normalizedTime = normalizeTimeInput(nextInputValue);

    if (normalizedTime) {
      onChange(`${selectedDateKey}T${normalizedTime}`);
    }
  }

  function handleTimeOptionSelect(time) {
    if (timeInputRef.current) {
      timeInputRef.current.value = time;
      timeInputRef.current.focus();
    }
    onChange(`${selectedDateKey}T${time}`);
    setIsTimeOptionsOpen(false);
  }

  const calendarDates = getMonthDates(displayedMonth);
  const today = new Date();

  return (
    <div className="date-time-field">
      <span className="date-time-label">
        {label}
        {optional && <small>任意</small>}
      </span>
      {optional && !value ? (
        <button
          className="empty-date-time-button"
          type="button"
          onClick={() => onChange(`${getDateKey(today)}T${defaultTime}`)}
        >
          ＋ 日時を設定
        </button>
      ) : (
        <div className="date-time-controls">
          <div className="date-picker" ref={pickerRef}>
            <button
              className="date-picker-button"
              id={`${id}-date`}
              type="button"
              aria-expanded={isCalendarOpen}
              aria-haspopup="dialog"
              onClick={openCalendar}
            >
              <span aria-hidden="true">▦</span>
              {formatDateLabel(selectedDate)}
            </button>

            {isCalendarOpen && (
              <div
                className="date-picker-popover"
                role="dialog"
                aria-label={`${label}の日付を選択`}
              >
                <div className="date-picker-header">
                  <strong>
                    {displayedMonth.getFullYear()}年
                    {displayedMonth.getMonth() + 1}月
                  </strong>
                  <div>
                    <button
                      type="button"
                      aria-label="前の月"
                      onClick={() =>
                        setDisplayedMonth((currentMonth) =>
                          addMonths(currentMonth, -1),
                        )
                      }
                    >
                      ‹
                    </button>
                    <button
                      type="button"
                      aria-label="次の月"
                      onClick={() =>
                        setDisplayedMonth((currentMonth) =>
                          addMonths(currentMonth, 1),
                        )
                      }
                    >
                      ›
                    </button>
                  </div>
                </div>

                <div className="date-picker-weekdays" aria-hidden="true">
                  {WEEKDAY_NAMES.map((weekday) => (
                    <span key={weekday}>{weekday}</span>
                  ))}
                </div>

                <div className="date-picker-days">
                  {calendarDates.map((date) => {
                    const dateKey = getDateKey(date);
                    const isOutsideMonth =
                      date.getMonth() !== displayedMonth.getMonth();
                    const isSelected = dateKey === selectedDateKey;

                    return (
                      <button
                        className={`${isOutsideMonth ? "is-outside-month" : ""}${isSelected ? " is-selected" : ""}${isSameDay(date, today) ? " is-today" : ""}`}
                        type="button"
                        disabled={Boolean(
                          minimumDateKey && dateKey < minimumDateKey,
                        )}
                        aria-label={`${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`}
                        aria-pressed={isSelected}
                        key={dateKey}
                        onClick={() => handleDateChange(date)}
                      >
                        {date.getDate()}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div
            className="time-picker"
            ref={timePickerRef}
            onKeyDown={(event) => {
              if (event.key === "Escape" && isTimeOptionsOpen) {
                event.stopPropagation();
                setIsTimeOptionsOpen(false);
              }
            }}
          >
            <input
              className="time-picker-input"
              id={`${id}-time`}
              type="text"
              role="combobox"
              aria-autocomplete="none"
              aria-controls={`${id}-time-options`}
              aria-expanded={isTimeOptionsOpen}
              aria-label={`${label}の時刻`}
              autoComplete="off"
              defaultValue={selectedTime}
              maxLength="5"
              pattern="([01]?[0-9]|2[0-3]):[0-5][0-9]"
              placeholder="hh:mm"
              ref={timeInputRef}
              required
              title="時刻は13:50の形式で入力してください"
              onBlur={(event) => {
                const normalizedTime = normalizeTimeInput(
                  event.currentTarget.value,
                );
                if (normalizedTime) {
                  event.currentTarget.value = normalizedTime;
                }
              }}
              onChange={handleTimeInputChange}
            />
            <button
              className="time-picker-toggle"
              type="button"
              aria-label={`${label}の時刻候補を表示`}
              onClick={() => {
                setIsCalendarOpen(false);
                setIsTimeOptionsOpen((isOpen) => !isOpen);
              }}
            >
              ▾
            </button>

            {isTimeOptionsOpen && (
              <div
                className="time-picker-options"
                id={`${id}-time-options`}
                role="listbox"
                aria-label={`${label}の15分刻みの時刻候補`}
              >
                {TIME_OPTIONS.map((time) => (
                  <button
                    type="button"
                    role="option"
                    aria-selected="false"
                    key={time}
                    onClick={() => handleTimeOptionSelect(time)}
                  >
                    {time}
                  </button>
                ))}
              </div>
            )}
          </div>
          {optional && (
            <button
              className="clear-date-time-button"
              type="button"
              aria-label={`${label}を削除`}
              title={`${label}を削除`}
              onClick={() => onChange("")}
            >
              ×
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default DateTimePicker;
