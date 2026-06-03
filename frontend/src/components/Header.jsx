import { Bell, Search, Menu } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Header({ title, onMenuClick }) {
  const { user } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-gray-100 flex items-center gap-4 px-6 flex-shrink-0 sticky top-0 z-10">
      <button
        onClick={onMenuClick}
        className="lg:hidden p-2 rounded-xl hover:bg-gray-100 transition-colors text-brand-gray"
      >
        <Menu size={20} />
      </button>

      <div className="font-bold text-brand-purple text-lg flex-1">{title}</div>

      {/* Search */}
      <div className="hidden md:flex items-center gap-2 bg-gray-50 border border-gray-100 rounded-xl px-4 py-2 w-56">
        <Search size={15} className="text-brand-gray flex-shrink-0" />
        <input
          placeholder="Rechercher..."
          className="bg-transparent text-sm outline-none w-full text-brand-purple placeholder-brand-lgray"
        />
      </div>

      {/* Notif */}
      <button className="relative p-2 rounded-xl hover:bg-gray-50 transition-colors text-brand-gray">
        <Bell size={20} />
        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-orange rounded-full" />
      </button>

      {/* Avatar */}
      <div className="flex items-center gap-2.5 cursor-pointer group">
        <div className="w-9 h-9 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-sm">
          {(user?.first_name?.[0] || user?.username?.[0] || "U").toUpperCase()}
        </div>
        <div className="hidden sm:block">
          <div className="text-sm font-semibold text-brand-purple leading-tight">
            {user?.first_name || user?.username || "Admin"}
          </div>
          <div className="text-xs text-brand-gray">Administrateur</div>
        </div>
      </div>
    </header>
  );
}
