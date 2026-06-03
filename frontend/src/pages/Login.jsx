import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Eye, EyeOff, LogIn } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(form.username, form.password);
      navigate("/");
    } catch {
      setError("Identifiants incorrects. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left — brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-[480px] bg-brand-gradient p-12 text-white flex-shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 border-2 border-white rounded flex items-center justify-center font-black text-lg">
            M
          </div>
          <span className="font-bold text-lg tracking-wide">AUTOMOTIV</span>
        </div>

        {/* Center visual */}
        <div className="space-y-4">
          <div className="text-5xl font-black leading-tight">
            FlowRH<br />
            <span className="opacity-60 text-3xl font-normal">Système RH</span>
          </div>
          <p className="text-white/70 text-base leading-relaxed">
            Gérez vos employés, congés, présences et paie depuis une seule plateforme moderne.
          </p>

          {/* Stats */}
          <div className="flex gap-6 pt-4">
            {[["535", "Employés"], ["2", "Départements"], ["217", "Postes"]].map(([n, l]) => (
              <div key={l}>
                <div className="text-2xl font-black">{n}</div>
                <div className="text-white/60 text-sm">{l}</div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/40 text-sm">© 2026 M-AUTOMOTIV · FlowRH</p>
      </div>

      {/* Right — login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-[#f5f5f8]">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-10 lg:hidden">
            <div className="w-8 h-8 bg-brand-gradient rounded flex items-center justify-center text-white font-black text-sm">M</div>
            <span className="font-bold text-brand-purple">M·AUTOMOTIV FlowRH</span>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-black text-brand-purple mb-2">Bienvenue</h1>
            <p className="text-brand-gray text-sm">Connectez-vous à votre espace RH</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-brand-purple mb-1.5">Nom d'utilisateur</label>
              <input
                className="input"
                placeholder="votre.nom"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-brand-purple mb-1.5">Mot de passe</label>
              <div className="relative">
                <input
                  className="input pr-11"
                  type={showPwd ? "text" : "password"}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-gray hover:text-brand-orange transition-colors"
                >
                  {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <LogIn size={18} />
                  Se connecter
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
