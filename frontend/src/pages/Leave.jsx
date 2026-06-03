import { useState } from "react";
import { CalendarDays, Clock, CheckCircle, XCircle, Plus, Search } from "lucide-react";

const LEAVES = [
  { id: 1, emp: "Mohammed Alami",  type: "Congé annuel", from: "10/06/2026", to: "14/06/2026", days: 5,  status: "pending",  dept: "Commercial" },
  { id: 2, emp: "Fatima Zahra",    type: "Maladie",      from: "08/06/2026", to: "10/06/2026", days: 3,  status: "pending",  dept: "RH" },
  { id: 3, emp: "Karim Benali",    type: "Congé annuel", from: "01/06/2026", to: "07/06/2026", days: 7,  status: "approved", dept: "Technique" },
  { id: 4, emp: "Sara El Amrani",  type: "Maternité",    from: "15/05/2026", to: "15/08/2026", days: 90, status: "approved", dept: "Finance" },
  { id: 5, emp: "Hassan Bennis",   type: "Sans solde",   from: "20/06/2026", to: "30/06/2026", days: 11, status: "rejected", dept: "Commercial" },
  { id: 6, emp: "Nadia Cherkaoui", type: "Congé annuel", from: "25/06/2026", to: "02/07/2026", days: 8,  status: "pending",  dept: "Direction" },
];

const STATUS_MAP = {
  pending:  { label: "En attente", cls: "badge-pending" },
  approved: { label: "Approuvé",   cls: "badge-active" },
  rejected: { label: "Refusé",     cls: "badge-danger" },
};

const TYPE_COLORS = {
  "Congé annuel": "#ff5c35",
  "Maladie":      "#fdbb36",
  "Maternité":    "#1aacd2",
  "Sans solde":   "#616175",
};

export default function Leave() {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = LEAVES.filter(l =>
    (filter === "all" || l.status === filter) &&
    l.emp.toLowerCase().includes(search.toLowerCase())
  );

  const counts = {
    pending:  LEAVES.filter(l => l.status === "pending").length,
    approved: LEAVES.filter(l => l.status === "approved").length,
    rejected: LEAVES.filter(l => l.status === "rejected").length,
  };

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "En attente",  count: counts.pending,  icon: Clock,        bg: "bg-yellow-50",  border: "border-yellow-200", text: "text-yellow-700", icon_cls: "text-yellow-500" },
          { label: "Approuvés",   count: counts.approved, icon: CheckCircle,  bg: "bg-green-50",   border: "border-green-200",  text: "text-green-700",  icon_cls: "text-green-500" },
          { label: "Refusés",     count: counts.rejected, icon: XCircle,      bg: "bg-red-50",     border: "border-red-100",    text: "text-red-700",    icon_cls: "text-red-400" },
        ].map(({ label, count, icon: Icon, bg, border, text, icon_cls }) => (
          <div key={label} className={`card border ${border} ${bg} flex items-center gap-4`}>
            <Icon size={32} className={icon_cls} />
            <div>
              <div className={`text-3xl font-black ${text}`}>{count}</div>
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
            placeholder="Rechercher..."
            className="bg-transparent text-sm outline-none w-full placeholder-brand-lgray text-brand-purple"
          />
        </div>

        <div className="flex rounded-xl border border-gray-200 overflow-hidden bg-white">
          {[["all", "Tous"], ["pending", "En attente"], ["approved", "Approuvés"], ["rejected", "Refusés"]].map(([v, l]) => (
            <button
              key={v}
              onClick={() => setFilter(v)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                filter === v ? "bg-brand-orange text-white" : "text-brand-gray hover:bg-gray-50"
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        <button className="btn-primary flex items-center gap-2">
          <Plus size={15} /> Nouvelle demande
        </button>
      </div>

      {/* Table */}
      <div className="card !p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Employé", "Type de congé", "Du", "Au", "Jours", "Département", "Statut", "Actions"].map(h => (
                  <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-brand-gray uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(leave => {
                const st = STATUS_MAP[leave.status];
                return (
                  <tr key={leave.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors group">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                          {leave.emp.split(" ").map(n => n[0]).join("").slice(0, 2)}
                        </div>
                        <span className="text-sm font-semibold text-brand-purple">{leave.emp}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: TYPE_COLORS[leave.type] }} />
                        <span className="text-sm text-brand-purple">{leave.type}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-brand-gray">{leave.from}</td>
                    <td className="px-5 py-3.5 text-sm text-brand-gray">{leave.to}</td>
                    <td className="px-5 py-3.5">
                      <span className="font-bold text-brand-purple">{leave.days}</span>
                      <span className="text-xs text-brand-gray ml-1">j</span>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-brand-gray">{leave.dept}</td>
                    <td className="px-5 py-3.5">
                      <span className={st.cls}>{st.label}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      {leave.status === "pending" && (
                        <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="px-3 py-1 bg-green-100 text-green-700 text-xs rounded-lg font-semibold hover:bg-green-200 transition-colors flex items-center gap-1">
                            <CheckCircle size={12} /> Approuver
                          </button>
                          <button className="px-3 py-1 bg-red-100 text-red-600 text-xs rounded-lg font-semibold hover:bg-red-200 transition-colors flex items-center gap-1">
                            <XCircle size={12} /> Refuser
                          </button>
                        </div>
                      )}
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
