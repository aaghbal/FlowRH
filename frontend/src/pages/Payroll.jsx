import { DollarSign, Download, TrendingUp, Users, Search } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const DATA = [
  { dept: "Commercial", salaire: 85000, effectif: 12 },
  { dept: "RH",         salaire: 42000, effectif: 6  },
  { dept: "Technique",  salaire: 120000, effectif: 18 },
  { dept: "Finance",    salaire: 65000, effectif: 9  },
  { dept: "Direction",  salaire: 95000, effectif: 5  },
];

const PAYSLIPS = Array.from({ length: 8 }, (_, i) => ({
  id: i + 1,
  emp: ["Mohammed Alami", "Sara El Amrani", "Karim Benali", "Fatima Zahra", "Hassan Bennis", "Nadia Cherkaoui", "Youssef Tahiri", "Amina Khalid"][i],
  poste: ["Manager", "RH Officer", "Technicien", "Comptable", "Commercial", "Directrice", "Dev", "Assistante"][i],
  brut: [12000, 8500, 10000, 9200, 7500, 18000, 11000, 7000][i],
  net:  [10200, 7225, 8500, 7820, 6375, 15300, 9350, 5950][i],
  statut: i < 5 ? "payé" : "en attente",
}));

const fmt = n => new Intl.NumberFormat("fr-MA").format(n) + " DH";

export default function Payroll() {
  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Masse salariale (Mai)", value: "2 250 000 DH", icon: DollarSign, trend: "+2.1%" },
          { label: "Salaire moyen",         value: "9 800 DH",     icon: TrendingUp,  trend: "+1.8%" },
          { label: "Employés payés",        value: "512 / 535",    icon: Users,       trend: "95.7%" },
        ].map(({ label, value, icon: Icon, trend }) => (
          <div key={label} className="card flex items-center gap-4">
            <div className="w-12 h-12 bg-brand-gradient rounded-xl flex items-center justify-center flex-shrink-0">
              <Icon size={22} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-brand-gray font-medium">{label}</p>
              <p className="text-xl font-black text-brand-purple">{value}</p>
              <p className="text-xs text-green-600 font-semibold">{trend}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="card">
        <h3 className="font-bold text-brand-purple mb-4">Masse salariale par département</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={DATA} barSize={36}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="dept" tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => `${v/1000}k`} tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={v => [fmt(v), "Total"]}
              contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }}
              cursor={{ fill: "#f5f5f8" }}
            />
            <Bar dataKey="salaire" fill="url(#grad)" radius={[8, 8, 0, 0]} />
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff5c35" />
                <stop offset="100%" stopColor="#2a1653" />
              </linearGradient>
            </defs>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Payslips table */}
      <div className="card !p-0 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 className="font-bold text-brand-purple">Bulletins de paie — Mai 2026</h3>
          <button className="btn-ghost flex items-center gap-2 text-sm">
            <Download size={15} /> Exporter tout
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Employé", "Poste", "Salaire Brut", "Salaire Net", "Statut", "Action"].map(h => (
                  <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-brand-gray uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PAYSLIPS.map(p => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs">
                        {p.emp.split(" ").map(n => n[0]).join("").slice(0, 2)}
                      </div>
                      <span className="text-sm font-semibold text-brand-purple">{p.emp}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-brand-gray">{p.poste}</td>
                  <td className="px-5 py-3.5 text-sm font-semibold text-brand-purple">{fmt(p.brut)}</td>
                  <td className="px-5 py-3.5 text-sm font-bold text-brand-orange">{fmt(p.net)}</td>
                  <td className="px-5 py-3.5">
                    <span className={p.statut === "payé" ? "badge-active" : "badge-pending"}>
                      {p.statut === "payé" ? "Payé" : "En attente"}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <button className="btn-ghost text-xs flex items-center gap-1 !px-3 !py-1.5">
                      <Download size={13} /> Bulletin
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
