import { useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";

import { errorMessage } from "@/api/errors";
import type { User } from "@/api/types";
import { homeFor } from "@/auth/home";
import { useLogin, useRegister, useSession } from "@/auth/session";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

const MIN_PASSWORD_LENGTH = 8;

const Login = () => {
  const [params, setParams] = useSearchParams();
  const mode: Mode = params.get("mode") === "register" ? "register" : "login";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const location = useLocation();
  const { data: session } = useSession();
  const login = useLogin();
  const register = useRegister();
  const pending = login.isPending || register.isPending;

  // Déjà connecté : retour à l'espace de l'utilisateur
  if (session) return <Navigate to={homeFor(session)} replace />;

  const switchMode = (next: Mode) => {
    setError(null);
    setParams(next === "register" ? { mode: "register" } : {});
  };

  const onSuccess = (user: User) => {
    const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    navigate(from && from !== "/login" ? from : homeFor(user), { replace: true });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!email || !password || (mode === "register" && !name.trim())) {
      setError("Veuillez renseigner tous les champs.");
      return;
    }
    if (mode === "register" && password.length < MIN_PASSWORD_LENGTH) {
      setError(`Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`);
      return;
    }
    const options = { onSuccess, onError: (e: unknown) => setError(errorMessage(e)) };
    if (mode === "login") login.mutate({ email, password }, options);
    else register.mutate({ email, password, name: name.trim() }, options);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute inset-0 noise-overlay" />
      </div>

      <div className="w-full max-w-md relative z-10 animate-fade-up">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-foreground flex items-center justify-center overflow-hidden">
            <img src="/logo_RAG_System.png" alt="RAG System" className="w-full h-full object-contain p-1" />
          </div>
          <div className="flex flex-col">
            <span className="font-oswald text-2xl font-medium tracking-tight">
              RAG<span className="text-primary">SYSTEM</span>
            </span>
            <span className="text-[0.65rem] font-space uppercase tracking-widest text-muted-foreground">
              Retrieval-Augmented Generation
            </span>
          </div>
        </div>

        <Card className="border-border/50 shadow-soft-lg">
          <CardContent className="p-8">
            <div className="flex gap-2 mb-6 border-b border-border" role="tablist">
              {(["login", "register"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={mode === tab}
                  onClick={() => switchMode(tab)}
                  className={cn(
                    "flex-1 py-3 text-sm font-semibold transition-colors",
                    mode === tab
                      ? "border-b-2 border-foreground text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {tab === "login" ? "Connexion" : "Inscription"}
                </button>
              ))}
            </div>

            <div className="text-center mb-6">
              <h1 className="text-2xl font-oswald font-medium tracking-tight mb-2">
                {mode === "login" ? "Bon retour" : "Créer un compte"}
              </h1>
              <p className="text-muted-foreground text-sm">
                {mode === "login"
                  ? "Connectez-vous pour interroger vos documents"
                  : "Rejoignez RAG System en quelques secondes"}
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-5 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {mode === "register" && (
                <div className="space-y-2">
                  <label htmlFor="name" className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    Nom
                  </label>
                  <Input
                    id="name"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={pending}
                    className="bg-background"
                  />
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="email" className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={pending}
                  className="bg-background"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  Mot de passe
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={pending}
                    className="bg-background pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {mode === "register" && (
                  <p className="text-xs text-muted-foreground">Minimum {MIN_PASSWORD_LENGTH} caractères</p>
                )}
              </div>

              <Button type="submit" className="w-full" size="lg" disabled={pending}>
                {pending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {mode === "login" ? "Connexion…" : "Création…"}
                  </>
                ) : (
                  <>
                    {mode === "login" ? "Se connecter" : "Créer mon compte"}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
