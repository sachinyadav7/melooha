"use client";

import { useCallback, useEffect, useState } from "react";

import AskScreen from "../components/AskScreen";
import BirthForm from "../components/BirthForm";
import ChartScreen from "../components/ChartScreen";
import Header from "../components/Header";
import { ErrorView, LoadingView } from "../components/StateViews";
import * as api from "../lib/api";

const STORAGE_KEY = "melooha.userId";

const readSaved = () => {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
};
const save = (id) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    /* private mode: the user simply signs in fresh next time */
  }
};
const forget = () => {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
};

export default function Home() {
  const [phase, setPhase] = useState("booting"); // booting, onboarding, chart, ask, fatal
  const [waking, setWaking] = useState(false);
  const [fatal, setFatal] = useState("");
  const [user, setUser] = useState(null);
  const [chart, setChart] = useState(null);

  const boot = useCallback(async () => {
    setPhase("booting");
    const timer = setTimeout(() => setWaking(true), 3000);
    try {
      await api.wakeServer();
      const saved = readSaved();
      if (!saved) return setPhase("onboarding");

      let loadedUser;
      try {
        loadedUser = await api.getUser(saved);
      } catch (e) {
        if (e.code === "user_not_found") {
          forget();
          return setPhase("onboarding");
        }
        throw e;
      }
      setUser(loadedUser);

      try {
        const loadedChart = await api.getChart(saved);
        setChart(loadedChart);
        setPhase(loadedUser.experiment_group === "chart" ? "chart" : "ask");
      } catch (e) {
        if (e.code === "chart_not_found") return setPhase("onboarding");
        throw e;
      }
    } catch (e) {
      setFatal(e.message);
      setPhase("fatal");
    } finally {
      clearTimeout(timer);
      setWaking(false);
    }
  }, []);

  useEffect(() => {
    boot();
  }, [boot]);

  const onboarded = ({ user: newUser, chart: newChart }) => {
    save(newUser.user_id);
    setUser(newUser);
    setChart(newChart);
    // Only the chart group sees the chart. The control group goes straight to asking.
    setPhase(newUser.experiment_group === "chart" ? "chart" : "ask");
  };

  const setBalance = (balance) => setUser((u) => ({ ...u, balance }));
  const showChart = user?.experiment_group === "chart";

  return (
    <main className="app">
      {phase !== "booting" && phase !== "fatal" && <Header balance={user?.balance} />}

      {phase === "booting" && <LoadingView waking={waking} />}
      {phase === "fatal" && <ErrorView message={fatal} onRetry={boot} />}
      {phase === "onboarding" && <BirthForm existingUser={user} onDone={onboarded} />}
      {phase === "chart" && (
        <ChartScreen user={user} chart={chart} onAsk={() => setPhase("ask")} onEditDetails={() => setPhase("onboarding")} />
      )}
      {phase === "ask" && (
        <AskScreen user={user} chart={chart} balance={user.balance} onBalance={setBalance} showChart={showChart}
                   onSeeChart={() => setPhase("chart")} />
      )}
    </main>
  );
}
