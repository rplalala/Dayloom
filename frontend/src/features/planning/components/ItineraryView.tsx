import { Fragment } from "react";
import type { Activity, Itinerary, Transfer, MinimumDailyCoverage, ProductWeather, PreferenceCoverage } from "../types";

function WeatherCard({ weather }: { weather: ProductWeather }) {
  const forecast = weather.status === "available" ? weather.forecast : null;
  return <aside aria-label="Daily weather" className="weather-strip">
    <strong>Weather</strong>
    {!forecast ? <span>Weather information is unavailable for this day.</span> : <>
      <div className="weather-metrics">
        {forecast.condition && <span>{forecast.condition}</span>}
        {forecast.min_temperature_c !== null && <span>Low: {forecast.min_temperature_c} °C</span>}
        {forecast.max_temperature_c !== null && <span>High: {forecast.max_temperature_c} °C</span>}
        {forecast.precipitation_probability_percent !== null && <span>Chance of rain: {forecast.precipitation_probability_percent}%</span>}
        {forecast.max_wind_speed_kph !== null && <span>Maximum wind: {forecast.max_wind_speed_kph} km/h</span>}
      </div>
      {weather.source_url === "https://open-meteo.com/" && <a href="https://open-meteo.com/">Open-Meteo</a>}
      <details className="weather-details"><summary>Weather details</summary>
        {weather.attribution && <p>{weather.attribution}</p>}
        {weather.source_url === "https://open-meteo.com/" && <p>
          <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
        </p>}
        <p>Forecasts may change.</p>
      </details>
    </>}
  </aside>;
}

function TransferCard({ transfer }: { transfer: Transfer }) {
  const label = transfer.mode ? { WALK: "Walk", TRANSIT: "Public transport", DRIVE: "Car transport" }[transfer.mode] : "Transport unverified";
  return (
    <aside className="activity-card" aria-label="Transfer">
      {transfer.preceding_end_time && <p>{formatTime(transfer.preceding_end_time)}: Previous activity ends</p>}
      <p>{label}: {transfer.provider_duration_seconds === null ? "Time unknown" :
        `about ${Math.ceil(transfer.provider_duration_seconds / 60)} min`}
        {" · "}{transfer.distance_meters === null ? "Distance unknown" :
          `${(transfer.distance_meters / 1000).toFixed(1)} km`}</p>
      {transfer.reserve_seconds > 0 && <p>Allow an additional {Math.ceil(transfer.reserve_seconds / 60)} min {transfer.mode === "DRIVE" ? "for pickup/drop-off." : "as a separate scheduling reserve."}</p>}
      {transfer.attribution && <p>Source: {transfer.attribution}</p>}
      {transfer.estimate_kind === "derived" && <p>This is a derived estimate, not a direct route observation.</p>}
      <p>{transfer.validation_state === "CONFIRMED" ? "Transfer conflict remains." :
        transfer.validation_state === "UNKNOWN" ? "Transfer feasibility is unverified." :
          "Based on the adopted route estimate; not a guarantee."}</p>
      {transfer.unknowns.map((value, index) => <p key={index}>{value}</p>)}
      {transfer.following_start_time && <p>{formatTime(transfer.following_start_time)}: Next activity starts</p>}
    </aside>
  );
}

function formatTime(value: string): string {
  const match = value.match(/T(\d{2}):(\d{2})/);
  return match ? `${match[1]}:${match[2]}` : value;
}

function ActivityCard({ activity }: { activity: Activity }) {
  return (
    <article className="activity-card">
      <div className="activity-time">
        {formatTime(activity.start_time)}–{formatTime(activity.end_time)}
      </div>
      <div className="activity-content">
        <h4>{activity.title}</h4>
        {activity.time_use === "free_window" && <p>Free window — optional suggestions</p>}
        {activity.time_use === "scheduled" && <p>Planned activity</p>}
        {activity.place_name && <p className="activity-place">{activity.place_name}</p>}
        {activity.location && <p>{activity.location}</p>}
        {activity.introduction && <p>{activity.introduction}</p>}
        {activity.notes && <p>{activity.notes}</p>}
        {activity.estimated_cost && (
          <p className="cost">
            Estimated cost: {activity.estimated_cost.currency} {activity.estimated_cost.amount}
          </p>
        )}
        {!!activity.nearby?.length && <section className="nearby-list" aria-label={`Nearby ${activity.place_name || activity.title}`}>
          <h5>Nearby options — not scheduled</h5>
          <ul>{activity.nearby.map((place, index) => <li key={index}>
            <strong>{place.place_name}</strong><p>{place.reason}</p>
            {place.area && <p>{place.area}</p>}
            {place.uncertainty && <p>{place.uncertainty}</p>}
            {place.attribution && <p>Source: {place.attribution}</p>}
          </li>)}</ul>
        </section>}
      </div>
    </article>
  );
}

export function ItineraryView({ itinerary, minimumCoverage = [], policyCompletion, preferenceCoverage = [] }: {
  preferenceCoverage?: PreferenceCoverage[];
  policyCompletion?: "complete" | "incomplete" | "unassessed";
  itinerary: Itinerary; minimumCoverage?: MinimumDailyCoverage[];
}) {
  return (
    <section className="itinerary" aria-labelledby="itinerary-title">
      {policyCompletion === "incomplete" && <p role="status">
        This itinerary is incomplete: some primary-visit or repetition requirements remain unresolved.
      </p>}
      <header className="itinerary-header">
        <div>
          <p className="eyebrow">Your itinerary</p>
          <h2 id="itinerary-title">{itinerary.destination}</h2>
        </div>
        <p>
          {itinerary.start_date} to {itinerary.end_date}
        </p>
      </header>
      {preferenceCoverage.length > 0 && <section aria-label="Preference coverage">
        <h3>Your interests</h3>
        <p>Soft planning goals based on suggested matches, not verified suitability or opening information.</p>
        <ul>{preferenceCoverage.map((row, index) => <li key={index}>
          {row.preference}: {row.scheduled} of {row.target} suggested visits arranged
          {row.target_origin === "current_trip_focus" ? " (trip focus)" : ""}.
          {row.status === "gap" && ` ${row.remaining} remaining; this is a soft preference gap.`}
          {row.status === "unassessed" && " Coverage could not be fully assessed."}
          {row.status === "covered" && " Soft target covered."}
        </li>)}</ul>
      </section>}
      {minimumCoverage.filter(row => row.status !== "satisfied").map(row => (
        <p key={row.date} role={row.status === "missing" ? "status" : undefined}>
          {row.date}: {row.status === "missing"
            ? "Minimum daily coverage remains unmet: no countable main visit was arranged."
            : row.status === "exempt"
              ? "Exempt from minimum sightseeing coverage because of a fixed user commitment."
              : "Minimum daily coverage could not be fully assessed."}
        </p>
      ))}
      <div className="itinerary-days">
        {itinerary.days.map((day, index) => (
          <section className="itinerary-day" key={day.date}>
            <div className="day-heading">
              <span>Day {index + 1}</span>
              <h3>{day.date}</h3>
            </div>
            <div className="activity-list">
              {day.weather && <WeatherCard weather={day.weather} />}
              {day.activities.length > 0 ? (
                day.activities.map((activity) => (
                  <Fragment key={activity.activity_id}>
                    {(itinerary.transfers ?? []).filter(t => t.to_activity_id === activity.activity_id)
                      .map(t => <TransferCard key={`${t.from_activity_id}:${t.to_activity_id}`} transfer={t} />)}
                    <ActivityCard activity={activity} />
                  </Fragment>
                ))
              ) : (
                <p className="empty-day">No scheduled activities.</p>
              )}
            </div>
          </section>
        ))}
      </div>
      {!!itinerary.reference_recommendations?.length && (
        <section aria-label="Optional reference recommendations">
          <h3>Optional references — not scheduled</h3>
          <p>Additional options to consider independently. No bookings have been made.</p>
          {itinerary.reference_recommendations.map((reference, index) => (
            <article className="activity-card" key={reference.source_place_id ?? index}>
              <div className="activity-content">
                <h4>{reference.place_name}</h4>
                <p>{reference.reason}</p>
                {reference.associated_day && <p>Suggested day: {reference.associated_day}</p>}
                {reference.area && <p>{reference.area}</p>}
                <p>{reference.source_ref
                  ? "Linked to supplied place information; current details may be uncertain."
                  : "Model-generated suggestion; not live-verified."}</p>
                {reference.uncertainty && <p>{reference.uncertainty}</p>}
              </div>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
