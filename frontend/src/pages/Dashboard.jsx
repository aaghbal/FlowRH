import { Users, CalendarDays, Clock, TrendingUp, UserCheck, UserX, AlertCircle, ArrowUpRight } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from "recharts";

const KPI = [
  { label: "Total Employés",    value: "535", change: "+12",  icon: Users,       color: "bg-brand-gradient",     text: "text-white" },
  { label: "Présents Aujourd'hui", value: "498", change: "93%", icon: UserCheck,   color: "bg-green-500",          text: "text-white" },
  { label: "En Congé",          value: "18",  change: "3.4%", icon: CalendarDays, color: "bg-brand-orange",       text: "text-white" },
  { label: "Heures ce Mois",    value: "9 420", change: "+2.1%", icon: Clock,    color: "bg-brand-purple",       text: "text-white" },
];

const attendanceData = [
  { day: "Lun", présents: 510, absents: 25 },
  { day: "Mar", présents: 498, absents: 37 },
  { day: "Mer", présents: 521, absents: 14 },
  { day: "Jeu", présents: 505, absents: 30 },
  { day: "Ven", présents: 487, absents: 48 },
];

const leaveData = [
  { name: "Congé annuel", value: 45, color: "#ff5c35" },
  { name: "Maladie",      value: 18, color: "#b6507b" },
  { name: "Maternité",    value: 8,  color: "#2a1653" },
  { name: "Sans solde",   value: 5,  color: "#c0c0c8" },
];

const salaryData = [
  { month: "Jan", total: 2100000 },
  { month: "Fév", total: 2080000 },
  { month: "Mar", total: 2150000 },
  { month: "Avr", total: 2200000 },
  { month: "Mai", total: 2180000 },
  { month: "Jui", total: 2250000 },
];

const recentEmployees = [
  { name: "Karim Benali",    dept: "Commercial",   date: "01/06/2026", status: "active" },
  { name: "Sara El Amrani",  dept: "RH",           date: "28/05/2026", status: "active" },
  { name: "Youssef Tahiri",  dept: "Technique",    date: "20/05/2026", status: "pending" },
  { name: "Nadia Cherkaoui", dept: "Finance",      date: "15/05/2026", status: "active" },
];

const pendingLeaves = [
  { name: "Mohammed Alami",  type: "Congé annuel", days: 5,  from: "10/06" },
  { name: "Fatima Zahra",    type: "Maladie",      days: 3,  from: "08/06" },
  { name: "Hassan Bennis",   type: "Sans solde",   days: 10, from: "15/06" },
];

function fmt(n) {
  return new Intl.NumberFormat("fr-MA", { style: "currency", currency: "MAD", maximumFractionDigits: 0 }).format(n);
}

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {KPI.map(({ label, value, change, icon: Icon, color, text }) => (
          <div key={label} className={`card overflow-hidden relative`}>
            <div className={`absolute inset-0 opacity-5 ${color}`} />
            <div className="relative flex items-start justify-between">
              <div>
                <p className="text-brand-gray text-xs font-medium mb-1">{label}</p>
                <p className="text-3xl font-black text-brand-purple">{value}</p>
                <span className="text-xs text-green-600 font-semibold flex items-center gap-1 mt-1">
                  <ArrowUpRight size={12} /> {change}
                </span>
              </div>
              <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center shadow-brand flex-shrink-0`}>
                <Icon size={22} className={text} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Attendance bar */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-brand-purple">Présences cette semaine</h3>
            <span className="text-xs text-brand-gray bg-gray-50 px-3 py-1 rounded-full">Semaine 23</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={attendanceData} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="day" tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }}
                cursor={{ fill: "#f5f5f8" }}
              />
              <Bar dataKey="présents" fill="#ff5c35" radius={[6, 6, 0, 0]} name="Présents" />
              <Bar dataKey="absents"  fill="#f2f2f2" radius={[6, 6, 0, 0]} name="Absents" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Leave pie */}
        <div className="card">
          <h3 className="font-bold text-brand-purple mb-4">Types de Congés</h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={leaveData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                {leaveData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {leaveData.map(({ name, value, color }) => (
              <div key={name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-brand-gray">{name}</span>
                </div>
                <span className="font-semibold text-brand-purple">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Salary trend */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-brand-purple">Évolution de la Masse Salariale</h3>
          <span className="text-xs text-brand-gray">2026</span>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={salaryData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => `${(v/1000000).toFixed(1)}M`} tick={{ fontSize: 12, fill: "#616175" }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={v => [fmt(v), "Masse salariale"]}
              contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }}
            />
            <Line type="monotone" dataKey="total" stroke="#ff5c35" strokeWidth={3} dot={{ fill: "#ff5c35", strokeWidth: 0, r: 5 }} activeDot={{ r: 7 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Bottom tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent employees */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-brand-purple">Nouveaux Employés</h3>
            <a href="/employees" className="text-xs text-brand-orange font-semibold hover:underline">Voir tout</a>
          </div>
          <div className="space-y-3">
            {recentEmployees.map(({ name, dept, date, status }) => (
              <div key={name} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <div className="w-9 h-9 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                  {name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-brand-purple truncate">{name}</div>
                  <div className="text-xs text-brand-gray">{dept} · {date}</div>
                </div>
                <span className={status === "active" ? "badge-active" : "badge-pending"}>
                  {status === "active" ? "Actif" : "En cours"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Pending leaves */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-brand-purple">Congés en Attente</h3>
            <span className="badge-pending">{pendingLeaves.length} demandes</span>
          </div>
          <div className="space-y-3">
            {pendingLeaves.map(({ name, type, days, from }) => (
              <div key={name} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <div className="w-9 h-9 rounded-full bg-brand-orange/10 flex items-center justify-center flex-shrink-0">
                  <CalendarDays size={16} className="text-brand-orange" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-brand-purple truncate">{name}</div>
                  <div className="text-xs text-brand-gray">{type} · {days}j · à partir du {from}</div>
                </div>
                <div className="flex gap-1.5">
                  <button className="px-2.5 py-1 bg-green-100 text-green-700 text-xs rounded-lg font-semibold hover:bg-green-200 transition-colors">✓</button>
                  <button className="px-2.5 py-1 bg-red-100 text-red-600 text-xs rounded-lg font-semibold hover:bg-red-200 transition-colors">✗</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
