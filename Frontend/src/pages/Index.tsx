import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Brain, 
  X, 
  AlertCircle, 
  ArrowRight, 
  User, 
  Globe, 
  Bot,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ShieldCheck,
  Search,
  BookOpen,
  Star,
  Zap,
  Check,
  Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuthStore } from "@/stores/authStore";

const Index = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, login, register } = useAuthStore();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<"admin" | "user">("user");
  const [isLoading, setIsLoading] = useState(false);
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsLoading(true);
    
    const result = await login(email, password);
    
    if (result.success) {
      setIsAuthModalOpen(false);
      setEmail("");
      setPassword("");
      const currentUser = useAuthStore.getState().user;
      if (currentUser?.role === "admin") {
        navigate("/admin/dashboard");
      } else {
        navigate("/chat");
      }
    } else {
      setAuthError(result.error || "Erreur de connexion");
    }
    setIsLoading(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsLoading(true);
    
    if (!name.trim()) {
      setAuthError("Le nom est requis");
      setIsLoading(false);
      return;
    }

    if (password.length < 4) {
      setAuthError("Le mot de passe doit contenir au moins 4 caractères");
      setIsLoading(false);
      return;
    }
    
    const result = await register(email, password, name, role);
    
    if (result.success) {
      setIsAuthModalOpen(false);
      setEmail("");
      setPassword("");
      setName("");
      setRole("user");
      const currentUser = useAuthStore.getState().user;
      if (currentUser?.role === "admin") {
        navigate("/admin/dashboard");
      } else {
        navigate("/chat");
      }
    } else {
      setAuthError(result.error || "Erreur lors de l'inscription");
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#EAEAEA] relative">
      {/* Background effects */}
      <div className="absolute top-0 right-0 w-[50rem] h-[50rem] bg-gradient-to-b from-white/60 to-transparent opacity-50 blur-3xl pointer-events-none rounded-full translate-x-1/3 -translate-y-1/3"></div>

      {/* Auth Modal (Login/Register) */}
      {isAuthModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div 
            onClick={() => {
              setIsAuthModalOpen(false);
              setAuthError(null);
              setEmail("");
              setPassword("");
              setName("");
              setRole("user");
            }}
            className="absolute inset-0 bg-neutral-900/60 backdrop-blur-sm transition-opacity"
          ></div>
          <Card className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 relative z-10">
            <button
              onClick={() => {
                setIsAuthModalOpen(false);
                setAuthError(null);
                setEmail("");
                setPassword("");
                setName("");
                setRole("user");
              }}
              className="absolute top-4 right-4 p-2 text-neutral-400 hover:text-neutral-900 rounded-full hover:bg-neutral-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            
            {/* Tabs */}
            <div className="flex gap-2 mb-8 border-b border-neutral-200">
              <button
                onClick={() => {
                  setAuthMode("login");
                  setAuthError(null);
                }}
                className={`flex-1 py-3 text-sm font-semibold transition-colors ${
                  authMode === "login"
                    ? "text-neutral-900 border-b-2 border-neutral-900"
                    : "text-neutral-500 hover:text-neutral-700"
                }`}
              >
                Connexion
              </button>
              <button
                onClick={() => {
                  setAuthMode("register");
                  setAuthError(null);
                }}
                className={`flex-1 py-3 text-sm font-semibold transition-colors ${
                  authMode === "register"
                    ? "text-neutral-900 border-b-2 border-neutral-900"
                    : "text-neutral-500 hover:text-neutral-700"
                }`}
              >
                Inscription
              </button>
            </div>

            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-neutral-900 text-white mb-4 shadow-lg">
                <User className="w-7 h-7" />
              </div>
              <h3 className="text-2xl font-bold tracking-tight">
                {authMode === "login" ? "Bienvenue sur RAG System" : "Créer un compte"}
              </h3>
              <p className="text-base text-neutral-500 mt-2">
                {authMode === "login" 
                  ? "Connectez-vous pour accéder à la plateforme"
                  : "Rejoignez RAG System et commencez à utiliser notre plateforme"}
              </p>
              {authError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
                  <div className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="w-4 h-4" />
                    <span className="text-xs font-medium">{authError}</span>
                  </div>
                </div>
              )}
            </div>

            {authMode === "login" ? (
              <form className="space-y-4" onSubmit={handleLogin}>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 rounded-lg border border-neutral-200 bg-neutral-50 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:bg-white transition-all placeholder:text-neutral-400"
                    placeholder="admin@rag-system.io"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Mot de passe
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 rounded-lg border border-neutral-200 bg-neutral-50 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:bg-white transition-all placeholder:text-neutral-400"
                    placeholder="••••••••"
                  />
                </div>
                <Button 
                  type="submit" 
                  disabled={isLoading}
                  className="w-full py-6 bg-neutral-900 hover:bg-neutral-800 text-white disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Connexion...
                    </>
                  ) : (
                    "Se connecter"
                  )}
                </Button>
              </form>
            ) : (
              <form className="space-y-4" onSubmit={handleRegister}>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Nom complet
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full px-4 py-3 rounded-lg border border-neutral-200 bg-neutral-50 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:bg-white transition-all placeholder:text-neutral-400"
                    placeholder="Jean Dupont"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 rounded-lg border border-neutral-200 bg-neutral-50 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:bg-white transition-all placeholder:text-neutral-400"
                    placeholder="jean.dupont@example.com"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Mot de passe
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={4}
                    className="w-full px-4 py-3 rounded-lg border border-neutral-200 bg-neutral-50 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:bg-white transition-all placeholder:text-neutral-400"
                    placeholder="••••••••"
                  />
                  <p className="text-xs text-neutral-500 mt-1">Minimum 4 caractères</p>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 uppercase tracking-widest mb-1.5">
                    Type de compte
                  </label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setRole("user")}
                      className={`flex-1 px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
                        role === "user"
                          ? "bg-neutral-900 text-white border-neutral-900"
                          : "bg-neutral-50 text-neutral-700 border-neutral-200 hover:border-neutral-300"
                      }`}
                    >
                      Utilisateur
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("admin")}
                      className={`flex-1 px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
                        role === "admin"
                          ? "bg-neutral-900 text-white border-neutral-900"
                          : "bg-neutral-50 text-neutral-700 border-neutral-200 hover:border-neutral-300"
                      }`}
                    >
                      Administrateur
                    </button>
                  </div>
                </div>
                <Button 
                  type="submit" 
                  disabled={isLoading}
                  className="w-full py-6 bg-neutral-900 hover:bg-neutral-800 text-white disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Inscription...
                    </>
                  ) : (
                    "Créer un compte"
                  )}
                </Button>
              </form>
            )}
          </Card>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex flex-wrap md:px-12 z-30 bg-stone-100 pt-6 pr-6 pb-6 pl-6 relative gap-x-20 gap-y-6 items-center justify-between">
        <div className="flex items-center gap-3 group cursor-pointer mr-8">
          <div className="flex text-white bg-neutral-900 w-9 h-9 rounded-lg relative items-center justify-center overflow-hidden">
            <img 
              src="/logo_RAG_System.png" 
              alt="RAG System Logo" 
              className="w-full h-full object-contain p-1"
            />
          </div>
          <div className="flex flex-col">
            <span className="uppercase leading-none text-2xl font-oswald font-medium tracking-tight">
              RAG
              <span className="text-orange-400">SYSTEM</span>
            </span>
            <span className="text-[0.6rem] uppercase text-neutral-700 tracking-widest font-space">
              Retrieval-Augmented Generation
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-8 mr-auto">
          <a href="#features" className="uppercase hover:text-neutral-900 transition-colors text-xs font-semibold text-neutral-600 tracking-widest">
            FONCTIONNALITÉS
          </a>
          <a href="#solutions" className="uppercase hover:text-neutral-900 transition-colors text-xs font-semibold text-neutral-600 tracking-widest">
            SOLUTIONS
          </a>
          <a href="#about" className="uppercase hover:text-neutral-900 transition-colors text-xs font-semibold text-neutral-600 tracking-widest">
            À PROPOS
          </a>
        </div>

        <div className="flex items-center gap-3 ml-auto">
          <ThemeToggle variant="compact" />
          {isAuthenticated ? (
            <>
              <span className="text-xs font-semibold uppercase tracking-tight">
                {user?.name}
              </span>
              <Button
                onClick={() => {
                  if (user?.role === "admin") {
                    navigate("/admin/dashboard");
                  } else {
                    navigate("/chat");
                  }
                }}
                className="uppercase text-xs"
              >
                Tableau de bord
              </Button>
            </>
          ) : (
            <Button
              onClick={() => setIsAuthModalOpen(true)}
              className="uppercase text-xs bg-neutral-900 hover:bg-neutral-800 text-white dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
            >
              Se connecter
              <ArrowRight className="ml-2 w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section className="md:px-12 md:pb-10 bg-zinc-100 max-w-[90rem] mx-auto pt-12 pr-6 pb-24 pl-6">
        <div className="flex flex-col gap-x-12 gap-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-12 lg:gap-16 gap-x-0 gap-y-8 items-start">
            <div className="lg:col-span-7 flex flex-col gap-x-8 gap-y-8">
              <div className="flex gap-4 items-center">
                <div className="h-px w-12 bg-neutral-400"></div>
                <span className="uppercase text-sm font-medium text-neutral-500 tracking-widest">
                  Système RAG de nouvelle génération
                </span>
              </div>
              <h1 className="md:text-8xl lg:text-9xl leading-[0.85] uppercase text-6xl font-oswald font-medium text-neutral-900 tracking-tight pt-8 pb-6">
                Intelligence pour l'ère de la
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-neutral-600 to-neutral-900 block">
                  Génération Augmentée
                </span>
              </h1>
            </div>

            <div className="lg:col-span-5 group h-full mt-1 relative">
              <div className="absolute inset-0 bg-neutral-900 rounded-2xl rotate-3 opacity-10 group-hover:rotate-6 transition-transform duration-500"></div>
              <div className="relative rounded-2xl overflow-hidden shadow-2xl h-[27.5rem] lg:h-[34.375rem] w-full bg-gradient-to-br from-blue-500 to-purple-600">
                <div className="absolute inset-0 flex items-center justify-center">
                  <Brain className="w-48 h-48 text-white opacity-20" />
                </div>
                <div className="bg-gradient-to-t from-neutral-900/40 to-transparent absolute top-0 right-0 bottom-0 left-0"></div>
                <div className="absolute bottom-6 left-6 right-6 p-4 bg-white/10 backdrop-blur-md rounded-xl border border-white/20 text-white">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[0.65rem] uppercase tracking-widest">
                      Analyse du Système
                    </span>
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
                  </div>
                  <div className="h-1 w-full bg-white/20 rounded-full overflow-hidden">
                    <div className="h-full bg-white w-2/3 animate-pulse"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col lg:flex-row mt-4 gap-x-12 gap-y-12 items-start">
            <div className="max-w-2xl">
              <h2 className="md:text-2xl leading-tight -mt-6 md:-mt-12 text-xl font-space font-medium text-neutral-800 tracking-tight mb-6">
                RAG System n'est pas qu'une technologie. C'est un partenaire stratégique pour les entreprises qui comprennent que l'avenir de l'IA conversationnelle repose sur la précision et la traçabilité des réponses.
              </h2>
              <div className="mt-8 flex gap-4">
                <Button
                  onClick={() => setIsAuthModalOpen(true)}
                  size="lg"
                  className="px-8 py-4 bg-neutral-900 hover:bg-neutral-800 text-white"
                >
                  ACCÉDER À LA PLATEFORME
                  <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>
            </div>

            <div className="w-full lg:w-5/12 ml-auto overflow-hidden bg-neutral-950 border-neutral-200 border rounded-2xl pt-6 pr-6 pl-6 relative shadow-sm">
              <div className="grid grid-cols-2 gap-4">
                <Card className="bg-gray-50 border-neutral-100">
                  <CardContent className="pt-4">
                    <div className="uppercase text-xs text-neutral-400 mb-1">Précision</div>
                    <div className="text-3xl font-oswald font-medium text-neutral-900">+95%</div>
                    <div className="text-[0.6rem] text-green-600 mt-2 flex items-center gap-1">
                      <ArrowRight className="w-2.5 h-2.5 rotate-[-90deg]" />
                      vs Base LLM
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-neutral-50">
                  <CardContent className="pt-4">
                    <div className="text-xs uppercase text-neutral-400 mb-1">Latence</div>
                    <div className="text-3xl font-oswald font-medium text-neutral-900">&lt;3s</div>
                    <div className="text-[0.6rem] text-green-600 mt-2 flex items-center gap-1">
                      <ArrowRight className="w-2.5 h-2.5 rotate-[-90deg]" />
                      Temps moyen
                    </div>
                  </CardContent>
                </Card>
                <Card className="col-span-2 text-white bg-neutral-900">
                  <CardContent className="pt-4">
                    <div className="flex justify-between items-center mb-4">
                      <span className="uppercase text-xs text-orange-500 tracking-widest">
                        État du Système
                      </span>
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    </div>
                    <div className="space-y-2 font-mono text-[0.65rem] text-neutral-400">
                      <div className="flex justify-between">
                        <span>&gt; RAG Engine</span>
                        <span className="text-white">Actif</span>
                      </div>
                      <div className="flex justify-between">
                        <span>&gt; Vector Store</span>
                        <span className="text-white">En ligne</span>
                      </div>
                      <div className="flex justify-between">
                        <span>&gt; LLM Provider</span>
                        <span className="text-emerald-400">98.5% Uptime</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem VS Solution Section */}
      <section id="features" className="bg-white border-neutral-200 border-t pt-14 pb-10">
        <div className="md:px-12 max-w-7xl mx-auto pr-6 pl-6">
          <div className="flex flex-col md:flex-row mb-16 gap-x-8 gap-y-8 items-end justify-between">
            <div className="max-w-xl">
              <span className="text-xs font-semibold text-red-600 uppercase tracking-widest mb-2 block">
                Le Défi Actuel
              </span>
              <h3 className="md:text-5xl text-4xl font-oswald font-medium text-neutral-900 tracking-tight">
                Des LLM aux systèmes RAG intelligents
              </h3>
              <p className="leading-relaxed text-neutral-600 mt-4">
                Les modèles de langage traditionnels sont limités par leur connaissance statique. La technologie RAG révolutionne l'accès à l'information en combinant recherche contextuelle et génération intelligente.
              </p>
            </div>
            <div className="flex gap-2">
              <div className="bg-neutral-200 w-12 h-1 rounded-full"></div>
              <div className="w-12 h-1 bg-neutral-900 rounded-full"></div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-24">
            <Card className="p-8 bg-neutral-50 border-neutral-100 hover:border-neutral-300 transition-colors">
              <div className="w-10 h-10 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mb-6">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-oswald font-semibold uppercase mb-3">Hallucinations</h4>
              <p className="text-base text-neutral-600 leading-relaxed">
                Les LLM génèrent souvent des informations incorrectes ou inventées, créant un risque de désinformation et de perte de confiance.
              </p>
            </Card>

            <Card className="p-8 bg-neutral-50 border-neutral-100 hover:border-neutral-300 transition-colors">
              <div className="w-10 h-10 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center mb-6">
                <Clock className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-oswald font-semibold uppercase mb-3">Connaissances Obsolètes</h4>
              <p className="text-base text-neutral-600 leading-relaxed">
                Les modèles statiques ne peuvent pas accéder à des informations récentes ou spécifiques à votre organisation, limitant leur utilité.
              </p>
            </Card>

            <Card className="p-8 bg-neutral-50 border-neutral-100 hover:border-neutral-300 transition-colors">
              <div className="w-10 h-10 bg-neutral-200 text-neutral-600 rounded-lg flex items-center justify-center mb-6">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-oswald font-semibold uppercase mb-3">Manque de Traçabilité</h4>
              <p className="text-base text-neutral-600 leading-relaxed">
                Impossible de vérifier la source des informations générées, créant des risques pour la conformité et la crédibilité.
              </p>
            </Card>
          </div>

          <div id="solutions" className="md:p-12 overflow-hidden text-white bg-neutral-900 rounded-3xl pt-8 pr-8 pb-8 pl-8 relative">
            <div className="blur-[6.25rem] bg-blue-500/10 w-96 h-96 rounded-full absolute top-0 right-0"></div>

            <div className="relative z-10 mb-12">
              <span className="uppercase block text-xs font-semibold text-blue-400 tracking-widest mb-2">
                La Solution RAG
              </span>
              <h3 className="md:text-5xl text-3xl font-oswald font-medium tracking-tight">
                Architecture de Génération Augmentée
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 border-neutral-700 border-t">
              <div className="hidden md:contents text-xs uppercase tracking-widest text-neutral-500">
                <div className="col-span-3 text-gray-50 border-neutral-800 border-b pt-4 pr-4 pb-4">Défi</div>
                <div className="col-span-3 text-gray-50 border-neutral-800 border-b border-l px-4 py-4">Solution RAG</div>
                <div className="col-span-6 text-gray-50 border-neutral-800 border-b border-l pt-4 pl-4">Avantage Algorithmique</div>
              </div>

              <div className="col-span-1 md:col-span-3 border-neutral-800 border-b pt-10 pr-4 pb-6 pl-4">
                <span className="font-medium text-red-400">Réponses Incorrectes</span>
              </div>
              <div className="col-span-1 md:col-span-3 md:px-4 md:border-l flex border-neutral-800 border-b pt-6 pb-6 gap-3 items-center">
                <ShieldCheck className="w-5 h-5" />
                <span>Détection d'Hallucinations</span>
              </div>
              <div className="col-span-1 md:col-span-6 md:pl-4 md:border-l text-sm text-neutral-400 border-neutral-800 border-b pt-6 pb-6 pl-4">
                Validation multi-critères : Le système évalue chaque réponse pour détecter les hallucinations, garantissant une précision maximale avant la génération finale.
              </div>

              <div className="col-span-1 md:col-span-3 border-neutral-800 border-b pt-10 pr-4 pb-6 pl-4">
                <span className="font-medium text-red-400">Informations Limitées</span>
              </div>
              <div className="col-span-1 md:col-span-3 py-6 md:px-4 border-b border-neutral-800 md:border-l flex items-center gap-3">
                <Search className="w-4 h-4" />
                <span>Recherche Hybride</span>
              </div>
              <div className="col-span-1 md:col-span-6 md:pl-4 md:border-l text-sm text-neutral-400 border-neutral-800 border-b pt-6 pb-6">
                Retrieval intelligent : Combine recherche vectorielle et BM25 pour trouver les documents les plus pertinents dans votre base de connaissances, garantissant des réponses à jour et précises.
              </div>

              <div className="col-span-1 md:col-span-3 border-neutral-800 border-b pt-10 pr-4 pb-6 pl-4">
                <span className="text-red-400 font-medium">Sources Non Traçables</span>
              </div>
              <div className="col-span-1 md:col-span-3 md:px-4 md:border-l flex gap-3 border-neutral-800 border-b pt-6 pb-6 items-center">
                <BookOpen className="w-5 h-5" />
                <span>Citations Automatiques</span>
              </div>
              <div className="col-span-1 md:col-span-6 md:pl-4 md:border-l text-sm text-neutral-400 border-neutral-800 border-b pt-6 pb-6">
                Traçabilité complète : Chaque réponse inclut des citations cliquables vers les documents sources, permettant la vérification et renforçant la confiance.
              </div>

              <div className="col-span-1 md:col-span-3 border-neutral-800 border-b pt-10 pr-4 pb-6 pl-4">
                <span className="font-medium text-red-400">Qualité Variable</span>
              </div>
              <div className="col-span-1 md:col-span-3 md:px-4 md:border-l flex gap-3 border-neutral-800 border-b pt-6 pb-6 items-center">
                <Star className="w-6 h-6" />
                <span>Évaluation Multi-Critères</span>
              </div>
              <div className="col-span-1 md:col-span-6 md:pl-4 md:border-l text-sm text-neutral-400 border-neutral-800 border-b pt-6 pb-6">
                Scoring intelligent : Évalue chaque réponse sur 5 critères (pertinence, complétude, concision, précision, cohérence) pour garantir une qualité constante et mesurable.
              </div>

              <div className="col-span-1 md:col-span-3 border-neutral-800 border-b pt-10 pr-4 pb-6 pl-4">
                <span className="font-medium text-red-400">Performance Inconstante</span>
              </div>
              <div className="col-span-1 md:col-span-3 md:px-4 md:border-l flex gap-3 border-neutral-800 border-b pt-6 pb-6 items-center">
                <Zap className="w-5 h-5" />
                <span>Circuit Breaker & Retry</span>
              </div>
              <div className="col-span-1 md:col-span-6 md:pl-4 md:border-l text-sm text-neutral-400 border-neutral-800 border-b pt-6 pb-6">
                Résilience maximale : Système de retry intelligent avec circuit breaker et fallback automatique, garantissant une disponibilité optimale même en cas de défaillance.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="about" className="md:px-12 max-w-7xl mx-auto pt-24 pr-6 pb-24 pl-6">
        <div className="mb-16">
          <span className="uppercase block text-xs font-semibold text-neutral-500 tracking-widest mb-2">
            Fonctionnalités Clés
          </span>
              <h3 className="md:text-6xl text-4xl font-oswald font-medium text-neutral-900 tracking-tight max-w-3xl">
                Une plateforme complète pour des réponses intelligentes et fiables.
              </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card className="p-8 flex flex-col justify-between hover:shadow-xl hover:-translate-y-1 transition-all">
            <div>
              <div className="text-sm uppercase tracking-widest text-neutral-500 mb-4">Utilisateur</div>
              <h4 className="text-3xl font-oswald font-medium mb-2">Interface de Chat</h4>
              <div className="text-4xl font-semibold text-neutral-900 mb-6">Gratuit</div>
              <ul className="space-y-4 text-base text-neutral-600 mb-8">
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Chat interactif avec streaming
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Citations cliquables
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Historique des conversations
                </li>
              </ul>
            </div>
            <Button onClick={() => setIsAuthModalOpen(true)} className="w-full" variant="outline">
              Accéder au Chat
            </Button>
          </Card>

          <Card className="p-8 flex flex-col justify-between transform md:-translate-y-4 shadow-2xl relative overflow-hidden bg-neutral-900 text-white border-neutral-800">
            <div className="absolute top-0 right-0 bg-white text-neutral-900 text-[0.6rem] font-semibold uppercase px-3 py-1">
              Recommandé
            </div>
            <div>
              <div className="text-sm uppercase tracking-widest text-neutral-400 mb-4">Administrateur</div>
              <h4 className="text-3xl font-oswald font-medium mb-2">Dashboard Complet</h4>
              <div className="text-4xl font-semibold text-white mb-6">Premium</div>
              <ul className="space-y-4 text-base text-neutral-300 mb-8">
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-white shrink-0 mt-0.5" />
                  Métriques de performance détaillées
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-white shrink-0 mt-0.5" />
                  Analytics avancées
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-white shrink-0 mt-0.5" />
                  Gestion des utilisateurs
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-white shrink-0 mt-0.5" />
                  Export de données
                </li>
              </ul>
            </div>
            <Button onClick={() => setIsAuthModalOpen(true)} className="w-full bg-white text-neutral-900 hover:bg-neutral-200">
              Accéder au Dashboard
            </Button>
          </Card>

          <Card className="p-8 flex flex-col justify-between hover:shadow-xl hover:-translate-y-1 transition-all">
            <div>
              <div className="text-sm uppercase tracking-widest text-neutral-500 mb-4">Entreprise</div>
              <h4 className="text-3xl font-oswald font-medium mb-2">Solution Custom</h4>
              <div className="text-4xl font-semibold text-neutral-900 mb-6">Sur mesure</div>
              <ul className="space-y-4 text-base text-neutral-600 mb-8">
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Intégration API complète
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Support dédié 24/7
                </li>
                <li className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-neutral-900 shrink-0 mt-0.5" />
                  Personnalisation avancée
                </li>
              </ul>
            </div>
            <Button onClick={() => alert("Contactez-nous pour une solution sur mesure")} className="w-full" variant="outline">
              Nous Contacter
            </Button>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="md:px-12 text-neutral-400 bg-neutral-900 border-neutral-800 border-t pt-12 pr-6 pb-12 pl-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4 text-white">
              <span className="text-lg font-oswald font-medium uppercase">RAG SYSTEM</span>
            </div>
            <p className="text-base max-w-xs leading-relaxed">
              La plateforme de référence pour la génération augmentée par récupération. Précision algorithmique pour des réponses fiables.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-12 text-base">
            <div className="flex flex-col gap-3">
              <span className="text-white font-medium uppercase tracking-widest text-xs">Plateforme</span>
              <a href="#features" className="hover:text-white transition-colors">Fonctionnalités</a>
              <a href="#solutions" className="hover:text-white transition-colors">Solutions</a>
              <a href="#about" className="hover:text-white transition-colors">Documentation</a>
            </div>
            <div className="flex flex-col gap-3">
              <span className="text-white font-medium uppercase tracking-widest text-xs">Entreprise</span>
              <a href="#about" className="hover:text-white transition-colors">À propos</a>
              <a href="#" className="hover:text-white transition-colors">Blog</a>
              <a href="#" className="hover:text-white transition-colors">Support</a>
            </div>
          </div>
        </div>
        <div className="max-w-7xl mx-auto mt-12 pt-8 border-t border-neutral-800 text-xs flex justify-between">
          <span>© 2024 RAG System. Tous droits réservés.</span>
          <div className="flex gap-4">
            <span className="hover:text-white cursor-pointer">Confidentialité</span>
            <span className="hover:text-white cursor-pointer">Mentions légales</span>
          </div>
      </div>
      </footer>
    </div>
  );
};

export default Index;
