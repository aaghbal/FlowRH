import { useState } from "react";
import { Clock, Search, UserCheck, UserX, Timer, Download } from "lucide-react";

const RECORDS = Array.from({ length: 15 }, (_, i) => ({
  id: i + 1,
  emp: ["Mohammed Alami", "Sara El Amrani", "Karim Benali", "Fatima Zahra", "Hassan Bennis"][i % 5],
  dept: ["Commercial", "RH", "Technique", "Finance", "Direction"][i % 5],
  date: `0${3 - (i % 3)}/06/2026`,
  entree: i % 6 === 0 ? "09:24" : `0${8 + (i % 2)}:${String(i * 7 % 60).padStart(2, "0")}`,
  sortie: i % 9 === 0 ? null : `1${7 + (i % 2)}:${String((i * 13) % 60).padStart(2, "0")}`,
  heures: i % 9 === 0 ? null : `${7 + (i % 3)}h${String((i * 17) % 60).padStart(2, "0")}`,
  statut: i % 9 === 0 ? "present_no_exit" : i % 6 === 0 ? "late" : "present",
}));

const STATUS_MAP = {
  present:         { label: "Présent",          cls: "badge-active" },
  late:            { label: "En retard",         cls: "badge-pending" },
  absent:          { label: "Absent",            cls: "badge-danger" },
  present_no_exit: { label: "Sortie manquante",  cls: "badge-pending" },
};

export default function Attendance() {
  const [search, setSearch] = useState("");
  const [dateFilter, setDateFilter] = useState("03/06/2026");

  const filtered = RECORDS.filter(r =>
    r.emp.toLowerCase().includes(search.toLowerCase()) &&
    (dateFilter === "" || r.date === dateFilter)
  );

  const stats = {
    presents: RECORDS.filter(r => r.statut !== "absent").length,
    retards:  RECORDS.filter(r => r.statut === "late").length,
    absents:  RECORDS.filter(r => r.statut === "absent").length,
  };

  return (
    <div className="space-y-5">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Présents", count: stats.presents, icon: UserCheck, color: "text-green-500", bg: "bg-green-50 border-green-200" },
          { label: "Retards",  count: stats.retards,  icon: Timer,     color: "text-yellow-500", bg: "bg-yellow-50 border-yellow-200" },
          { label: "Absents",  count: stats.absents,  icon: UserX,     color: "text-red-400",    bg: "bg-red-50 border-red-100" },
        ].map(({ label, count, icon: Icon, color, bg }) => (
          <div key={label} className={`card border flex items-center gap-4 ${bg}`}>
            <Icon size={32} className={color} />
            <div>
              <div className={`text-3xl font-black ${color}`}>{count}</div>
              <div className="text-sm font-medium text-brand-gray">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-4 py-2.5 flex-1 min-w-[200px]">
          <Search size={15} className="text-brand-gray flex-shrink-0" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher un employé..."
            className="bg-transparent text-sm outline-none w-full placeholder-brand-lgray text-brand-purple"
          />
        </div>
        <input
          type="date"
          className="input !w-auto"
          onChange={e => {
            const d = e.target.value;
            if (d) {
              const [y, m, day] = d.split("-");
              setDateFilter(`${day}/${m}/${y}`);
            } else setDateFilter("");
          }}
        />
        <button className="btn-ghost flex items-center gap-2">
          <Download size={15} /> Export
        </button>
      </div>

      {/* Table */}
      <div className="card !p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Employé", "Département", "Date", "Entrée", "Sortie", "Heures", "Statut"].map(h => (
                  <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-brand-gray uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(rec => {
                const st = STATUS_MAP[rec.statut];
                return (
                  <tr key={rec.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                          {rec.emp.split(" ").map(n => n[0]).join("").slice(0, 2)}
                        </div>
                        <span className="text-sm font-semibold text-brand-purple">{rec.emp}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-brand-gray">{rec.dept}</td>
                    <td className="px-5 py-3.5 text-sm text-brand-gray">{rec.date}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-sm font-semibold ${rec.statut === "late" ? "text-yellow-600" : "text-brand-purple"}`}>
                        {rec.entree}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-sm text-brand-gray">{rec.sortie || "—"}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5">
                        <Clock size={13} className="text-brand-orange" />
                        <span className="text-sm font-semibold text-brand-purple">{rec.heures || "—"}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={st.cls}>{st.label}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
