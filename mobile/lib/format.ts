/** Small display formatters shared across screens (Hermes-safe — no Intl). */

const WEEKDAYS_LONG = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];
const WEEKDAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** 1130 -> "1,130" (thousands separators, no reliance on Intl). */
export function thousands(value: number): string {
  return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/** "poha_masala" -> "Poha Masala". */
export function titleCase(label: string): string {
  return label.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** A friendly first name from an email local part ("demo.user@x" -> "Demo"). */
export function displayName(email: string | null): string {
  if (!email) return 'there';
  const first = email.split('@')[0]?.split(/[._-]/)[0] ?? '';
  return first ? first.charAt(0).toUpperCase() + first.slice(1) : 'there';
}

export function initial(email: string | null): string {
  return email ? email.charAt(0).toUpperCase() : '?';
}

/** "Wednesday, 16 July" */
export function longDate(d: Date): string {
  return `${WEEKDAYS_LONG[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function weekdayShort(d: Date): string {
  return WEEKDAYS_SHORT[d.getDay()];
}

/** Local YYYY-MM-DD key for bucketing entries by calendar day. */
export function dateKey(d: Date): string {
  const month = `${d.getMonth() + 1}`.padStart(2, '0');
  const day = `${d.getDate()}`.padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

/** "8:12 am" from an ISO timestamp. */
export function shortTime(iso: string): string {
  const d = new Date(iso);
  const minutes = `${d.getMinutes()}`.padStart(2, '0');
  const ampm = d.getHours() >= 12 ? 'pm' : 'am';
  const hour = d.getHours() % 12 || 12;
  return `${hour}:${minutes} ${ampm}`;
}

/** "Today" / "Yesterday" / "Monday, 14 July" for a day bucket. */
export function dayLabel(key: string, today: Date): string {
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (key === dateKey(today)) return 'Today';
  if (key === dateKey(yesterday)) return 'Yesterday';
  return longDate(new Date(`${key}T00:00:00`));
}
