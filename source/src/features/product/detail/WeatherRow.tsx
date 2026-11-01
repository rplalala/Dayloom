import type { DetailDay } from './types';
import { Icon } from '../Icon';
import { monthDay, weekday } from './display';

const finite = (value?: number | null): value is number => typeof value === 'number' && Number.isFinite(value);
const format = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value);
const safeSource = (value?: string | null) => {
  try {
    const url = new URL(value || '');
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
  } catch { return undefined; }
};

export function WeatherRow({ day, sourceNumber }: { day: DetailDay; sourceNumber: number }) {
  const weather = day.weather;
  const low = weather?.temperature_min_c, high = weather?.temperature_max_c;
  const average = finite(low) && finite(high) ? low / 2 + high / 2 : null;
  const rain = weather?.precipitation_probability_percent;
  const source = safeSource(weather?.source_url);
  return <details className="weather-row weather-disclosure">
    <summary className="weather-line" aria-label={`Weather details for ${monthDay(day.date)}`} aria-description={`Estimated average ${average == null ? 'unavailable' : `${format(average)} degrees Celsius`}; rain chance ${finite(rain) ? `${format(rain)} percent` : 'unavailable'}`}>
      <span className="weather-date"><strong>{monthDay(day.date)}</strong><small>{weekday(day.date)}</small></span>
      <span className="weather-small-icon" aria-hidden="true"><Icon name={/rain/i.test(weather?.summary || '') ? 'rain' : /sun|clear/i.test(weather?.summary || '') ? 'sun' : 'cloud'} size={19} /></span>
      <span className="weather-average" title="Average temperature estimated from the daily low and high">{average == null ? 'Avg —' : `≈${format(average)}°C`}</span>
      <span className="weather-rain" title="Rain chance"><Icon name="rain" size={14} /><span>{finite(rain) ? `${format(rain)}%` : '—'}</span></span>
      <span className="weather-chevron" aria-hidden="true"><Icon name="chevron" size={14} /></span>
    </summary>
    <div className="weather-expanded">
      <strong>{weather?.summary || 'Weather unavailable'}</strong>
      {finite(low) && <span>Low {low}°C</span>}
      {finite(high) && <span>High {high}°C</span>}
      {average != null && <small>Average estimated from the daily low and high.</small>}
      {finite(rain) && <span>Rain chance {rain}%</span>}
      {finite(weather?.max_wind_speed_kph) && <span>Wind up to {weather.max_wind_speed_kph} km/h</span>}
      {weather?.attribution && <small>{weather.attribution}</small>}
      {source && <a href={source} target="_blank" rel="noopener noreferrer">Weather source {sourceNumber} ↗</a>}
    </div>
  </details>;
}
