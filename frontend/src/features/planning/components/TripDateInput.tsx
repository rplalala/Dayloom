import { useRef, useState } from "react";
import { addCalendarDays, isValidISODate } from "../datePolicy";

interface TripDateInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSelect?: () => void;
  min?: string;
  max?: string;
  disabled?: boolean;
  describedBy?: string;
}

function monthStart(value: string): string {
  return `${value.slice(0, 7)}-01`;
}

function shiftMonth(value: string, months: number): string {
  const date = new Date(`${monthStart(value)}T12:00:00Z`);
  date.setUTCMonth(date.getUTCMonth() + months);
  return date.toISOString().slice(0, 10);
}

function monthDates(value: string): string[] {
  const first = new Date(`${monthStart(value)}T12:00:00Z`);
  const count = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  return Array.from({ length: count }, (_, index) => addCalendarDays(monthStart(value), index));
}

function englishDate(value: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-US", { ...options, timeZone: "UTC" })
    .format(new Date(`${value}T12:00:00Z`));
}

export function TripDateInput({ label, value, onChange, onSelect, min, max, disabled, describedBy }: TripDateInputProps) {
  const [open, setOpen] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState("");
  const trigger = useRef<HTMLButtonElement>(null);
  const calendar = useRef<HTMLDivElement>(null);
  const savedDate = isValidISODate(value) ? value : min || new Date().toISOString().slice(0, 10);
  const selected = min && savedDate < min ? min : max && savedDate > max ? max : savedDate;
  const month = visibleMonth || monthStart(selected);

  function close() {
    setOpen(false);
    trigger.current?.focus();
  }

  function select(date: string) {
    onChange(date);
    onSelect?.();
    close();
  }

  function moveFocus(date: string) {
    if ((min && date < min) || (max && date > max)) return;
    if (monthStart(date) !== month) {
      setVisibleMonth(monthStart(date));
      requestAnimationFrame(() => calendar.current?.querySelector<HTMLButtonElement>(`[data-date="${date}"]`)?.focus());
    } else {
      calendar.current?.querySelector<HTMLButtonElement>(`[data-date="${date}"]`)?.focus();
    }
  }

  return <div className="trip-date-control" onKeyDown={event => {
    if (open && event.key === "Escape") { event.preventDefault(); close(); }
  }}>
    <label>{label}
      <input type="text" inputMode="numeric" placeholder="YYYY-MM-DD" pattern="[0-9]{4}-[0-9]{2}-[0-9]{2}"
        maxLength={10} value={value} onChange={event => onChange(event.target.value)}
        min={min} max={max} required disabled={disabled} aria-describedby={describedBy} />
    </label>
    <button type="button" className="date-trigger" ref={trigger} disabled={disabled}
      aria-label={`Choose ${label}`} aria-expanded={open}
      onClick={() => { if (open) close(); else { setVisibleMonth(monthStart(selected)); setOpen(true); } }}>
      Calendar
    </button>
    {open && <div className="date-calendar" role="dialog" aria-label={`${label} calendar`} ref={calendar}
      onKeyDown={event => {
        const target = event.target as HTMLElement;
        const date = target.dataset.date;
        if (!date) return;
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(date); return; }
        const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
        if (offset !== undefined) { event.preventDefault(); moveFocus(addCalendarDays(date, offset)); }
      }}>
      <div className="date-calendar-heading">
        <button type="button" aria-label="Previous month" disabled={!!min && shiftMonth(month, -1).slice(0, 7) < min.slice(0, 7)}
          onClick={() => setVisibleMonth(shiftMonth(month, -1))}>‹</button>
        <strong>{englishDate(month, { month: "long", year: "numeric" })}</strong>
        <button type="button" aria-label="Next month" disabled={!!max && shiftMonth(month, 1).slice(0, 7) > max.slice(0, 7)}
          onClick={() => setVisibleMonth(shiftMonth(month, 1))}>›</button>
      </div>
      <div className="date-calendar-weekdays" aria-hidden="true">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => <span key={day}>{day}</span>)}
      </div>
      <div className="date-calendar-days" aria-label="Calendar dates">
        {monthDates(month).map((date, index) => <button key={date} type="button" data-date={date}
          style={index === 0 ? { gridColumnStart: new Date(`${date}T12:00:00Z`).getUTCDay() + 1 } : undefined}
          aria-label={englishDate(date, { month: "long", day: "numeric", year: "numeric" })}
          aria-current={date === value ? "date" : undefined} disabled={(!!min && date < min) || (!!max && date > max)}
          onClick={() => select(date)}>{Number(date.slice(-2))}</button>)}
      </div>
    </div>}
  </div>;
}
