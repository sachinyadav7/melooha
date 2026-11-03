"use client";

import { useEffect, useRef, useState } from "react";

import * as api from "../lib/api";

const todayString = () => new Date().toISOString().slice(0, 10);

export default function BirthForm({ existingUser, onDone }) {
  const [cities, setCities] = useState(null);
  const [citiesError, setCitiesError] = useState(null);
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [city, setCity] = useState("");
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const createdUser = useRef(existingUser || null); // so a retry never creates a second account

  const loadCities = () => {
    setCitiesError(null);
    api.getCities().then(setCities).catch((e) => setCitiesError(e.message));
  };
  useEffect(loadCities, []);

  const validate = () => {
    const found = {};
    if (!createdUser.current && !name.trim()) found.name = "Please enter your name.";
    if (!date) found.date = "Please choose your date of birth.";
    else if (date > todayString()) found.date = "Your date of birth cannot be in the future.";
    if (!time) found.time = "Please enter your time of birth.";
    if (!city) found.city = "Please choose your birth city.";
    return found;
  };

  const submit = async (event) => {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    setSubmitError(null);
    try {
      if (!createdUser.current) createdUser.current = await api.createUser(name.trim());
      const chart = await api.saveChart(createdUser.current.user_id, { date, time, city });
      onDone({ user: createdUser.current, chart });
    } catch (e) {
      setSubmitError(e.message);
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={submit} noValidate>
      <div className="stack-sm">
        <h1>Let us find your chart</h1>
        <p className="muted">Your chart is made from when and where you were born. It takes less than a minute.</p>
      </div>

      {!createdUser.current && (
        <div className="field">
          <label className="label" htmlFor="name">Your name</label>
          <input id="name" className={`input${errors.name ? " has-error" : ""}`} value={name} autoComplete="given-name"
                 onChange={(e) => setName(e.target.value)} />
          {errors.name && <span className="error-text">{errors.name}</span>}
        </div>
      )}

      <div className="field">
        <label className="label" htmlFor="date">Date of birth</label>
        <input id="date" type="date" max={todayString()} className={`input${errors.date ? " has-error" : ""}`} value={date}
               onChange={(e) => setDate(e.target.value)} />
        {errors.date && <span className="error-text">{errors.date}</span>}
      </div>

      <div className="field">
        <label className="label" htmlFor="time">Time of birth</label>
        <input id="time" type="time" className={`input${errors.time ? " has-error" : ""}`} value={time}
               onChange={(e) => setTime(e.target.value)} />
        <span className="help">Not sure? Ask a family member. Even a time within an hour or two helps.</span>
        {errors.time && <span className="error-text">{errors.time}</span>}
      </div>

      <div className="field">
        <label className="label" htmlFor="city">Birth city</label>
        {citiesError ? (
          <div className="banner" role="alert">
            <span>{citiesError}</span>
            <button type="button" className="btn btn-secondary" onClick={loadCities}>Try again</button>
          </div>
        ) : (
          <select id="city" className={`input${errors.city ? " has-error" : ""}`} value={city} disabled={!cities}
                  onChange={(e) => setCity(e.target.value)}>
            <option value="">{cities ? "Choose your city" : "Loading cities..."}</option>
            {cities?.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
        <span className="help">Do not see your city? Choose the nearest big city.</span>
        {errors.city && <span className="error-text">{errors.city}</span>}
      </div>

      {submitError && (
        <div className="banner" role="alert">
          <span>{submitError}</span>
        </div>
      )}

      <button className="btn btn-primary" type="submit" disabled={busy}>
        {busy ? "Making your chart..." : "Show my chart"}
      </button>
    </form>
  );
}
