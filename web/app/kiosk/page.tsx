"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { Activity, Thermometer, Droplets, AlertTriangle, Timer, X, Play } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function KioskMode() {
  const { data, error } = useSWR("/api/kiosk/tanks", fetcher, {
    refreshInterval: 60000, // 60s throttling as per PRD
  });

  const [timerSeconds, setTimerSeconds] = useState(0);
  const [timerActive, setTimerActive] = useState(false);
  const [showTimerSetup, setShowTimerSetup] = useState(false);

  useEffect(() => {
    let interval: any;
    if (timerActive && timerSeconds > 0) {
      interval = setInterval(() => {
        setTimerSeconds((prev) => {
          if (prev <= 1) {
             setTimerActive(false);
             return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timerActive, timerSeconds]);

  const startTimer = (minutes: number) => {
    setTimerSeconds(minutes * 60);
    setTimerActive(true);
    setShowTimerSetup(false);
  };
  
  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (error) return <div className="h-screen w-screen bg-black text-red-500 flex items-center justify-center text-4xl font-black">CONNECTION LOST</div>;
  if (!data) return <div className="h-screen w-screen bg-black flex items-center justify-center">...</div>;

  const tanks = data?.data?.tanks || [];

  return (
    <div className="fixed inset-0 bg-black text-white overflow-hidden flex items-center justify-center p-4 z-[9999]">
      {/* 
        Kiosk mode completely overtakes the screen. 
        It is designed for low-power wall displays. 
      */}

      {/* Timer Trigger */}
      <button 
        onClick={() => setShowTimerSetup(true)}
        className="absolute top-8 right-8 z-[10000] p-4 bg-zinc-900 rounded-full text-zinc-500 hover:text-white transition-colors"
      >
        <Timer className="w-8 h-8" />
      </button>

      {/* Timer Setup Modal */}
      {showTimerSetup && (
        <div className="absolute inset-0 z-[10001] bg-black/90 backdrop-blur-md flex flex-col items-center justify-center">
          <button onClick={() => setShowTimerSetup(false)} className="absolute top-8 right-8 p-4 text-zinc-500 hover:text-white">
             <X className="w-12 h-12" />
          </button>
          <h2 className="text-6xl font-black mb-12 tracking-tighter">QUICK TIMER</h2>
          <div className="grid grid-cols-3 gap-8">
            {[15, 30, 45, 60, 90, 120].map(mins => (
               <button 
                 key={mins}
                 onClick={() => startTimer(mins)}
                 className="bg-zinc-900 border-2 border-zinc-800 hover:border-white rounded-3xl p-12 text-5xl font-bold flex flex-col items-center gap-4 transition-all"
               >
                 {mins} <span className="text-2xl text-zinc-500 uppercase tracking-widest">MIN</span>
               </button>
            ))}
          </div>
        </div>
      )}

      {/* Active Timer Overlay */}
      {timerActive && (
        <div className="absolute top-0 left-0 right-0 z-[9990] bg-blue-950 border-b-8 border-blue-500 shadow-2xl flex flex-col items-center justify-center py-12 animate-in slide-in-from-top duration-700">
           <span className="text-4xl text-blue-400 font-bold tracking-widest uppercase mb-4 flex items-center gap-4"><Timer className="w-10 h-10 animate-pulse"/> Brew Timer Active</span>
           <span className="text-[12rem] leading-none font-black tracking-tighter tabular-nums text-white">
              {formatTime(timerSeconds)}
           </span>
           <button onClick={() => setTimerActive(false)} className="mt-8 bg-blue-900 text-blue-300 px-8 py-3 rounded-full text-2xl font-bold uppercase tracking-widest hover:bg-blue-800">Dismiss</button>
        </div>
      )}
      
      {tanks.length === 0 ? (
        <div className="text-4xl text-zinc-600 font-black tracking-widest">SYSTEM IDLE</div>
      ) : (
        <div className="grid grid-cols-1 gap-8 w-full h-full max-w-7xl max-h-[800px]">
          {tanks.map((tank: any) => {
            const isAlert = tank.alert_state === "critical";
            const isWarning = tank.alert_state === "warning";
            
            // Map alert state to stark background colors
            let bgColor = "bg-zinc-900";
            if (isAlert) bgColor = "bg-red-950 border-4 border-red-500";
            else if (isWarning) bgColor = "bg-yellow-950 border-4 border-yellow-500";
            else if (tank.status === "Fermenting") bgColor = "bg-emerald-950 border-2 border-emerald-900";

            return (
              <div key={tank.tank_id} className={`rounded-[3rem] p-12 flex flex-col justify-between transition-colors duration-1000 ${bgColor}`}>
                
                <div className="flex justify-between items-start">
                  <div>
                    <h1 className="text-7xl font-black tracking-tighter mb-4">{tank.name}</h1>
                    <div className="flex items-center gap-4 text-3xl font-bold text-zinc-400">
                      <span className="flex items-center gap-2 bg-black/30 px-6 py-2 rounded-full">
                        <Activity className="w-8 h-8" />
                        {tank.status}
                      </span>
                      {isAlert && (
                        <span className="flex items-center gap-2 bg-red-500 text-white px-6 py-2 rounded-full animate-pulse">
                          <AlertTriangle className="w-8 h-8" />
                          CRITICAL ALERT
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-zinc-500 tracking-widest uppercase">{tank.tank_id}</div>
                  </div>
                </div>

                <div className="flex justify-between items-end">
                  <div className="flex flex-col">
                    <span className="text-3xl font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2"><Thermometer/> Temp</span>
                    <span className="text-9xl font-black tracking-tighter tabular-nums">
                      {tank.temp_c?.toFixed(1)}<span className="text-6xl text-zinc-600">°C</span>
                    </span>
                  </div>
                  
                  <div className="flex flex-col text-right">
                    <span className="text-3xl font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center justify-end gap-2"><Droplets/> Gravity</span>
                    <span className="text-9xl font-black tracking-tighter tabular-nums">
                      {tank.sg?.toFixed(3)}
                    </span>
                  </div>
                </div>
                
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
