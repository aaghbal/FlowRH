import { useState } from "react";
import { Search, Plus, Filter, Download, Eye, Edit, Trash2, ChevronLeft, ChevronRight } from "lucide-react";

const MOCK = Array.from({ length: 20 }, (_, i) => ({
  id: i + 1,
  matricule: `EMP${String(i + 1).padStart(3, "0")}`,
  nom: ["Alami", "Benali", "Tahiri", "Cherkaoui", "El Amrani", "Bennis", "Saidi", "Khalid"][i % 8],
  prenom: ["Mohammed", "Sara", "Youssef", "Nadia", "Karim", "Fatima", "Hassan", "Amina"][i % 8],
  dept: ["Commercial", "RH", "Technique", "Finance", "Direction"][i % 5],
  poste: ["Manager", "Technicien", "Comptable", "Commercial", "Directeur"][i % 5],
  statut: i % 7 === 0 ? "inactive" : "active",
  telephone: `06${String(10000000 + i * 1234567).slice(0, 8)}`,
  dateEmbauche: `${String(1 + (i % 28)).padStart(2, "0")}/0${1 + (i % 9)}/202${3 + (i % 3)}`,
}));

const DEPTS = ["Tous", "Commercial", "RH", "Technique", "Finance", "Direction"];

export default function Employees() {
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("Tous");
  const [page, setPage] = useState(1);
  const PER_PAGE = 8;

  const filtered = MOCK.filter(e =>
    (dept === "Tous" || e.dept === dept) &&
    (`${e.prenom} ${e.nom} ${e.matricule}`.toLowerCase().includes(search.toLowerCase()))
  );

  const total = filtered.length;
  const pages = Math.ceil(total / PER_PAGE);
  const rows = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-4 py-2.5 flex-1 min-w-[200px]">
          <Search size={15} className="text-brand-gray flex-shrink-0" />
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            placeholder="Rechercher un employé..."
            className="bg-transparent text-sm outline-none w-full placeholder-brand-lgray text-brand-purple"
          />
        </div>

        <select
          value={dept}
          onChange={e => { setDept(e.target.value); setPage(1); }}
          className="input !w-auto px-3 py-2.5 text-sm"
        >
          {DEPTS.map(d => <option key={d}>{d}</option>)}
        </select>

        <button className="btn-ghost flex items-center gap-2">
          <Filter size={15} /> Filtres
        </button>
        <button className="btn-ghost flex items-center gap-2">
          <Download size={15} /> Export
        </button>
        <button className="btn-primary flex items-center gap-2">
          <Plus size={15} /> Ajouter
        </button>
      </div>

      {/* Table */}
      <div className="card !p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Employé", "Matricule", "Département", "Poste", "Date embauche", "Statut", "Actions"].map(h => (
                  <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-brand-gray uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(emp => (
                <tr key={emp.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors group">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                        {emp.prenom[0]}{emp.nom[0]}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-brand-purple">{emp.prenom} {emp.nom}</div>
                        <div className="text-xs text-brand-gray">{emp.telephone}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm font-mono text-brand-gray">{emp.matricule}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm text-brand-purple">{emp.dept}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm text-brand-gray">{emp.poste}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm text-brand-gray">{emp.dateEmbauche}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={emp.statut === "active" ? "badge-active" : "badge-inactive"}>
                      {emp.statut === "active" ? "Actif" : "Inactif"}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 rounded-lg hover:bg-brand-orange/10 text-brand-orange transition-colors">
                        <Eye size={15} />
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500 transition-colors">
                        <Edit size={15} />
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 transition-colors">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-gray-100">
          <span className="text-sm text-brand-gray">
            {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} sur {total} employés
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-xl hover:bg-gray-100 disabled:opacity-30 transition-colors text-brand-gray"
            >
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: pages }, (_, i) => i + 1).map(p => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-8 h-8 rounded-xl text-sm font-semibold transition-colors
                  ${p === page ? "bg-brand-orange text-white" : "hover:bg-gray-100 text-brand-gray"}`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="p-2 rounded-xl hover:bg-gray-100 disabled:opacity-30 transition-colors text-brand-gray"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
