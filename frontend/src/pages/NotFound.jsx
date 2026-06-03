import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-4">
      <div className="text-8xl font-black bg-brand-gradient bg-clip-text text-transparent">404</div>
      <h2 className="text-2xl font-bold text-brand-purple">Page introuvable</h2>
      <p className="text-brand-gray">Cette page n'existe pas ou a été déplacée.</p>
      <Link to="/" className="btn-primary mt-2">Retour au tableau de bord</Link>
    </div>
  );
}
