"use client";

import useSWR from "swr";
import { Activity, Thermometer, Droplets, AlertTriangle } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function KioskMode() {
  const { data, error } = useSWR("/api/kiosk/tanks", fetcher, {
    refreshInterval: 60000, // 60s throttling as per PRD
  });

  if (error) return <div className="h-screen w-screen bg-black text-red-500 flex items-center justify-center text-4xl font-black">CONNECTION LOST</div>;
  if (!data) return <div className="h-screen w-screen bg-black flex items-center justify-center">...</div>;

  const tanks = data?.data?.tanks || [];

  return (
    <div className="fixed inset-0 bg-black text-white overflow-hidden flex items-center justify-center p-4 z-[9999]">
      {/* 
        Kiosk mode completely overtakes the screen. 
        It is designed for low-power wall displays. 
      */}
      
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
